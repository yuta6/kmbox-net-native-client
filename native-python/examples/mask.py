import time

from examples.ip_port_uuid import IP, PORT, UUID
from kmboxnet import KmboxNet


km = KmboxNet(ip=IP, port=PORT, uuid=UUID, monitor_port=None)

try:
    print("mask_x(True) for 3 sec")
    km.mask_x(True)
    time.sleep(3)
    km.mask_x(False)

    print("mask_y(True) for 3 sec")
    km.mask_y(True)
    time.sleep(3)
    km.mask_y(False)

    print("done")
except KeyboardInterrupt:
    pass
finally:
    try:
        km.unmask_all()
    except Exception:
        pass
