import time

from kmboxnet import Kmbox
from ip_port_uuid import IP, PORT, UUID

mouse = Kmbox(ip=IP, port=PORT, uuid=UUID)

while True :
    print(mouse.monitor.hard_mouse, mouse.monitor.hard_keyboard)
    time.sleep(0.001)
