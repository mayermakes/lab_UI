# API Reference

`server.py` exposes a REST API over HTTP on a single port (default **5000**). All endpoints return JSON. The web UI (`lab_control.html`) is served at the root path.

---

## General conventions

**Base URL:** `http://<host>:5000`

**Success response envelope:**
```json
{
  "status": "ok",
  ... endpoint-specific fields ...
}
```

**Error response envelope:**
```json
{
  "status": "error",
  "message": "human-readable description"
}
```
HTTP status codes are used correctly: `200` for success, `400` for bad input, `500` for device/server errors.

All `POST` bodies must be `Content-Type: application/json`.

---

## Frontend

### `GET /`
Serves `lab_control.html`. The browser UI for controlling all instruments.

---

## Health

### `GET /health`
Returns server configuration and mode.

**Response:**
```json
{
  "status": "ok",
  "stub_mode": false,
  "psu_ip": "192.168.1.100",
  "mm_ip": "192.168.1.99",
  "dcl_ip": "192.168.1.80"
}
```
`stub_mode: true` means no hardware drivers were found — all measurements return simulated data.

---

## Power Supply — `/api/psu/`

Device: **Multicomp Pro MP711001** — 4-channel programmable bench PSU.
Hardware connection: TCP to the IP/port given at server startup.

---

### `GET /api/psu/status`
Checks connectivity to the PSU.

**Response:**
```json
{
  "status": "ok",
  "device": "MP711001",
  "ip": "192.168.1.100",
  "channels": 4
}
```
Returns HTTP 500 if the instrument is not reachable.

---

### `POST /api/psu/channel/<ch>/voltage`
Sets the output voltage for a channel.

**URL parameter:** `ch` — integer 1–4

**Body:**
```json
{ "voltage": 12.5 }
```
Range: 0–30 V (instrument limit).

**Response:**
```json
{ "status": "ok", "channel": 2, "voltage": 12.5 }
```

---

### `POST /api/psu/channel/<ch>/current`
Sets the current limit for a channel.

**URL parameter:** `ch` — integer 1–4

**Body:**
```json
{ "current": 1.5 }
```
Range: 0–10 A (instrument limit).

**Response:**
```json
{ "status": "ok", "channel": 2, "current": 1.5 }
```

---

### `POST /api/psu/channel/<ch>/output_on`
Enables the output for a channel.

**URL parameter:** `ch` — integer 1–4

**Body:** none required

**Response:**
```json
{ "status": "ok", "channel": 1, "output": true }
```

---

### `POST /api/psu/channel/<ch>/output_off`
Disables the output for a channel.

**URL parameter:** `ch` — integer 1–4

**Body:** none required

**Response:**
```json
{ "status": "ok", "channel": 1, "output": false }
```

---

### `GET /api/psu/channel/<ch>/measure`
Reads back the actual output voltage and current for a channel.

**URL parameter:** `ch` — integer 1–4

**Response:**
```json
{
  "status": "ok",
  "channel": 1,
  "voltage": 5.002,
  "current": 0.314
}
```
Values are floats in volts and amps. In stub mode, returns the setpoint ± 0.5 % noise (0 when output is off).

---

## Multimeter — `/api/mm/`

Device: **Multicomp Pro MP730027** — bench multimeter.
Hardware connection: TCP to the IP/port given at server startup.

---

### `GET /api/mm/status`
Checks connectivity to the multimeter.

**Response:**
```json
{ "status": "ok", "device": "MP730027", "ip": "192.168.1.99" }
```

---

### `GET /api/mm/measure/<mode>`
Takes a measurement in the specified mode.

**URL parameter:** `mode` — one of:

| mode | Measures | Unit |
|------|----------|------|
| `dc_voltage` | DC voltage | V |
| `ac_voltage` | AC voltage (RMS) | V |
| `dc_current` | DC current | A |
| `ac_current` | AC current (RMS) | A |
| `resistance` | Resistance | Ω |
| `continuity` | Continuity / low-resistance | Ω |
| `diode` | Diode forward voltage | V |
| `capacitance` | Capacitance | F |
| `frequency` | Frequency | Hz |

**Response:**
```json
{ "status": "ok", "mode": "dc_voltage", "value": 4.9981 }
```
`value` is always a float in the SI unit for that mode. In stub mode, `dc_voltage` returns a 0.1 V sine wave around 5 V; other modes return realistic constants ± noise.

**Error (unknown mode):** HTTP 400
```json
{ "status": "error", "message": "Unknown mode 'xyz'. Valid: [...]" }
```

---

## DC Load — `/api/dcload/`

Device: **Multicomp Pro MP71077x** — programmable DC electronic load.
Hardware connection: UDP to the IP/port given at server startup.

---

### `GET /api/dcload/status`
Checks connectivity to the DC Load.

**Response:**
```json
{ "status": "ok", "device": "MP71077x", "ip": "192.168.1.80" }
```

---

### `POST /api/dcload/mode`
Sets the operating mode of the load.

**Body:**
```json
{ "mode": "CC" }
```

| mode | Name | Controlled quantity |
|------|------|---------------------|
| `CC` | Constant Current | Current draw |
| `CV` | Constant Voltage | Terminal voltage |
| `CP` | Constant Power | Dissipated power |
| `CR` | Constant Resistance | Apparent resistance |

**Response:**
```json
{ "status": "ok", "mode": "CC" }
```

---

### `POST /api/dcload/set/<parameter>`
Sets the target value for the active mode.

**URL parameter:** `parameter` — must match the active mode:

| parameter | Use with mode | Range | Unit |
|-----------|--------------|-------|------|
| `current` | CC | 0–30 | A |
| `voltage` | CV | 0–80 | V |
| `power` | CP | 0–200 | W |
| `resistance` | CR | 0.1–1000 | Ω |

**Body:**
```json
{ "value": 2.5 }
```

**Response:**
```json
{ "status": "ok", "parameter": "current", "value": 2.5 }
```

Always call `POST /api/dcload/mode` to set the mode **before** sending a setpoint — the underlying driver maps each parameter to a mode-specific register.

---

### `POST /api/dcload/load_on`
Engages the load (starts drawing current).

**Body:** none required

**Response:**
```json
{ "status": "ok", "load": true }
```

---

### `POST /api/dcload/load_off`
Disengages the load.

**Body:** none required

**Response:**
```json
{ "status": "ok", "load": false }
```

---

### `GET /api/dcload/measure`
Reads back the measured input voltage and current.

**Response:**
```json
{
  "status": "ok",
  "voltage": 4.998,
  "current": 2.491
}
```
Dissipated power can be computed as `voltage × current`. Both values are 0.0 when the load is off.

Stub mode simulates each operating mode correctly:

| Mode | Voltage | Current |
|------|---------|---------|
| CC | ~5 V (floating) | = setpoint |
| CV | = setpoint | ~1 A (floating) |
| CP | ~5 V (floating) | = power ÷ voltage |
| CR | ~5 V (floating) | = voltage ÷ resistance |

---

## Typical workflow

```
# 1. Verify connectivity
GET /api/psu/status
GET /api/mm/status
GET /api/dcload/status

# 2. Configure PSU channel 1 to 5 V / 2 A
POST /api/psu/channel/1/voltage   {"voltage": 5.0}
POST /api/psu/channel/1/current   {"current": 2.0}
POST /api/psu/channel/1/output_on

# 3. Configure DC Load in CC mode at 1 A
POST /api/dcload/mode             {"mode": "CC"}
POST /api/dcload/set/current      {"value": 1.0}
POST /api/dcload/load_on

# 4. Measure
GET  /api/psu/channel/1/measure   → {"voltage": 4.998, "current": 0.997}
GET  /api/dcload/measure          → {"voltage": 4.996, "current": 1.002}
GET  /api/mm/measure/dc_voltage   → {"mode": "dc_voltage", "value": 4.9975}

# 5. Shut down
POST /api/dcload/load_off
POST /api/psu/channel/1/output_off
```

---

## curl examples

```bash
# Check server health
curl http://localhost:5000/health

# Set PSU CH1 to 3.3 V
curl -X POST http://localhost:5000/api/psu/channel/1/voltage \
     -H "Content-Type: application/json" \
     -d '{"voltage": 3.3}'

# Turn PSU CH1 output on
curl -X POST http://localhost:5000/api/psu/channel/1/output_on

# Read PSU CH1 actual values
curl http://localhost:5000/api/psu/channel/1/measure

# Set DC Load to CC 500 mA
curl -X POST http://localhost:5000/api/dcload/mode \
     -H "Content-Type: application/json" \
     -d '{"mode": "CC"}'

curl -X POST http://localhost:5000/api/dcload/set/current \
     -H "Content-Type: application/json" \
     -d '{"value": 0.5}'

curl -X POST http://localhost:5000/api/dcload/load_on

# Take a multimeter resistance measurement
curl http://localhost:5000/api/mm/measure/resistance
```

---

## Architecture notes

**Single-port design.** All three devices and the HTML frontend are served from one Flask process on one port. This means only one URL needs to be known — no per-device port management.

**Lazy connection / auto-reconnect.** The `DeviceManager` class opens the TCP/UDP socket to each instrument on the first API call, not at startup. If a call fails due to a network or device error it resets the connection and retries once before returning HTTP 500.

**Thread safety.** A `threading.Lock` guards all driver access. Flask runs in threaded mode, so concurrent requests from the auto-polling frontend are safe.

**Stub mode.** Activated automatically when the `lab_api` Python package cannot be imported (missing drivers, running outside the repo, etc.). Stub data is fully stateful — setting voltage on a channel is reflected in subsequent measure calls, and mode/setpoint changes in the DC load affect simulated measurements.
