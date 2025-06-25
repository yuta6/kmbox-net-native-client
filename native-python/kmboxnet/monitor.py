import socket
import threading

CMD_CONNECT     = 0xAF3C2828
CMD_MONITOR     = 0x27388020
CMD_MOUSE_MOVE  = 0xAEDE7345
CMD_MOUSE_RIGHT = 0x238D8212

# 例外定義
class KmboxError(Exception):
    pass

class CreateSocketError(KmboxError):
    pass

class TimeoutError(KmboxError):
    pass

class CommandError(KmboxError):
    pass

class MonitorError(KmboxError):
    pass

class Monitor:
    def __init__(self, port: int):
        self.port = port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._mouse_buttons = 0   
        self._keyboard_byte = 0   

    def start(self):
        if self._running:
            return
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", self.port))
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._sock:
            self._sock.close()
        if self._thread:
            self._thread.join()

    def _listen(self):
        while self._running:
            try:
                data, _ = self._sock.recvfrom(1024)
            except OSError:
                break
            if len(data) < 20:
                continue
            mb = data[1]
            kb = data[9]
            self._mouse_buttons = mb
            self._keyboard_byte = kb

    @property
    def is_mouse_left(self) -> bool:
        if not self._running:
            raise MonitorError("Monitor not started")
        return bool(self._mouse_buttons & 0x01)

    @property
    def is_mouse_right(self) -> bool:
        if not self._running:
            raise MonitorError("Monitor not started")
        return bool(self._mouse_buttons & 0x02)

    @property
    def is_mouse_middle(self) -> bool:
        if not self._running:
            raise MonitorError("Monitor not started")
        return bool(self._mouse_buttons & 0x04)

    def get_keyboard_state(self) -> int:
        if not self._running:
            raise MonitorError("Monitor not started")
        return self._keyboard_byte
