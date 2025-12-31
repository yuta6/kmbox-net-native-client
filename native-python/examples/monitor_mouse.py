import time
from kmboxnet import KmboxNet
from examples.ip_port_uuid import IP, PORT, UUID

kmbox = KmboxNet(ip=IP, port=PORT, uuid=UUID)

try:
    for i in range(200):
        time.sleep(0.01)
        
        if kmbox.monitor.left:
            print("Left button pressed!")
        if kmbox.monitor.right:
            print("Right button pressed!")
        if kmbox.monitor.middle:
            print("Middle button pressed!")
        if kmbox.monitor.side1:
            print("Side1 button pressed!")
        if kmbox.monitor.side2:
            print("Side2 button pressed!")
        
        x, y = kmbox.monitor.move
        if x != 0 or y != 0:
            print(f"Mouse moved: ({x}, {y})")
        
        wheel = kmbox.monitor.wheel
        if wheel != 0:
            print(f"Wheel: {wheel}")

except KeyboardInterrupt:
    print("\nTest stopped.")

