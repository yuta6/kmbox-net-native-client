import socket
import struct
import random
from dataclasses import dataclass, field
import time

from .monitor import Monitor
from .hidtable import HidKey

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
        self._index = 0
        self._soft_mouse = SoftMouse()

        # define sokect
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.settimeout(self.TIMEOUT)
            self._server_addr = (ip, port)
        except Exception as e:
            raise ConnectionError(e)

        # send connectet command
        result, _ = self.send_cmd(CMD_CONNECT)
        if result is False:
            raise ConnectionError("Connection failture.")

        # start monitor
        self.monitor: Monitor | None = None
        if monitor_port is not None:
            try:
                rand_override = monitor_port | (0xAA55 << 16)
                result, data = self.send_cmd(CMD_MONITOR, rand_override=rand_override)

                if result:
                    self.monitor = Monitor(monitor_port)
                    self.monitor.start()
                    time.sleep(0.01)
                else:
                    raise MonitorError("Device monitor setup failed")

            except Exception as e:
                print(f"monitor start error: {e}")

    def _make_header(self, cmd: int, rand_override: int | None = None) -> bytes:
        self._index += 1
        if rand_override is None:
            rand_override = random.randint(0, 0x7FFFFFFF)
        return struct.pack("<IIII", self.mac, rand_override, self._index, cmd)

    def send_cmd(self, cmd: int, payload: bytes = b'', rand_override: int | None = None) -> tuple[bool, bytes]:
        self._sock.sendto(self._make_header(cmd, rand_override) + payload, self._server_addr)

        try:
            data, sender_addr = self._sock.recvfrom(1024)
            _, _, resp_index, resp_cmd = struct.unpack("<IIII", data[:16])
            if resp_cmd != cmd or resp_index != self._index or sender_addr != self._server_addr:
                raise CommandError("Invalid Response")
            return True, data
        except socket.timeout:
            raise TimeoutError("Command Timeout")
        except CommandError as e:
            print(f"Warning:{e}")
            return False, b''
        except Exception as e:
            print(f"Error:{e}")
            return False, b''

    def move(self, x: int, y: int) -> bool:
        """Move mouse"""
        self._soft_mouse.x = x
        self._soft_mouse.y = y

        result, _ = self.send_cmd(CMD_MOUSE_MOVE, self._soft_mouse.to_payload())

        self._soft_mouse.reset_movement()
        return result

    def left(self, is_down: bool) -> bool:
        """Left mouse button"""
        if is_down:
            self._soft_mouse.button |= 0x01
        else:
            self._soft_mouse.button &= ~0x01

        result, _ = self.send_cmd(CMD_MOUSE_LEFT, self._soft_mouse.to_payload())
        return result

    def right(self, is_down: bool) -> bool:
        """Right mouse button"""
        if is_down:
            self._soft_mouse.button |= 0x02
        else:
            self._soft_mouse.button &= ~0x02

        result, _ = self.send_cmd(CMD_MOUSE_RIGHT, self._soft_mouse.to_payload())
        return result

    def middle(self, is_down: bool) -> bool:
        """Middle mouse button"""
        if is_down:
            self._soft_mouse.button |= 0x04
        else:
            self._soft_mouse.button &= ~0x04

        result, _ = self.send_cmd(CMD_MOUSE_MIDDLE, self._soft_mouse.to_payload())
        return result

    def wheel(self, wheel_value: int) -> bool:
        """Mouse wheel scroll"""
        self._soft_mouse.wheel = wheel_value

        result, _ = self.send_cmd(CMD_MOUSE_WHEEL, self._soft_mouse.to_payload())

        self._soft_mouse.wheel = 0
        return result

    def mouse_all(self, button: int, x: int, y: int, wheel: int) -> bool:
        """All mouse operations in one command"""
        self._soft_mouse.button = button
        self._soft_mouse.x = x
        self._soft_mouse.y = y
        self._soft_mouse.wheel = wheel

        result, _ = self.send_cmd(CMD_MOUSE_WHEEL, self._soft_mouse.to_payload())

        self._soft_mouse.reset_movement()
        return result

    def mask_left(self, enable: bool) -> bool:
        """Mask/unmask left mouse button"""
        if enable:
            self.mask_flag |= 0x01  # BIT0
        else:
            self.mask_flag &= ~0x01
        result, _ = self.send_cmd(CMD_MASK_MOUSE, rand_override=self.mask_flag)
        return result

    def mask_right(self, enable: bool) -> bool:
        """Mask/unmask right mouse button"""
        if enable:
            self.mask_flag |= 0x02  # BIT1
        else:
            self.mask_flag &= ~0x02
        result, _ = self.send_cmd(CMD_MASK_MOUSE, rand_override=self.mask_flag)
        return result

    def mask_middle(self, enable: bool) -> bool:
        """Mask/unmask middle mouse button"""
        if enable:
            self.mask_flag |= 0x04  # BIT2
        else:
            self.mask_flag &= ~0x04
        result, _ = self.send_cmd(CMD_MASK_MOUSE, rand_override=self.mask_flag)
        return result

    def mask_side1(self, enable: bool) -> bool:
        """Mask/unmask side button 1"""
        if enable:
            self.mask_flag |= 0x08  # BIT3
        else:
            self.mask_flag &= ~0x08
        result, _ = self.send_cmd(CMD_MASK_MOUSE, rand_override=self.mask_flag)
        return result

    def mask_side2(self, enable: bool) -> bool:
        """Mask/unmask side button 2"""
        if enable:
            self.mask_flag |= 0x10  # BIT4
        else:
            self.mask_flag &= ~0x10
        result, _ = self.send_cmd(CMD_MASK_MOUSE, rand_override=self.mask_flag)
        return result

    def mask_x(self, enable: bool) -> bool:
        """Mask/unmask X axis movement"""
        if enable:
            self.mask_flag |= 0x20  # BIT5
        else:
            self.mask_flag &= ~0x20
        result, _ = self.send_cmd(CMD_MASK_MOUSE, rand_override=self.mask_flag)
        return result

    def mask_y(self, enable: bool) -> bool:
        """Mask/unmask Y axis movement"""
        if enable:
            self.mask_flag |= 0x40  # BIT6
        else:
            self.mask_flag &= ~0x40
        result, _ = self.send_cmd(CMD_MASK_MOUSE, rand_override=self.mask_flag)
        return result

    def mask_wheel(self, enable: bool) -> bool:
        """Mask/unmask mouse wheel"""
        if enable:
            self.mask_flag |= 0x80  # BIT7
        else:
            self.mask_flag &= ~0x80
        result, _ = self.send_cmd(CMD_MASK_MOUSE, rand_override=self.mask_flag)
        return result

    @property
    def is_left(self) -> bool:
        if not self.monitor:
            raise MonitorError("monitor not configured")
        return self.monitor.is_mouse_left

    @property
    def is_middle(self) -> bool:
        if not self.monitor:
            raise MonitorError("monitor not configured")
        return self.monitor.is_mouse_middle

    @property
    def is_right(self) -> bool:
        if not self.monitor:
            raise MonitorError("monitor not configured")
        return self.monitor.is_mouse_right

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

class MonitorError(KmboxError):
    pass
