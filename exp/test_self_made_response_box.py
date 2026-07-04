import time

import serial
from serial.tools import list_ports


def find_port():
    for port in list_ports.comports():
        if port.device.startswith(("/dev/ttyACM", "/dev/ttyUSB")):
            return port.device
    return "/dev/ttyACM0"


port_name = find_port()

with serial.Serial(port_name, 115200, timeout=0.1) as box:
    time.sleep(2)
    box.reset_input_buffer()
    box.write(b"S")
    box.flush()

    print(f"Sent S to {port_name}. Press a button; Ctrl+C to quit.")

    try:
        while True:
            line = box.readline().decode("ascii", errors="replace").strip()
            if line:
                print(line)
                box.write(b"S")
                box.flush()
    except KeyboardInterrupt:
        print("\nDone.")
