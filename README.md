## Python Package for the Adaura Technologies Programmable RF Attenuators

This Python package provides a simple interface for controlling Adaura Technologies programmable RF attenuators. With just a few lines of code, you can set attenuation levels, automate test sequences, and integrate the attenuator into your measurement workflows. Programmable attenuators are especially useful for tasks such as determining the sensitivity of wireless receivers or verifying the accuracy of vendor-reported metrics like RSSI and SNR. This package streamlines these processes, making it easy to script and repeat your RF measurements.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install git+https://github.zhaw.ch/InES/AdauraAttenuator.git
```

or

```bash
pip install --user --break-system-packages git+https://github.zhaw.ch/InES/AdauraAttenuator.git
```

## Quick Start

Example Script
```python
from adaura_attenuator import AdauraAttenuator
import time

found_attenuators = AdauraAttenuator.find_attenuators()

print(f"Found attenuators: {found_attenuators}")

if len(found_attenuators) == 0:
    exit(1)

found_attenuator = found_attenuators[0]
attenuator = AdauraAttenuator(serial_number=found_attenuator[0],comport=found_attenuator[1])
print(f"Attenuator Info: {attenuator.get_info()}")

attenuator.locate()

attenuator.set_attenuator(0,3)
print(f"Attenuator Status: {attenuator.get_status()}")

attenuator.set_all_attenuators(90)
print(f"Attenuator Status: {attenuator.get_status()}")

wait = attenuator.ramp_attenuators('D', low=0, high=90, step=10, step_time=1, mode='non-blocking')
print(f"Ramp time for {wait} seconds...")
time.sleep(wait)
print(f"Attenuator Status: {attenuator.get_status()}")

attenuator.ramp_attenuators('A', low=0, high=90, step=10, step_time=500, mode='blocking')
print(f"Attenuator Status: {attenuator.get_status()}")

# Example of using a command not implemented in the class
attenuator.send_command("RAND 1 0 90")
time.sleep(0.1)
print(f"Attenuator Status: {attenuator.get_status()}")
```

<details>
<summary>
Message Driven Attenuation Script
</summary>

```python
from adaura_attenuator import AdauraAttenuator
import serial
import sys
import time

def progressbar(it, prefix="", size=60, out=sys.stdout):
    count = len(it)
    start = time.time() # time estimate start
    def show(j):
        x = int(size*j/count)
        # time estimate calculation and string
        remaining = ((time.time() - start) / j) * (count - j)
        days, rem = divmod(remaining, 86400)
        hours, rem = divmod(rem, 3600)
        mins, sec = divmod(rem, 60)
        time_str = f"{int(days):02}d:{int(hours):02}h:{int(mins):02}m:{sec:04.1f}s"
        print(f"{prefix}[{u'█'*x}{('.'*(size-x))}] {j}/{count} Est wait {time_str}", end='\r', file=out, flush=True)
    show(0.1) # avoid div/0 
    for i, item in enumerate(it):
        yield item
        show(i+1)
    print("\n", flush=True, file=out)


# Define attenuations
attenuations = [0,5,10,15,20,25,30,30.25,30.5,30.75]


# Connect to the Adaura attenuator
found_attenuators = AdauraAttenuator.find_attenuators(pid=0xECA8)
print(f"Found attenuators: {found_attenuators}")
if len(found_attenuators) == 0:
    exit(1)
found_attenuator = found_attenuators[0]
attenuator = AdauraAttenuator(serial_number=found_attenuator[0],comport=found_attenuator[1])
attenuator.set_all_attenuators(attenuations[0])
print(f"Attenuator Status: {attenuator.get_status()}")


# Connect to the DUT node
dut_node = serial.Serial('/dev/serial/by-id/usb-SEGGER_J-Link_*', 115200, timeout=1)


# Go through the attenuations
print("Starting attenuation ramp...")
print(f"Current time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
line = b''
for i in progressbar(range(len(attenuations)), "Running: ", 60):
    while True:
        line = dut_node.readline()
        if "next_attenuation" in line.decode('utf-8'):
            attenuator.set_all_attenuators(attenuations[i])
            break
        
print("Done.")
print(f"Attenuator Status: {attenuator.get_status()}")
print(f"Current time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
```
</details>
