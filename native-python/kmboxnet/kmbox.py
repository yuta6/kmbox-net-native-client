import socket
import struct
import random
from dataclasses import dataclass, field
import time
from typing import Optional
import ipaddress

from .monitor import Monitor

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

@dataclass
class SoftKeyboard:
    ctrl: int = 0
    reserved: int = 0
    button: list[int] = field(default_factory=lambda: [0] * 10)

    def to_payload(self) -> bytes:
        """Convert to struct payload"""
        return struct.pack("<BB10B", self.ctrl, self.reserved, *self.button)

class KmboxNet:
    TIMEOUT= 2.0

    def __init__(self, ip: str, port: int, uuid: str, monitor_port:int|None = 5002, monitor_timeout: Optional[float] = 0.003):
        """
        Initialize KmboxNet connection.

        Args:
            ip (str): Your Kmbox device IP address
            port (int): Your Kmbox device port number
            uuid (str): Your Kmbox device UUID (8 digit hexadecimal)
            monitor_port (int|None, optional): Monitor port number. None to disable. Defaults to 5002.
            monitor_timeout (float, optional): Monitor timeout in seconds. Defaults to 0.003.

        Raises:
            KmboxError: If UUID is invalid or connection fails
        """
        # mac address generation from uuid
        try:
            mac_bytes = bytes.fromhex(uuid)
            if len(mac_bytes) != 4:
                raise ValueError
            self.mac = int.from_bytes(mac_bytes, byteorder='big')
        except ValueError:
            raise KmboxError("UUID is 8 degits.")

        self._index = 0
        self._soft_mouse = SoftMouse()
        self._soft_keyboard = SoftKeyboard()
        self.mask_flag = 0

        # define sokect
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.settimeout(self.TIMEOUT)
            self._server_addr = (ip, port)
        except Exception as e:
            raise KmboxError(e)

        # send connectet command
        result, _ = self.send_cmd(CMD_CONNECT)
        if result is False:
            raise KmboxError("Connection failture.")

        # start monitor
        self.monitor: Monitor | None = None
        if monitor_port is not None:
            try:
                rand_override = monitor_port | (0xAA55 << 16)
                result, data = self.send_cmd(CMD_MONITOR, rand_override=rand_override)

                if result:
                    self.monitor = Monitor(monitor_port, monitor_timeout)
                    self.monitor.start()
                    time.sleep(0.01)
                else:
                    raise KmboxError("Device monitor setup failed")

            except Exception as e:
                print(f"monitor start error: {e}")

    def _make_header(self, cmd: int, rand_override: int | None = None) -> bytes:
        self._index += 1
        if rand_override is None:
            rand_override = random.randint(0, 0x7FFFFFFF)
        return struct.pack("<IIII", self.mac, rand_override, self._index, cmd)

    def send_cmd(self, cmd: int, payload: bytes = b'', rand_override: int | None = None) -> tuple[bool, bytes]:
        """
        Send directly command to Kmbox device.

        Args:
            cmd (int): Command ID to send
            payload (bytes, optional): Command payload data. Defaults to b''.
            rand_override (int | None, optional): Override random value. Defaults to None.

        Returns:
            tuple[bool, bytes]: (Success status, Response data)
        """
        header = self._make_header(cmd, rand_override)
        
        MAX_PACKET_SIZE = 1500  # keep safely at MTU of 1500
        
        # If total packet fits in one send
        if len(header) + len(payload) <= MAX_PACKET_SIZE:
            packet = header + payload
            # Send normally here
            return self._send_packet(packet)

        # Else send in chunks
        for i in range(0, len(payload), MAX_PACKET_SIZE):
            chunk_payload = payload[i:i + MAX_PACKET_SIZE]
            packet = header + chunk_payload
            success, response = self._send_packet(packet)
            if not success:
                return False, b''
        return True, b''

    def _send_packet(self, packet: bytes) -> tuple[bool, bytes]:
        try:
            self._sock.sendto(packet, self._server_addr)
            return True, b''
        except OSError as e:
            print(f"Send error: {e}")
            return False, b''

    def move(self, x: int, y: int) -> bool:
        """
        Move mouse cursor relatively.

        Args:
            x (int): Relative X-axis movement in pixels
            y (int): Relative Y-axis movement in pixels

        Returns:
            bool: True if command sent successfully
        """
        self._soft_mouse.x = x
        self._soft_mouse.y = y

        result, _ = self.send_cmd(CMD_MOUSE_MOVE, self._soft_mouse.to_payload())

        self._soft_mouse.reset_movement()
        return result

    def move_auto(self, x: int, y: int, ms: int) -> bool:
        """
        Move mouse cursor automatically over specified duration.

        Args:
            x (int): Relative X-axis movement in pixels
            y (int): Relative Y-axis movement in pixels
            ms (int): Movement duration in milliseconds

        Returns:
            bool: True if command sent successfully
        """
        self._soft_mouse.x = x
        self._soft_mouse.y = y

        result, _ = self.send_cmd(CMD_MOUSE_AUTOMOVE, self._soft_mouse.to_payload(), rand_override=ms)

        self._soft_mouse.reset_movement()
        return result

    def move_bezier(self, x: int, y: int, ms: int, x1: int, y1: int, x2: int, y2: int) -> bool:
        """
        Move mouse cursor using Bezier curve.

        Args:
            x (int): End point X coordinate
            y (int): End point Y coordinate
            ms (int): Movement duration in milliseconds
            x1 (int): First control point X coordinate
            y1 (int): First control point Y coordinate
            x2 (int): Second control point X coordinate
            y2 (int): Second control point Y coordinate

        Returns:
            bool: True if command sent successfully
        """
        self._soft_mouse.x = x
        self._soft_mouse.y = y
        self._soft_mouse.point[0] = x1
        self._soft_mouse.point[1] = y1
        self._soft_mouse.point[2] = x2
        self._soft_mouse.point[3] = y2

        result, _ = self.send_cmd(CMD_BEZIER_MOVE, self._soft_mouse.to_payload(), rand_override=ms)

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
        """
        Scroll mouse wheel.

        Args:
            wheel_value (int): Wheel scroll amount (positive for up, negative for down)

        Returns:
            bool: True if command sent successfully
        """
        self._soft_mouse.wheel = wheel_value
        result, _ = self.send_cmd(CMD_MOUSE_WHEEL, self._soft_mouse.to_payload())
        self._soft_mouse.wheel = 0
        return result

    def key_down(self, vk_key: int) -> bool:
        """Press key down"""
        if 0xE0 <= vk_key <= 0xE7:
            bit_pos = vk_key - 0xE0  # 0xE0→0, 0xE1→1, ..., 0xE7→7
            self._soft_keyboard.ctrl |= (1 << bit_pos)
        else:
            for i in range(10):
                if self._soft_keyboard.button[i] == vk_key:
                    break
                if self._soft_keyboard.button[i] == 0:
                    self._soft_keyboard.button[i] = vk_key
                    break
            else:
                self._soft_keyboard.button[:-1] = self._soft_keyboard.button[1:]
                self._soft_keyboard.button[9] = vk_key

        result, _ = self.send_cmd(CMD_KEYBOARD_ALL, self._soft_keyboard.to_payload())
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

    def key_up(self, vk_key: int) -> bool:
        """Release key"""
        if 0xE0 <= vk_key <= 0xE7:
            bit_pos = vk_key - 0xE0
            self._soft_keyboard.ctrl &= ~(1 << bit_pos)
        else:
            for i in range(10):
                if self._soft_keyboard.button[i] == vk_key:
                    self._soft_keyboard.button[i:-1] = self._soft_keyboard.button[i+1:]
                    self._soft_keyboard.button[9] = 0
                    break

        result, _ = self.send_cmd(CMD_KEYBOARD_ALL, self._soft_keyboard.to_payload())
        return result

    def mask_keyboard(self, vkey: int) -> bool:
        """Mask specific keyboard key"""
        v_key = vkey & 0xFF
        rand_value = (self.mask_flag & 0xFF) | (v_key << 8)
        result, _ = self.send_cmd(CMD_MASK_MOUSE, rand_override=rand_value)
        return result

    def unmask_keyboard(self, vkey: int) -> bool:
        """Unmask specific keyboard key"""
        v_key = vkey & 0xFF
        rand_value = (self.mask_flag & 0xFF) | (v_key << 8)
        result, _ = self.send_cmd(CMD_UNMASK_ALL, rand_override=rand_value)
        return result

    def unmask_all(self) -> bool:
        """Unmask all previously masked inputs"""
        self.mask_flag = 0
        result, _ = self.send_cmd(CMD_UNMASK_ALL, rand_override=self.mask_flag)
        return result

    def set_config(self, ip: str, port: int) -> bool:
        """Set device IP configuration"""
        ip_int = int(ipaddress.IPv4Address(ip))
        payload = struct.pack(">H", port)
        result, _ = self.send_cmd(CMD_SETCONFIG, payload, rand_override=ip_int)
        return result

    def reboot(self) -> bool:
        """Reboot the kmbox device and disconnect"""
        try:
            result, _ = self.send_cmd(CMD_REBOOT)

            self._sock.close()

            if self.monitor:
                self.monitor.stop()

            return result
        except Exception:
            return False

    def debug(self, port: int, enable: bool) -> bool:
        """Enable/disable debug output to specified port"""
        rand_value = port | (int(enable) << 16)
        result, _ = self.send_cmd(CMD_DEBUG, rand_override=rand_value)
        return result

    def lcd_color(self, rgb565: int) -> bool:
        """Fill LCD screen with specified color"""
        try:
            for y in range(40):
                color_data = struct.pack("<512H", *([rgb565] * 512))
                rand_value = 0 | (y * 4)
                result, _ = self.send_cmd(CMD_SHOWPIC, color_data, rand_override=rand_value)
                if not result:
                    return False
            return True
        except Exception:
            return False

    def lcd_picture_bottom(self, image_data: bytes) -> bool:
        """Display 128x80 picture on bottom of LCD"""
        if len(image_data) != 128 * 80 * 2:  # 128x80x2bytes
            raise ValueError("Image data must be 128x80x2 bytes (RGB565)")

        try:
            for y in range(20):
                row_data = image_data[y * 1024:(y + 1) * 1024]
                rand_value = 80 + (y * 4)
                result, _ = self.send_cmd(CMD_SHOWPIC, row_data, rand_override=rand_value)
                if not result:
                    return False
            return True
        except Exception:
            return False

    def lcd_picture(self, image_data: bytes) -> bool:
        """Display 128x160 picture on full LCD"""
        if len(image_data) != 128 * 160 * 2:
            raise ValueError("Image data must be 128x160x2 bytes (RGB565)")

        try:
            for _ in range(3): # Repeat three times - UDP seems drop some packets occasionally, three writes fixes it.
                for y in range(40):
                    row_data = image_data[y * 1024:(y + 1) * 1024]
                    rand_value = y * 4
                    result, _ = self.send_cmd(CMD_SHOWPIC, row_data, rand_override=rand_value)
                    if not result:
                        return False
            return True
        except Exception:
            return False

    def set_vid_pid(self, vid: int, pid: int) -> bool:
        """Set USB Vendor ID and Product ID"""
        payload = struct.pack("<HH", vid, pid)
        result, _ = self.send_cmd(CMD_SETVIDPID, payload)
        return result

    def trace_enable(self, enable: bool) -> bool:
        """Enable/disable trace functionality"""
        rand_value = 1 if enable else 0
        result, _ = self.send_cmd(CMD_TRACE_ENABLE, rand_override=rand_value)
        return result

    def __del__(self):
        try:
            self.left(False)
            self.right(False)
            self.middle(False)
            self.unmask_all()
            if self.monitor:
                self.monitor.stop()
            self._sock.close()
        except Exception:
            print("KmboxNet, Failed to close!")
            pass
class KmboxError(Exception):
    """KmboxNet related errors"""
    pass
