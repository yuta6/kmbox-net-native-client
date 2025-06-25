import socket
import struct
import random
from dataclasses import dataclass, field

from .monitor import Monitor,MonitorError
from .hidtable import HidKey
from ._bitmask import BitMask

CMD_CONNECT        = 0xaf3c2828
CMD_MOUSE_MOVE     = 0xaede7345
CMD_MOUSE_LEFT     = 0x9823ae8d
CMD_MOUSE_MIDDLE   = 0x97a3ae8d
CMD_MOUSE_RIGHT    = 0x238d8212
CMD_MOUSE_WHEEL    = 0xffeead38
CMD_MOUSE_AUTOMOVE = 0xaede7346
CMD_KEYBOARD_ALL   = 0x123c2c2f
CMD_REBOOT         = 0xaa8855aa
CMD_BEZIER_MOVE    = 0xa238455a
CMD_MONITOR        = 0x27388020
CMD_DEBUG          = 0x27382021
CMD_MASK_MOUSE     = 0x23234343
CMD_UNMASK_ALL     = 0x23344343
CMD_SETCONFIG      = 0x1d3d3323
CMD_SETVIDPID      = 0xffed3232
CMD_SHOWPIC        = 0x12334883
CMD_TRACE_ENABLE   = 0xbbcdddac

class Kmbox:
    TIMEOUT= 2.0

    def __init__(self, ip: str, port: int, uuid: str, monitor_port:int|None = 5002):
        """
        :param ip: Kmbox IP Adress
        :param port: Kmbox Port
        :param uuid: Kmbox UUID 8 degits hex
        :param timeout: socket receive timeout
        """
        # mac address generation from uuid
        try:
            mac_bytes = bytes.fromhex(uuid)
            if len(mac_bytes) != 4:
                raise ValueError
            self.mac = int.from_bytes(mac_bytes, byteorder='big')
        except ValueError:
            raise ConnectionError("UUID is 8 degits.")

        # key
        self.key = list(mac_bytes)
        self.index = 0
        self.soft_mouse = SoftMouse()
        self.soft_keyboard = SoftKeyboard()

        # define sokect
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(self.TIMEOUT)
            self.server_addr = (ip, port)
        except Exception as e:
            raise ConnectionError(e)

        # send connectet command
        result, _ = self.send_cmd(CMD_CONNECT)
        if result is False:
            raise ConnectionError("Connection failture.")

        # start monitor
        self._monitor: Monitor | None = None
        if monitor_port is not None:
            try:
                self._monitor = Monitor(monitor_port)
                self._monitor.start()
                rand_override = monitor_port | (0xAA55 << 16)
                result, _ = self.send_cmd(CMD_MONITOR, rand_override= rand_override)
                if result is False:
                    raise MonitorError("Monitor start failture.")
            except Exception as e:
                print(f"monitor start error: {e}")

    def _make_header(self, cmd: int, rand_override: int | None = None) -> bytes:
        self.index += 1
        if rand_override is None:
            rand_override = random.randint(0, 0x7FFFFFFF)
        return struct.pack("<IIII", self.mac, rand_override, self.index, cmd)

    def send_cmd(self, cmd: int, payload: bytes = b'', rand_override: int | None = None) -> tuple[bool, bytes]:
        self.sock.sendto(self._make_header(cmd, rand_override) + payload, self.server_addr)

        try:
            data, sender_addr = self.sock.recvfrom(1024)
            _, _, resp_index, resp_cmd = struct.unpack("<IIII", data[:16])
            if resp_cmd != cmd or resp_index != self.index or sender_addr != self.server_addr:
                raise CommandError("Invalid Response")
            return True, data
        except socket.timeout:
            raise TimeoutError("Command Timeout")
        except CommandError as e:
            print(f"Warning:{e}")
            return False, b''

    def move(self, x: int, y: int) -> bool:
        """Move mouse"""
        self.soft_mouse.x = x
        self.soft_mouse.y = y

        result, _ = self.send_cmd(CMD_MOUSE_MOVE, self.soft_mouse.to_payload())

        self.soft_mouse.reset_movement()
        return result

    def left(self, is_down: bool) -> bool:
        """Left mouse button"""
        if is_down:
            self.soft_mouse.button |= 0x01
        else:
            self.soft_mouse.button &= ~0x01

        result, _ = self.send_cmd(CMD_MOUSE_LEFT, self.soft_mouse.to_payload())
        return result

    def right(self, is_down: bool) -> bool:
        """Right mouse button"""
        if is_down:
            self.soft_mouse.button |= 0x02
        else:
            self.soft_mouse.button &= ~0x02

        result, _ = self.send_cmd(CMD_MOUSE_RIGHT, self.soft_mouse.to_payload())
        return result

    def middle(self, is_down: bool) -> bool:
        """Middle mouse button"""
        if is_down:
            self.soft_mouse.button |= 0x04
        else:
            self.soft_mouse.button &= ~0x04

        result, _ = self.send_cmd(CMD_MOUSE_MIDDLE, self.soft_mouse.to_payload())
        return result

    def wheel(self, wheel_value: int) -> bool:
        """Mouse wheel scroll"""
        self.soft_mouse.wheel = wheel_value

        result, _ = self.send_cmd(CMD_MOUSE_WHEEL, self.soft_mouse.to_payload())

        self.soft_mouse.wheel = 0
        return result

    @property
    def is_left(self) -> bool:
        if not self._monitor:
            raise MonitorError("monitor not configured")
        return self._monitor.is_mouse_left

    @property
    def is_middle(self) -> bool:
        if not self._monitor:
            raise MonitorError("monitor not configured")
        return self._monitor.is_mouse_middle

    @property
    def is_right(self) -> bool:
        if not self._monitor:
            raise MonitorError("monitor not configured")
        return self._monitor.is_mouse_right

@dataclass
class SoftMouse:
    button: int = 0
    x: int = 0
    y: int = 0
    wheel: int = 0
    point: list[int] = field(default_factory=lambda: [0] * 10)

    def to_payload(self) -> bytes:
        """Convert to struct payload"""
        return struct.pack("<14i", self.button, self.x, self.y, self.wheel, *self.point)

    def reset_movement(self) :
        """Reset relative movement values"""
        self.x = 0
        self.y = 0
        self.wheel = 0


class KmboxError(Exception):
    pass

class ConnectionError(KmboxError):
    pass

class TimeoutError(KmboxError):
    pass

class CommandError(KmboxError):
    pass
