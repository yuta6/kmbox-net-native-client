import time

from kmboxnet import KmboxNet
from tests.ip_port_uuid import IP, PORT, UUID

mouse = KmboxNet(ip=IP, port=PORT, uuid=UUID)

while True:
    print(mouse.monitor.hard_mouse, mouse.monitor.hard_keyboard)
    time.sleep(0.001)
