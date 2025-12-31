import time

from kmboxnet import Event, KmboxNet
from tests.ip_port_uuid import IP, PORT, UUID

mouse = KmboxNet(ip=IP, port=PORT, uuid=UUID, monitor_timeout=0.01)

current_time = time.perf_counter()
time.sleep(1)
index = 0
while time.perf_counter() - current_time < 5.0:
    index += 1
    event: Event = mouse.monitor.events.get()
    length = mouse.monitor.events.qsize()
    print(f"index :{index}, length :{length}, {event.mouse}, {event.keyboard}")
