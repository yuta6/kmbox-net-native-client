import time
from kmboxnet import KmboxNet
from examples.ip_port_uuid import IP, PORT, UUID

kmbox = KmboxNet(ip=IP, port=PORT, uuid=UUID)
monitor = kmbox.monitor

KEY_MAP = {
    0x04: "A",
    0x05: "B",
    0x06: "C",
    0x07: "D",
    0x08: "E",
    0x09: "F",
    0x0A: "G",
    0x0B: "H",
    0x16: "S",
    0x1A: "W",
    0x17: "T",
    0x2C: "Space",
    0x28: "Enter",
    0x29: "Esc",
}

MODIFIER_MAP = {
    0xE0: "LCtrl",
    0xE1: "LShift",
    0xE2: "LAlt",
    0xE3: "LWin",
    0xE4: "RCtrl",
    0xE5: "RShift",
    0xE6: "RAlt",
    0xE7: "RWin",
}

try:
    for i in range(200):
        time.sleep(0.01)

        pressed_keys = []

        for vkey, name in MODIFIER_MAP.items():
            if monitor.get_keyboard(vkey):
                pressed_keys.append(name)

        for vkey, name in KEY_MAP.items():
            if monitor.get_keyboard(vkey):
                pressed_keys.append(name)

        if pressed_keys:
            print(f"Keys: {' + '.join(pressed_keys)}")

except KeyboardInterrupt:
    print("\nTest stopped.")
