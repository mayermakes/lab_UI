# DC Load Device - MP71077x Driver

Electronic DC load control library using SCPI protocol over UDP.

## Device Info

- **Model**: MP71077x series DC Electronic Load
- **Interface**: Ethernet (UDP Socket)
- **Default Port**: 3000
- **Protocol**: SCPI (Standard Commands for Programmable Instruments)

## Installation

The MP71077x driver is part of the `dcload_device` package:

```python
from dcload_device import MP71077x
```

## Quick Start

```python
from dcload_device import MP71077x

# Connect to load
load = MP71077x("192.168.1.80")

# Set CC mode current
load.set_ci_current(1.0)

# Enable input
load.input_on()

# Read back current setpoint
print(load.get_ci_current())

# Disable input
load.input_off()
```

## API Reference

### Initialization

```python
load = MP71077x(ip, port=3000, timeout=2)
```

**Parameters:**
- `ip` (str): Device IP address
- `port` (int): UDP port (default: 3000)
- `timeout` (float): Socket timeout in seconds (default: 2)

### Input Control

#### `input_on()`
Enable load input.

```python
load.input_on()
```

#### `input_off()`
Disable load input.

```python
load.input_off()
```

#### `get_input_state() -> str`
Query current input state.

```python
state = load.get_input_state()  # "ON" or "OFF"
```

### Voltage Settings (CV Mode)

#### `set_cv_voltage(voltage: float)`
Set constant-voltage setpoint.

```python
load.set_cv_voltage(5.0)
```

#### `get_cv_voltage() -> float`
Read CV voltage setpoint.

#### `set_upper_voltage_limit(limit: float)`
Set upper voltage protection limit.

#### `get_upper_voltage_limit() -> float`
Read upper voltage limit.

#### `set_lower_voltage_limit(limit: float)`
Set lower voltage protection limit.

#### `get_lower_voltage_limit() -> float`
Read lower voltage limit.

### Current Settings (CI Mode)

#### `set_ci_current(current: float)`
Set constant-current draw.

```python
load.set_ci_current(2.0)  # draw 2A
```

#### `get_ci_current() -> float`
Read CI current setpoint.

#### `set_upper_current_limit(limit: float)`
Set upper current protection limit.

#### `get_upper_current_limit() -> float`
Read upper current limit.

#### `set_lower_current_limit(limit: float)`
Set lower current protection limit.

#### `get_lower_current_limit() -> float`
Read lower current limit.

### Power Settings (CP Mode)

#### `set_cp_power(power: float)`
Set constant-power draw.

```python
load.set_cp_power(10.0)  # draw 10W
```

#### `get_cp_power() -> float`
Read CP power setpoint.

#### `set_upper_power_limit(limit: float)` / `get_upper_power_limit() -> float`
Upper power protection limit.

#### `set_lower_power_limit(limit: float)` / `get_lower_power_limit() -> float`
Lower power protection limit.

### Resistance Settings (CR Mode)

#### `set_cr_resistance(resistance: float)`
Set constant-resistance mode value.

```python
load.set_cr_resistance(10.0)  # 10 Ohm
```

#### `get_cr_resistance() -> float`
Read CR resistance setpoint.

#### `set_upper_resistance_limit(limit: float)` / `get_upper_resistance_limit() -> float`
Upper resistance protection limit.

#### `set_lower_resistance_limit(limit: float)` / `get_lower_resistance_limit() -> float`
Lower resistance protection limit.

## Low-Level IO

For advanced usage or custom SCPI commands:

#### `write(cmd: str)`
Send command to device (no response expected).

```python
load.write(":INP 1")
```

#### `query(cmd: str) -> str`
Send command and retrieve response.

```python
response = load.query(":CURR?")
```

## REST API

Flask-based HTTP interface for remote access.

### Starting the Server

```bash
cd dcload_device
python -m flask --app flask_app run --port 5000
```

Server runs on `http://localhost:5000`

### API Endpoints

#### `POST /input`
Enable or disable load input.

**Request:**
```json
{"state": true}
```

**Response:**
```json
{"ok": true}
```

#### `POST /set/voltage`
Set CV voltage and/or voltage limits.

**Request:**
```json
{"cv": 5.0, "upper": 30.0, "lower": 0.0}
```

#### `POST /set/current`
Set CI current and/or current limits.

**Request:**
```json
{"ci": 2.0, "upper": 10.0, "lower": 0.0}
```

#### `POST /set/power`
Set CP power and/or power limits.

**Request:**
```json
{"cp": 10.0, "upper": 200.0, "lower": 0.0}
```

#### `POST /set/resistance`
Set CR resistance and/or resistance limits.

**Request:**
```json
{"cr": 10.0, "upper": 1000.0, "lower": 0.1}
```

#### `GET /get/voltage`
Read voltage setpoint and limits.

**Response:**
```json
{"cv": 5.0, "upper": 30.0, "lower": 0.0}
```

#### `GET /get/current`
Read current setpoint and limits.

#### `GET /get/power`
Read power setpoint and limits.

#### `GET /get/resistance`
Read resistance setpoint and limits.

#### `GET /input/state`
Read input on/off state.

**Response:**
```json
{"state": "ON"}
```

## Common Patterns

### CC Load Test

```python
load = MP71077x("192.168.1.80")

load.set_ci_current(2.0)
load.set_upper_current_limit(5.0)
load.input_on()
```

### Sweep Current

```python
import time

for i in [0.5, 1.0, 1.5, 2.0, 2.5]:
    load.set_ci_current(i)
    time.sleep(1.0)

load.input_off()
```

### Test with PSU

Verify PSU output and regulation under load:

```python
from dcload_device import MP71077x
from psu_device import MP711001
import time

psu = MP711001("192.168.1.100")
load = MP71077x("192.168.1.80")

psu.set_voltage(1, 5.0)
psu.set_current(1, 3.0)
psu.output_on(1)

load.set_ci_current(2.0)
load.input_on()

time.sleep(1)

result = psu.measure(1)
print(f"Voltage under load: {result['voltage']}V")
print(f"Current drawn: {result['current']}A")

load.input_off()
psu.output_off(1)
```

## Error Handling

The driver automatically reconnects on socket errors.

```python
try:
    load.set_ci_current(2.0)
    load.input_on()
except Exception as e:
    print(f"Error: {e}")
```

## Performance Notes

- **Transport**: UDP (connectionless); lower overhead than TCP
- **Timing**: 0.1-0.15s delay between commands for stability
- **Reconnection**: ~0.5s delay on error recovery

## Troubleshooting

### "Command response timeout"
- Check device IP address and that port 3000 is reachable
- Try increasing `timeout` parameter

### Values not applying
- Confirm units match device expectations (V, A, W, OHM)
- Check that protection limits are set wide enough to allow the setpoint

## See Also

- Main documentation: [../README.md](../README.md)
- PSU device: [../psu_device/README.md](../psu_device/README.md)
- Multimeter device: [../multimeter_device/README.md](../multimeter_device/README.md)
