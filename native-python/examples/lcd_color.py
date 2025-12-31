import time
from kmboxnet import KmboxNet
from examples.ip_port_uuid import IP, PORT, UUID

km = KmboxNet(ip=IP, port=PORT, uuid=UUID)

RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F

print("LCD color test...")

print("Red")
km.lcd_color(RED)
time.sleep(1)

print("Green")
km.lcd_color(GREEN)
time.sleep(1)

print("Blue")
km.lcd_color(BLUE)
time.sleep(1)

print("\nDone")