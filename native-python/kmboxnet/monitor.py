import threading
import socket
from dataclasses import dataclass, field
from typing import Optional
import struct

@dataclass
class HardMouse:
    report_id: int = 0
    buttons: int = 0
    x: int = 0
    y: int = 0
    wheel: int = 0

@dataclass
class HardKeyboard:
    report_id: int = 0
    buttons: int = 0
    data: list[int] = field(default_factory=lambda: [0] * 10)

class Monitor:
    TIMEOUT = 2.0

    def __init__(self, port: int):
        self.port = port
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None

        self.hard_mouse = HardMouse()
        self.hard_keyboard = HardKeyboard()

        self._lock = threading.Lock()

    def start(self):
        """monitor start"""
        if self.running:
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(self.TIMEOUT)
            self.sock.bind(('0.0.0.0', self.port))

            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()

        except Exception as e:
            self.running = False
            if self.sock:
                self.sock.close()
                self.sock = None
            raise MonitorError(f"Monitor start failed: {e}")

    def stop(self):
        """monitor stop"""
        self.running = False

        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _listen_loop(self):
        """monitor loop"""
        try:
            while self.running and self.sock:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    if len(data) >= 7:
                        self._update_hard(data)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Monitor receive error: {e}")
                    break

        except Exception as e:
            print(f"Monitor loop error: {e}")
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass

    def _update_hard(self, data: bytes):
        try:
            with self._lock:
                if len(data) < 8:
                    print(f"Insufficient data for mouse: {len(data)} bytes")
                    return

                # Mouse Parse 8byte
                # struct: report_id(1) + buttons(1) + x(2) + y(2) + wheel(2)
                mouse_data = struct.unpack("<BBhhh", data[:8])
                self.hard_mouse.report_id = mouse_data[0]
                self.hard_mouse.buttons = mouse_data[1]
                self.hard_mouse.x = mouse_data[2]
                self.hard_mouse.y = mouse_data[3]
                self.hard_mouse.wheel = mouse_data[4]

                # keyboard parse 12byte
                if len(data) >= 20:  # 8(mouse) + 12(keyboard)
                    # struct: report_id(1) + buttons(1) + data[10](10)
                    keyboard_data = struct.unpack("<BB10B", data[8:20])
                    self.hard_keyboard.report_id = keyboard_data[0]
                    self.hard_keyboard.buttons = keyboard_data[1]
                    self.hard_keyboard.data = list(keyboard_data[2:])
                elif len(data) >= 8:
                    print(f"Only mouse data available: {len(data)} bytes")

        except struct.error as e:
            print(f"Data parse error: {e}, data length: {len(data)}")

    @property
    def left(self) -> bool:
        with self._lock:
            return bool(self.hard_mouse.buttons & 0x01)

    @property
    def right(self) -> bool:
        with self._lock:
            return bool(self.hard_mouse.buttons & 0x02)

    @property
    def middle(self) -> bool:
        with self._lock:
            return bool(self.hard_mouse.buttons & 0x04)

    @property
    def side1(self) -> bool:
        with self._lock:
            return bool(self.hard_mouse.buttons & 0x08)

    @property
    def side2(self) -> bool:
        with self._lock:
            return bool(self.hard_mouse.buttons & 0x10)

    def get_keyboard(self, vkey: int) -> bool:
        with self._lock:
            if 0xE0 <= vkey <= 0xE7:
                bit_pos = vkey - 0xE0
                return bool(self.hard_keyboard.buttons & (1 << bit_pos))
            else:
                return vkey in self.hard_keyboard.data

    @property
    def move(self) -> tuple[int, int]:
        with self._lock:
            return (self.hard_mouse.x, self.hard_mouse.y)

    @property
    def wheel(self) -> int:
        with self._lock:
            return self.hard_mouse.wheel

    @property
    def is_running(self) -> bool:
        return self.running

class MonitorError(Exception):
    pass

class MonitorError(Exception):
    pass
