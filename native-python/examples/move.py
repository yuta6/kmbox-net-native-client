import time

from kmboxnet import KmboxNet
from examples.ip_port_uuid import IP, PORT, UUID

mouse = KmboxNet(ip=IP, port=PORT, uuid=UUID)

while True:
    mouse.move(150, 0)
    time.sleep(1)
    mouse.move(0, 150)
    time.sleep(1)
    mouse.move(-150, 0)
    time.sleep(1)
    mouse.move(0, -150)
    time.sleep(1)

