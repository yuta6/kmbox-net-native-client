import time

from kmboxnet import Kmbox , HardMouse, HardKeyboard
from ip_port_uuid import IP, PORT, UUID

mouse = Kmbox(ip=IP, port=PORT, uuid=UUID)

while True :
    events : dict  = mouse.monitor.events.get()
    if "mouse" in events:
        ms = events["mouse"]
        print(ms.report_id, ms.buttons, ms.x, ms.y, ms.wheel)
    else :
        print("No mouse data available")

    print()
