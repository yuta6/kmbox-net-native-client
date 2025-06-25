import time

from kmboxnet import Kmbox

ip=""
port=0
uuid=""

mouse = Kmbox(ip, port, uuid)

while True :
    mouse.move(150,0)
    time.sleep(1)
    mouse.move(0,150)
    time.sleep(1)
    mouse.move(-150,0)
    time.sleep(1)
    mouse.move(0,-150)
    time.sleep(1)
