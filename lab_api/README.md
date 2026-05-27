# Lab API - Device Control Library

A Python library for controlling lab instruments via Ethernet. Provides stable, blocking SCPI-based drivers for power supplies, multimeters, and electronic DC loads with Flask REST API endpoints.

## Overview

This library includes drivers for three device types:

- **PSU Device (MP711001)**: 4-channel programmable power supply (TCP)
- **Multimeter Device (MP730027)**: Digital multimeter with multiple measurement modes (TCP)
- **DC Load Device (MP71077x)**: Electronic DC load with CC/CV/CP/CR modes (UDP)

All drivers use SCPI (Standard Commands for Programmable Instruments) over Ethernet with automatic reconnection and error handling.

## Project Structure

```
lab_api/
├── README.md                   (this file)
├── demo.py                     (example usage)
├── psu_device/
│   ├── __init__.py
│   ├── mp711001.py             (PSU driver)
│   ├── flask_app.py            (REST API)
│   └── README.md
├── multimeter_device/
│   ├── __init__.py
│   ├── mp730027.py             (Multimeter driver)
│   ├── flask_app.py            (REST API)
│   └── README.md
└── dcload_device/
    ├── __init__.py
    ├── mp71077x.py             (DC Load driver)
    ├── flask_app.py            (REST API)
    └── README.md
```

## Quick Start

### Python Library Usage

```python
from psu_device import MP711001
from multimeter_device import MP730027
from dcload_device import MP71077x

# Initialize devices
psu = MP711001("192.168.1.100")         # TCP, port 5025
mm = MP730027("192.168.1.99", port=3000)
dcload = MP71077x("192.168.1.80")       # UDP, port 18190

# Set PSU voltage and enable output
psu.set_voltage(1, 5.0)
psu.set_current(1, 2.0)
psu.output_on(1)

# Set DC load to draw 1A in constant current mode
dcload.set_mode_current()
dcload.set_ci_current(1.0)
dcload.load_on()

# Measure with multimeter
voltage = mm.measure_dc_voltage()
print(f"Measured voltage: {voltage}V")

# Read back from load
result = dcload.measure()
print(f"Load sees: {result['voltage']}V, {result['current']}A")

# Clean up
dcload.load_off()
psu.output_off(1)
```

### Running REST API Servers

Each device package includes a Flask app. Run from the project root:

```bash
# PSU (port 5000)
python dcload_device/flask_app.py

# DC Load (port 5000 — change per device as needed)
python dcload_device/flask_app.py
```

Or as a module from inside the package directory:

```bash
cd dcload_device
python -m flask --app flask_app run --port 5002
```

## Device Notes

### MP71077x DC Load

The DC load uses **UDP** (not TCP) and binds to the local port on construction. The default port is **18190**. No `openSocket()`/`closeSocket()` calls are needed — the driver manages the socket automatically.

Supported modes: CC (constant current), CV (constant voltage), CP (constant power), CR (constant resistance).

All setters accept an optional `verify=True` parameter that reads back the value and raises `ConnectionError` if it doesn't match.

```python
dcload = MP71077x("192.168.1.80")           # port=18190, timeout=0.5

dcload.set_mode_current()
dcload.set_ci_current(2.0, verify=True)     # raises if not confirmed
dcload.load_on()

result = dcload.measure()                   # {"voltage": 4.98, "current": 1.99}
```

### MP711001 PSU

4-channel TCP device. Each command takes a channel argument (1–4).

```python
psu = MP711001("192.168.1.100")             # port=5025, timeout=2

psu.set_voltage(1, 5.0)
psu.set_current(1, 2.0)
psu.output_on(1)
result = psu.measure(1)                     # {"channel": 1, "voltage": "5.00", "current": "0.50"}
```

### MP730027 Multimeter

TCP device. See `multimeter_device/README.md` for available measurement modes.

## Network Configuration

| Device | Model | IP | Port | Protocol |
|--------|-------|----|------|----------|
| PSU | MP711001 | 192.168.1.100 | 5025 | TCP |
| Multimeter | MP730027 | 192.168.1.99 | 3000 | TCP |
| DC Load | MP71077x | 192.168.1.80 | 18190 | UDP |

## Requirements

- Python 3.7+
- `flask` (for REST APIs)
- `colorama` (DC load driver)
- Network connectivity to devices

## Troubleshooting

### "Failed to bind to 0.0.0.0:\<port\>"
Another process (or a previous run that didn't exit cleanly) is holding the UDP port. Kill it or change the `port` parameter.

### Connection refused (TCP devices)
- Confirm the device IP with `ping`
- Verify the device is powered on and port is not firewalled

### Socket timeout
- Increase the `timeout` parameter on initialization
- Check network latency

### Measurements inconsistent
- Allow stabilization time after changing voltage or current
- See `demo.py` for recommended `time.sleep()` delays between commands

## See Also

- [PSU Device README](./psu_device/README.md)
- [Multimeter Device README](./multimeter_device/README.md)
- [DC Load Device README](./dcload_device/README.md)
- [demo.py](./demo.py)