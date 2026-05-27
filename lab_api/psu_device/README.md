# PSU Device - MP711001 Driver

4-channel programmable power supply control library using SCPI protocol over Ethernet.

## Device Info

- **Model**: Multicomp-Pro MP711001
- **Type**: 4-Channel Programmable DC Power Supply
- **Interface**: Ethernet (TCP Socket)
- **Default Port**: 5025
- **Protocol**: SCPI (Standard Commands for Programmable Instruments)

## Installation

The MP711001 driver is part of the `psu_device` package:

```python
from psu_device import MP711001
```

## Quick Start

```python
from psu_device import MP711001

# Connect to PSU
psu = MP711001("192.168.1.100")

# Set voltage on channel 1
psu.set_voltage(1, 5.0)

# Set current limit on channel 1
psu.set_current(1, 2.0)

# Enable output on channel 1
psu.output_on(1)

# Measure voltage and current
result = psu.measure(1)
print(f"Voltage: {result['voltage']}V, Current: {result['current']}A")

# Disable output
psu.output_off(1)
```

## API Reference

### Initialization

```python
psu = MP711001(ip, port=5025, timeout=2)
```

**Parameters:**
- `ip` (str): Device IP address
- `port` (int): TCP port (default: 5025)
- `timeout` (float): Socket timeout in seconds (default: 2)

### Channel Selection

#### `select_channel(ch: int)`
Select active channel for subsequent commands.

```python
psu.select_channel(1)  # Switch to channel 1
```

**Channels**: 1, 2, 3, 4

### Output Control

#### `output_on(ch: int)`
Enable output on specified channel.

```python
psu.output_on(1)
```

#### `output_off(ch: int)`
Disable output on specified channel.

```python
psu.output_off(1)
```

### Parameter Configuration

#### `set_voltage(ch: int, voltage: float)`
Set output voltage on specified channel.

```python
psu.set_voltage(1, 5.0)    # 5V
psu.set_voltage(2, 3.3)    # 3.3V
psu.set_voltage(3, 12.0)   # 12V
```

#### `set_current(ch: int, current: float)`
Set current limit on specified channel.

```python
psu.set_current(1, 2.0)    # 2.0A limit
psu.set_current(2, 1.5)    # 1.5A limit
```

### Measurement

#### `measure(ch: int) -> dict`
Read voltage and current from specified channel.

```python
result = psu.measure(1)
# Returns: {"channel": 1, "voltage": "5.00", "current": "0.50"}
```

**Returns:**
- `channel` (int): Channel number
- `voltage` (str): Measured voltage
- `current` (str): Measured current

## Low-Level IO

For advanced usage or custom SCPI commands:

#### `write(cmd: str)`
Send command to device (no response expected).

```python
psu.write("OUTP ON")
```

#### `query(cmd: str) -> str`
Send command and retrieve response.

```python
response = psu.query("MEAS:VOLT?")
```

## REST API

Flask-based HTTP interface for remote access.

### Starting the Server

```bash
cd psu_device
python -m flask --app flask_app run --port 5000
```

Server runs on `http://localhost:5000`

### API Endpoints

#### `POST /set`
Set voltage and/or current on a channel.

**Request:**
```json
{
  "channel": 1,
  "voltage": 5.0,
  "current": 2.0
}
```

**Response:**
```json
{"ok": true}
```

#### `POST /output`
Enable or disable channel output.

**Request:**
```json
{
  "channel": 1,
  "state": true
}
```

**Response:**
```json
{"ok": true}
```

#### `GET /measure`
Read voltage and current from active channel.

**Response:**
```json
{
  "channel": 1,
  "voltage": "5.00",
  "current": "0.50"
}
```

## Common Patterns

### Initialize Multiple Channels

```python
channels = [
    {"channel": 1, "voltage": 5.0, "current": 2.0},
    {"channel": 2, "voltage": 3.3, "current": 1.5},
    {"channel": 3, "voltage": 12.0, "current": 3.0},
]

for ch in channels:
    psu.set_voltage(ch["channel"], ch["voltage"])
    psu.set_current(ch["channel"], ch["current"])
    psu.output_on(ch["channel"])
```

### Ramp Voltage

```python
import time

for v in [0.0, 1.0, 2.0, 3.0, 5.0]:
    psu.set_voltage(1, v)
    time.sleep(0.5)
```

### Measure Power Consumption

```python
result = psu.measure(1)
voltage = float(result["voltage"])
current = float(result["current"])
power = voltage * current  # watts

print(f"Power: {power}W")
```

### Test with DC Load

Verify PSU output and regulation under load:

```python
from psu_device import MP711001
from dcload_device import MP710771
import time

psu = MP711001("192.168.1.100")
dcload = MP710771("192.168.1.80", port=3000)

# Configure PSU
psu.set_voltage(1, 5.0)
psu.set_current(1, 2.0)
psu.output_on(1)

# Configure load and draw current
dcload.set_mode_current(1)
dcload.set_current(1, 1.0)
dcload.load_on(1)

time.sleep(1)

# Compare readings
psu_v = float(psu.measure(1)["voltage"])
load_v = float(dcload.measure(1)["voltage"])
print(f"Voltage sag under load: {(psu_v - load_v)*1000:.1f}mV")

dcload.load_off(1)
psu.output_off(1)
```

### Verify Output with Multimeter

```python
from psu_device import MP711001
from multimeter_device import MP730027

psu = MP711001("192.168.1.100")
mm = MP730027("192.168.1.99", port=3000)

psu.set_voltage(1, 5.0)
psu.output_on(1)

import time
time.sleep(1)

psu_reading = psu.measure(1)
mm_reading = mm.measure_dc_voltage()

print(f"PSU reports: {psu_reading['voltage']}V")
print(f"Multimeter measures: {mm_reading}V")
print(f"Difference: {abs(float(psu_reading['voltage']) - float(mm_reading))*1000:.1f}mV")

psu.output_off(1)
```

## Error Handling

The driver automatically reconnects on socket errors. No explicit error handling required in most cases.

For custom error handling:

```python
try:
    psu.set_voltage(1, 5.0)
    psu.output_on(1)
except Exception as e:
    print(f"Error: {e}")
    # Driver will attempt reconnect on next command
```

## Performance Notes

- **Timing**: 0.1-0.15s delay between commands for stability
- **Measurement**: Single-shot, blocking. No polling loops.
- **Reconnection**: ~0.5s delay on error recovery
- **Max Channels**: 4 (indexed 1-4)

## Specifications

Typical PSU specifications (refer to device manual for exact values):

- **Voltage Range**: 0-60V
- **Current Range**: 0-5A (per channel)
- **Resolution**: 0.01V, 0.001A
- **Accuracy**: ±1% typical

## Troubleshooting

### "Connection refused"
- Check device IP address: `ping 192.168.1.100`
- Verify device is powered on
- Confirm port 5025 is not blocked by firewall

### "Socket timeout"
- Device may be overloaded; try increasing `timeout` parameter
- Check network latency

### Measurements inconsistent
- Allow stabilization time after voltage/current changes
- See example in `demo.py` for recommended delays

### Output won't enable
- Check current limit is set reasonably
- Verify load doesn't exceed PSU limits
- Try different channel

## See Also

- Main documentation: [../README.md](../README.md)
- Example usage: [../demo.py](../demo.py)
- Multimeter device: [../multimeter_device/README.md](../multimeter_device/README.md)
- DC Load device: [../dcload_device/README.md](../dcload_device/README.md)
