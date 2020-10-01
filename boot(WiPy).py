import os
from machine import UART
uart = UART(0, 115200)
os.dupterm(uart)

exec(open("/flash/netconfig.py").read())
