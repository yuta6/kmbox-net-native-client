import threading
import socket
from dataclasses import dataclass, field
from typing import Optional
import struct
import queue
import time


@dataclass
class HardMouse:
    report_id: int = 0
    buttons: int = 0
    x: int = 0
    y: int = 0
    wheel: int = 0
    time_stamp: float = 0


@dataclass
class HardKeyboard:
    report_id: int = 0
    buttons: int = 0
    data: list[int] = field(default_factory=lambda: [0] * 10)


@dataclass
class Event:
    mouse: HardMouse
    keyboard: HardKeyboard


class Monitor:
    def __init__(self, port: int, monitor_timeout: Optional[float] = 0.003):
        self.port = port
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None

        self.hard_mouse = HardMouse()
        self.hard_keyboard = HardKeyboard()

        self.events = queue.Queue()

        self.is_neutral_event_sent = False
        self.monitor_timeout = monitor_timeout

        self._lock = threading.Lock()

    def start(self):
        """monitor start"""
        if self.running:
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(self.monitor_timeout)
            self.sock.bind(("0.0.0.0", self.port))

            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()

        except Exception as e:
            self.running = False
            if self.sock:
                self.sock.close()
                self.sock = None
            raise KmboxNetMonitorError(f"Monitor start failed: {e}")

    def stop(self):
        """monitor stop"""
        self.running = False

        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _listen_loop(self):
        """monitor loop"""
        try:
            while self.running and self.sock:
                try:
                    data, _addr = self.sock.recvfrom(1024)
                except socket.timeout:
                    if self.is_neutral_event_sent:
                        continue

                    with self._lock:
                        neutral_mouse = HardMouse(
                            report_id=self.hard_mouse.report_id,
                            buttons=self.hard_mouse.buttons,
                            x=0,
                            y=0,
                            wheel=self.hard_mouse.wheel,
                            time_stamp=time.perf_counter(),
                        )
                        current_keyboard = self.hard_keyboard

                        self.hard_mouse = neutral_mouse
                        self.hard_keyboard = current_keyboard
                        self.events.put(Event(neutral_mouse, current_keyboard))

                    self.is_neutral_event_sent = True
                    continue
                except OSError as e:
                    if self.running:
                        print(f"Monitor receive error: {e}")
                    break

                try:
                    new_mouse, new_keyboard = self._build_mouse_and_keyboard_from_data(
                        data
                    )
                except (ValueError, struct.error):
                    continue

                with self._lock:
                    self.events.put(Event(new_mouse, new_keyboard))
                    self.hard_mouse = new_mouse
                    self.hard_keyboard = new_keyboard

                self.last_event_time = time.perf_counter()
                self.is_neutral_event_sent = False

        except Exception as e:
            print(f"Monitor loop error: {e}")
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass

    def _build_mouse_and_keyboard_from_data(
        self, data: bytes
    ) -> tuple[HardMouse, HardKeyboard]:
        if len(data) < 20:
            raise ValueError(f"insufficient monitor packet: {len(data)} bytes")

        # Mouse Parse 8 bytes
        # struct: report_id(1) + buttons(1) + x(2) + y(2) + wheel(2)
        report_id, buttons, x, y, wheel = struct.unpack_from("<BBhhh", data, 0)
        new_mouse = HardMouse(
            report_id=report_id,
            buttons=buttons,
            x=x,
            y=y,
            wheel=wheel,
            time_stamp=time.perf_counter(),
        )

        # Keyboard parse 12 bytes
        # struct: report_id(1) + buttons(1) + data[10](10)
        k_report_id, k_buttons, *k_data = struct.unpack_from("<BB10B", data, 8)
        new_keyboard = HardKeyboard(
            report_id=k_report_id,
            buttons=k_buttons,
            data=list(k_data),
        )

        return new_mouse, new_keyboard

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


class KmboxNetMonitorError(Exception):
    """Monitor related errors"""

    pass
