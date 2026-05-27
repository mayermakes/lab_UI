# Multimeter Device - MP730027 Driver

Digital multimeter control library with support for voltage, current, resistance, continuity, and temperature measurements using SCPI protocol over Ethernet.

## Device Info

- **Model**: Multicomp-Pro MP730027
- **Type**: Digital Multimeter
- **Interface**: Ethernet (TCP Socket)
- **Default Port**: 3000
- **Protocol**: SCPI (Standard Commands for Programmable Instruments)

## Installation

The MP730027 driver is part of the `multimeter_device` package:

```python
from multimeter_device import MP730027
```

## Quick Start

```python
from multimeter_device import MP730027

# Connect to multimeter
mm = MP730027("192.168.1.99", port=3000)

# Measure DC voltage
voltage = mm.measure_dc_voltage()
print(f"DC Voltage: {voltage}V")

# Measure resistance
resistance = mm.measure_resistance()
print(f"Resistance: {resistance}Ω")

# Generic measurement
result = mm.measure("ac_current")
print(f"AC Current: {result['value']}A")
```

## API Reference

### Initialization

```python
mm = MP730027(ip, port=3000, timeout=2)
```

**Parameters:**
- `ip` (str): Device IP address
- `port` (int): TCP port (default: 3000)
- `timeout` (float): Socket timeout in seconds (default: 2)

### Voltage Measurements

#### `measure_dc_voltage() -> str`
Measure DC voltage (V).

```python
voltage = mm.measure_dc_voltage()
# Returns: "5.00" (as string)
```

#### `measure_ac_voltage() -> str`
Measure AC voltage (V).

```python
voltage = mm.measure_ac_voltage()
# Returns: "230.5" (as string)
```

### Current Measurements

#### `measure_dc_current() -> str`
Measure DC current (A).

```python
current = mm.measure_dc_current()
# Returns: "0.50" (as string)
```

#### `measure_ac_current() -> str`
Measure AC current (A).

```python
current = mm.measure_ac_current()
# Returns: "1.23" (as string)
```

### Resistance & Continuity

#### `measure_resistance() -> str`
Measure resistance (Ω).

```python
resistance = mm.measure_resistance()
# Returns: "1500" (as string, in ohms)
```

#### `measure_continuity() -> str`
Test continuity (beeps if resistance < 50Ω).

```python
result = mm.measure_continuity()
# Returns: "0" (beeps) or "1" (open circuit)
```

### Temperature

#### `measure_temperature() -> str`
Measure temperature (°C). Requires probe sensor connected.

```python
temp = mm.measure_temperature()
# Returns: "25.3" (as string, in Celsius)
```

### Generic Measurement

#### `measure(mode: str) -> dict`
Unified interface for all measurement types.

```python
result = mm.measure("dc_voltage")
# Returns: {"mode": "dc_voltage", "value": "5.00"}
```

**Supported Modes:**
- `"dc_voltage"` - DC voltage measurement
- `"ac_voltage"` - AC voltage measurement
- `"dc_current"` - DC current measurement
- `"ac_current"` - AC current measurement
- `"resistance"` - Resistance measurement
- `"continuity"` - Continuity test
- `"temperature"` - Temperature measurement

**Returns:**
```python
{
    "mode": str,      # The measurement mode used
    "value": str      # The measured value
}
```

## Low-Level IO

For advanced usage or custom SCPI commands:

#### `write(cmd: str)`
Send command to device (no response expected).

```python
mm.write("CONF:VOLT:DC")
```

#### `query(cmd: str) -> str`
Send command and retrieve response.

```python
response = mm.query("MEAS:VOLT:DC?")
```

## REST API

Flask-based HTTP interface for remote access.

### Starting the Server

```bash
cd multimeter_device
python -m flask --app flask_app run --port 5001
```

Server runs on `http://localhost:5001`

### API Endpoints

#### `POST /measure`
Measure with specified mode.

**Request:**
```json
{
  "mode": "dc_voltage"
}
```

**Response:**
```json
{
  "mode": "dc_voltage",
  "value": "5.00"
}
```

#### `GET /measure/<mode>`
Quick measurement with mode in URL.

**Request:**
```
GET /measure/dc_voltage
GET /measure/resistance
GET /measure/ac_current
```

**Response:**
```json
{
  "mode": "dc_voltage",
  "value": "5.00"
}
```

**Valid Modes:**
- `dc_voltage`, `ac_voltage`
- `dc_current`, `ac_current`
- `resistance`, `continuity`, `temperature`

## Common Patterns

### Multi-Measurement Reading

```python
measurements = {
    "dc_voltage": mm.measure_dc_voltage(),
    "dc_current": mm.measure_dc_current(),
    "resistance": mm.measure_resistance(),
}

for name, value in measurements.items():
    print(f"{name}: {value}")
```

### Continuous Monitoring

```python
import time

for i in range(10):
    voltage = mm.measure_dc_voltage()
    print(f"Reading {i+1}: {voltage}V")
    time.sleep(1)
```

### Convert to Float

```python
voltage_str = mm.measure_dc_voltage()
voltage_float = float(voltage_str)
print(f"Type: {type(voltage_float)}, Value: {voltage_float}")
```

### Verify PSU Output Accuracy

Compare PSU internal reading with multimeter external measurement:

```python
from psu_device import MP711001
from multimeter_device import MP730027

psu = MP711001("192.168.1.100")
mm = MP730027("192.168.1.99", port=3000)

# Set PSU to 5V
psu.set_voltage(1, 5.0)
psu.set_current(1, 2.0)
psu.output_on(1)

import time
time.sleep(2)

# Compare readings
psu_v = float(psu.measure(1)['voltage'])
mm_v = float(mm.measure_dc_voltage())

print(f"PSU reading:        {psu_v:.3f}V")
print(f"Multimeter reading: {mm_v:.3f}V")
print(f"Difference:         {abs(psu_v - mm_v)*1000:.1f}mV")

psu.output_off(1)
```

### Monitor PSU Output Under Load

Verify voltage stability when DC load draws current:

```python
from psu_device import MP711001
from multimeter_device import MP730027
from dcload_device import MP710771

psu = MP711001("192.168.1.100")
mm = MP730027("192.168.1.99", port=3000)
dcload = MP710771("192.168.1.80", port=3000)

psu.set_voltage(1, 12.0)
psu.set_current(1, 3.0)
psu.output_on(1)

dcload.set_mode_current(1)
dcload.load_on(1)

print(f"Load Current (A) | Multimeter (V) | Load Input (V)")
print("-" * 50)

for i in [0.5, 1.0, 1.5, 2.0]:
    dcload.set_current(1, i)
    time.sleep(0.5)
    
    mm_v = float(mm.measure_dc_voltage())
    load_v = float(dcload.measure(1)['voltage'])
    
    print(f"{i:>16.1f} | {mm_v:>14.3f} | {load_v:>17.3f}")

dcload.load_off(1)
psu.output_off(1)
```

### Verify Connection

```python
try:
    voltage = mm.measure_dc_voltage()
    print("Connected!")
except:
    print("Connection failed")
```

## Error Handling

The driver automatically reconnects on socket errors. No explicit error handling required in most cases.

For custom error handling:

```python
try:
    voltage = mm.measure_dc_voltage()
except ValueError as e:
    print(f"Invalid mode: {e}")
except Exception as e:
    print(f"Measurement error: {e}")
    # Driver will attempt reconnect on next command
```

## Performance Notes

- **Timing**: 0.15-0.2s delay between commands for stability
- **Measurement**: Single-shot, blocking. No polling loops.
- **Reconnection**: ~0.5s delay on error recovery
- **Response Format**: All measurements return strings (convert with `float()` as needed)

## Specifications

Typical multimeter specifications (refer to device manual for exact values):

- **Voltage Range**: 0-1000V AC/DC
- **Current Range**: 0-10A AC/DC
- **Resistance Range**: 0-100MΩ
- **Display Resolution**: 3-4 digits typical
- **Accuracy**: ±0.5-1% typical

## Troubleshooting

### "Connection refused"
- Check device IP address: `ping 192.168.1.99`
- Verify device is powered on
- Confirm port 3000 is not blocked by firewall

### "Socket timeout"
- Device may be slow; try increasing `timeout` parameter
- Check network latency
- Ensure probe connections are secure

### "Invalid mode" error
- Check mode spelling (use constants or list from docstring)
- Verify mode is supported by device

### Measurements reading zero
- Check probe connections
- Verify measurement range for device
- Try a known voltage source to verify device operation

### Temperature sensor not working
- Confirm temperature probe is connected
- Some devices require probe to be recognized before use
- Check device manual for probe specifications

## See Also

- Main documentation: [../README.md](../README.md)
- Example usage: [../demo.py](../demo.py)
- PSU device: [../psu_device/README.md](../psu_device/README.md)
- DC Load device: [../dcload_device/README.md](../dcload_device/README.md)
