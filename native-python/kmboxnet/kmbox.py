import socket
import struct
import random
import threading

from .monitor import Monitor,MonitorError

HID_TABLE = {
    'KEY_NONE': 0x00,
    'KEY_ERRORROLLOVER': 0x01,
    'KEY_POSTFAIL': 0x02,
    'KEY_ERRORUNDEFINED': 0x03,
    'KEY_A': 0x04,
    'KEY_B': 0x05,
    'KEY_C': 0x06,
    'KEY_D': 0x07,
    'KEY_E': 0x08,
    'KEY_F': 0x09,
    'KEY_G': 0x0A,
    'KEY_H': 0x0B,
    'KEY_I': 0x0C,
    'KEY_J': 0x0D,
    'KEY_K': 0x0E,
    'KEY_L': 0x0F,
    'KEY_M': 0x10,
    'KEY_N': 0x11,
    'KEY_O': 0x12,
    'KEY_P': 0x13,
    'KEY_Q': 0x14,
    'KEY_R': 0x15,
    'KEY_S': 0x16,
    'KEY_T': 0x17,
    'KEY_U': 0x18,
    'KEY_V': 0x19,
    'KEY_W': 0x1A,
    'KEY_X': 0x1B,
    'KEY_Y': 0x1C,
    'KEY_Z': 0x1D,
    'KEY_1_EXCLAMATION_MARK': 0x1E,
    'KEY_2_AT': 0x1F,
    'KEY_3_NUMBER_SIGN': 0x20,
    'KEY_4_DOLLAR': 0x21,
    'KEY_5_PERCENT': 0x22,
    'KEY_6_CARET': 0x23,
    'KEY_7_AMPERSAND': 0x24,
    'KEY_8_ASTERISK': 0x25,
    'KEY_9_OPARENTHESIS': 0x26,
    'KEY_0_CPARENTHESIS': 0x27,
    'KEY_ENTER': 0x28,
    'KEY_ESCAPE': 0x29,
    'KEY_BACKSPACE': 0x2A,
    'KEY_TAB': 0x2B,
    'KEY_SPACEBAR': 0x2C,
    'KEY_MINUS_UNDERSCORE': 0x2D,
    'KEY_EQUAL_PLUS': 0x2E,
    'KEY_OBRACKET_AND_OBRACE': 0x2F,
    'KEY_CBRACKET_AND_CBRACE': 0x30,
    'KEY_BACKSLASH_VERTICAL_BAR': 0x31,
    'KEY_NONUS_NUMBER_SIGN_TILDE': 0x32,
    'KEY_SEMICOLON_COLON': 0x33,
    'KEY_SINGLE_AND_DOUBLE_QUOTE': 0x34,
    'KEY_GRAVE_ACCENT_AND_TILDE': 0x35,
    'KEY_COMMA_AND_LESS': 0x36,
    'KEY_DOT_GREATER': 0x37,
    'KEY_SLASH_QUESTION': 0x38,
    'KEY_CAPS_LOCK': 0x39,
    'KEY_F1': 0x3A,
    'KEY_F2': 0x3B,
    'KEY_F3': 0x3C,
    'KEY_F4': 0x3D,
    'KEY_F5': 0x3E,
    'KEY_F6': 0x3F,
    'KEY_F7': 0x40,
    'KEY_F8': 0x41,
    'KEY_F9': 0x42,
    'KEY_F10': 0x43,
    'KEY_F11': 0x44,
    'KEY_F12': 0x45,
    'KEY_PRINTSCREEN': 0x46,
    'KEY_SCROLL_LOCK': 0x47,
    'KEY_PAUSE': 0x48,
    'KEY_INSERT': 0x49,
    'KEY_HOME': 0x4A,
    'KEY_PAGEUP': 0x4B,
    'KEY_DELETE': 0x4C,
    'KEY_END1': 0x4D,
    'KEY_PAGEDOWN': 0x4E,
    'KEY_RIGHTARROW': 0x4F,
    'KEY_LEFTARROW': 0x50,
    'KEY_DOWNARROW': 0x51,
    'KEY_UPARROW': 0x52,
    'KEY_KEYPAD_NUM_LOCK_AND_CLEAR': 0x53,
    'KEY_KEYPAD_SLASH': 0x54,
    'KEY_KEYPAD_ASTERISK': 0x55,
    'KEY_KEYPAD_MINUS': 0x56,
    'KEY_KEYPAD_PLUS': 0x57,
    'KEY_KEYPAD_ENTER': 0x58,
    'KEY_KEYPAD_1_END': 0x59,
    'KEY_KEYPAD_2_DOWN_ARROW': 0x5A,
    'KEY_KEYPAD_3_PAGEDN': 0x5B,
    'KEY_KEYPAD_4_LEFT_ARROW': 0x5C,
    'KEY_KEYPAD_5': 0x5D,
    'KEY_KEYPAD_6_RIGHT_ARROW': 0x5E,
    'KEY_KEYPAD_7_HOME': 0x5F,
    'KEY_KEYPAD_8_UP_ARROW': 0x60,
    'KEY_KEYPAD_9_PAGEUP': 0x61,
    'KEY_KEYPAD_0_INSERT': 0x62,
    'KEY_KEYPAD_DECIMAL_SEPARATOR_DELETE': 0x63,
    'KEY_NONUS_BACK_SLASH_VERTICAL_BAR': 0x64,
    'KEY_APPLICATION': 0x65,
    'KEY_POWER': 0x66,
    'KEY_KEYPAD_EQUAL': 0x67,
    'KEY_F13': 0x68,
    'KEY_F14': 0x69,
    'KEY_F15': 0x6A,
    'KEY_F16': 0x6B,
    'KEY_F17': 0x6C,
    'KEY_F18': 0x6D,
    'KEY_F19': 0x6E,
    'KEY_F20': 0x6F,
    'KEY_F21': 0x70,
    'KEY_F22': 0x71,
    'KEY_F23': 0x72,
    'KEY_F24': 0x73,
    'KEY_EXECUTE': 0x74,
    'KEY_HELP': 0x75,
    'KEY_MENU': 0x76,
    'KEY_SELECT': 0x77,
    'KEY_STOP': 0x78,
    'KEY_AGAIN': 0x79,
    'KEY_UNDO': 0x7A,
    'KEY_CUT': 0x7B,
    'KEY_COPY': 0x7C,
    'KEY_PASTE': 0x7D,
    'KEY_FIND': 0x7E,
    'KEY_MUTE': 0x7F,
    'KEY_VOLUME_UP': 0x80,
    'KEY_VOLUME_DOWN': 0x81,
    'KEY_LOCKING_CAPS_LOCK': 0x82,
    'KEY_LOCKING_NUM_LOCK': 0x83,
    'KEY_LOCKING_SCROLL_LOCK': 0x84,
    'KEY_KEYPAD_COMMA': 0x85,
    'KEY_KEYPAD_EQUAL_SIGN': 0x86,
    'KEY_INTERNATIONAL1': 0x87,
    'KEY_INTERNATIONAL2': 0x88,
    'KEY_INTERNATIONAL3': 0x89,
    'KEY_INTERNATIONAL4': 0x8A,
    'KEY_INTERNATIONAL5': 0x8B,
    'KEY_INTERNATIONAL6': 0x8C,
    'KEY_INTERNATIONAL7': 0x8D,
    'KEY_INTERNATIONAL8': 0x8E,
    'KEY_INTERNATIONAL9': 0x8F,
    'KEY_LANG1': 0x90,
    'KEY_LANG2': 0x91,
    'KEY_LANG3': 0x92,
    'KEY_LANG4': 0x93,
    'KEY_LANG5': 0x94,
    'KEY_LANG6': 0x95,
    'KEY_LANG7': 0x96,
    'KEY_LANG8': 0x97,
    'KEY_LANG9': 0x98,
    'KEY_ALTERNATE_ERASE': 0x99,
    'KEY_SYSREQ': 0x9A,
    'KEY_CANCEL': 0x9B,
    'KEY_CLEAR': 0x9C,
    'KEY_PRIOR': 0x9D,
    'KEY_RETURN': 0x9E,
    'KEY_SEPARATOR': 0x9F,
    'KEY_OUT': 0xA0,
    'KEY_OPER': 0xA1,
    'KEY_CLEAR_AGAIN': 0xA2,
    'KEY_CRSEL': 0xA3,
    'KEY_EXSEL': 0xA4,
    'KEY_KEYPAD_00': 0xB0,
    'KEY_KEYPAD_000': 0xB1,
    'KEY_THOUSANDS_SEPARATOR': 0xB2,
    'KEY_DECIMAL_SEPARATOR': 0xB3,
    'KEY_CURRENCY_UNIT': 0xB4,
    'KEY_CURRENCY_SUB_UNIT': 0xB5,
    'KEY_KEYPAD_OPARENTHESIS': 0xB6,
    'KEY_KEYPAD_CPARENTHESIS': 0xB7,
    'KEY_KEYPAD_OBRACE': 0xB8,
    'KEY_KEYPAD_CBRACE': 0xB9,
    'KEY_KEYPAD_TAB': 0xBA,
    'KEY_KEYPAD_BACKSPACE': 0xBB,
    'KEY_KEYPAD_A': 0xBC,
    'KEY_KEYPAD_B': 0xBD,
    'KEY_KEYPAD_C': 0xBE,
    'KEY_KEYPAD_D': 0xBF,
    'KEY_KEYPAD_E': 0xC0,
    'KEY_KEYPAD_F': 0xC1,
    'KEY_KEYPAD_XOR': 0xC2,
    'KEY_KEYPAD_CARET': 0xC3,
    'KEY_KEYPAD_PERCENT': 0xC4,
    'KEY_KEYPAD_LESS': 0xC5,
    'KEY_KEYPAD_GREATER': 0xC6,
    'KEY_KEYPAD_AMPERSAND': 0xC7,
    'KEY_KEYPAD_LOGICAL_AND': 0xC8,
    'KEY_KEYPAD_VERTICAL_BAR': 0xC9,
    'KEY_KEYPAD_LOGICAL_OR': 0xCA,
    'KEY_KEYPAD_COLON': 0xCB,
    'KEY_KEYPAD_NUMBER_SIGN': 0xCC,
    'KEY_KEYPAD_SPACE': 0xCD,
    'KEY_KEYPAD_AT': 0xCE,
    'KEY_KEYPAD_EXCLAMATION_MARK': 0xCF,
    'KEY_KEYPAD_MEMORY_STORE': 0xD0,
    'KEY_KEYPAD_MEMORY_RECALL': 0xD1,
    'KEY_KEYPAD_MEMORY_CLEAR': 0xD2,
    'KEY_KEYPAD_MEMORY_ADD': 0xD3,
    'KEY_KEYPAD_MEMORY_SUBTRACT': 0xD4,
    'KEY_KEYPAD_MEMORY_MULTIPLY': 0xD5,
    'KEY_KEYPAD_MEMORY_DIVIDE': 0xD6,
    'KEY_KEYPAD_PLUSMINUS': 0xD7,
    'KEY_KEYPAD_CLEAR': 0xD8,
    'KEY_KEYPAD_CLEAR_ENTRY': 0xD9,
    'KEY_KEYPAD_BINARY': 0xDA,
    'KEY_KEYPAD_OCTAL': 0xDB,
    'KEY_KEYPAD_DECIMAL': 0xDC,
    'KEY_KEYPAD_HEXADECIMAL': 0xDD,
    'KEY_LEFTCONTROL': 0xE0,
    'KEY_LEFTSHIFT': 0xE1,
    'KEY_LEFTALT': 0xE2,
    'KEY_LEFT_GUI': 0xE3,
    'KEY_RIGHTCONTROL': 0xE4,
    'KEY_RIGHTSHIFT': 0xE5,
    'KEY_RIGHTALT': 0xE6,
    'KEY_RIGHT_GUI': 0xE7,
    'BIT0': 0x01,
    'BIT1': 0x02,
    'BIT2': 0x04,
    'BIT3': 0x08,
    'BIT4': 0x10,
    'BIT5': 0x20,
    'BIT6': 0x40,
    'BIT7': 0x80,
}

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
    def __init__(self, ip: str, port: int, uuid: str, monitor_port:int|None = 5002, timeout: float = 2.0):
        """
        :param ip: Kmbox IP Adress
        :param port: Kmbox Port 
        :param mac_str: Kmbox UUID
        :param timeout: socket receive timeout 
        """
        self.timeout = timeout

        # mac address generation from uuid
        try:
            mac_bytes = bytes.fromhex(uuid)
            if len(mac_bytes) != 4:
                raise ValueError
            self.mac = int.from_bytes(mac_bytes, byteorder='big')
        except ValueError:
            raise CreateSocketError("UUID is 8 degits.")

        # key
        self.key = list(mac_bytes)
        self.index = 0

        # define sokect
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(self.timeout)
            self.server = (ip, port)
        except Exception as e:
            raise CreateSocketError(f"Failture: {e}")

        # send connectet command
        self._send_head(CMD_CONNECT)

        # receive response
        try:
            data, _ = self.sock.recvfrom(1024)
        except socket.timeout:
            raise TimeoutError("Timeout")

        # response check
        _, _, resp_index, resp_cmd = struct.unpack("<IIII", data[:16])
        if resp_cmd != CMD_CONNECT or resp_index != self.index:
            raise CommandError("Invalid Response")
        
        # start monitor
        self._monitor: Monitor | None = None
        if monitor_port is not None:
            try:
                self._monitor = Monitor(monitor_port)
                self._monitor.start()
                rand = monitor_port | (0xAA55 << 16)
                self._send_head(CMD_MONITOR, rand_override=rand)
                data, _ = self.sock.recvfrom(1024)
                _, _, ri, rc = struct.unpack("<IIII", data[:16])
                if rc != CMD_MONITOR or ri != self.index:
                    raise CommandError("monitor start failed")
            except Exception as e:
                #　if failture, warning only
                print(f"[Warning] monitor start error: {e}")

    def _make_head(self, cmd: int, rand: int | None = None) -> bytes:
        if rand is None:
            rand = random.randint(0, 0x7FFFFFFF)
        return struct.pack("<IIII", self.mac, rand, self.index, cmd)

    def _send_head(self, cmd: int, rand_override: int | None = None) -> None:
        self.index += 1
        if rand_override is None:
            rand = random.randint(0, 0x7FFFFFFF)
        else:
            rand = rand_override
        head = self._make_head(cmd, rand)
        self.sock.sendto(head, self.server)

    def mouse_move(self, x: int, y: int) -> None:
        """
        move mouse
        """
        if not hasattr(self, '_lock'):
            self._lock = threading.Lock()
        if not self._lock.acquire(timeout=self.timeout):
            raise CreateSocketError("Failture Lock")
        try:
            # create header
            self.index += 1
            head = self._make_head(CMD_MOUSE_MOVE)

            # soft_mouse_t struct: 14 int (button, x, y, wheel, point[10])
            payload = struct.pack(
                "<14i",
                0,   # button
                x,
                y,
                0,   # wheel
                *([0]*10)
            )
            self.sock.sendto(head + payload, self.server)

            # receive response
            try:
                data, _ = self.sock.recvfrom(1024)
            except socket.timeout:
                raise TimeoutError("Timeout")

            _, _, resp_index, resp_cmd = struct.unpack("<IIII", data[:16])
            if resp_cmd != CMD_MOUSE_MOVE or resp_index != self.index:
                raise CommandError("Failture")

        finally:
            self._lock.release()

    @property
    def is_mouse_left(self) -> bool:
        if not self._monitor:
            raise MonitorError("monitor not configured")
        return self._monitor.is_mouse_left

    @property
    def is_mouse_middle(self) -> bool:
        if not self._monitor:
            raise MonitorError("monitor not configured")
        return self._monitor.is_mouse_middle

    @property
    def is_mouse_right(self) -> bool:
        if not self._monitor:
            raise MonitorError("monitor not configured")
        return self._monitor.is_mouse_right


class KmboxError(Exception):
    pass

class CreateSocketError(KmboxError):
    pass

class TimeoutError(KmboxError):
    pass

class CommandError(KmboxError):
    pass
