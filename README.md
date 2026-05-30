# Lab Control Interface

A browser-based instrument control panel for the [lab_api](https://github.com/mayermakes/lab_api) project. Control and monitor your Multicomp Pro bench equipment from any browser on the same network — no driver installation needed on the client side.

---

## Supported instruments

| Device | Model | Protocol | Default address |
|--------|-------|----------|----------------|
| Power Supply | MP711001 | TCP | 192.168.1.100:5025 |
| Multimeter | MP730027 | TCP | 192.168.1.99:3000 |
| DC Load | MP71077x | UDP | 192.168.1.80:18190 |

---

## Files

```
lab_api/
├── lab_api/                  ← original lab_api driver package
│   ├── psu_device/
│   ├── multimeter_device/
│   └── dcload_device/
├── server.py                 ← Flask server (this project)
├── lab_control.html          ← Web UI (this project)
└── README.md
```

Place `server.py` and `lab_control.html` in the root of the `lab_api` repository (next to the `lab_api/` package folder).

---

## Quick start

**1. Install dependencies**

```bash
pip install flask flask-cors
```

**2. Start the server**

```bash
python server.py
```

The server starts on port 5000 and connects to instruments at their default IPs. Open **http://localhost:5000** in any browser.

**3. Connect instruments**

Enter the server URL in the header bar (`http://localhost:5000` if running locally) and click **CONNECT ALL**. Each device card shows a green indicator when reachable.

---

## Running without hardware — Stub mode

If the `lab_api` drivers cannot be imported the server starts in **stub mode** automatically. All API calls return realistic simulated data (including ±0.5 % noise and sinusoidal waveforms). This lets you develop, test, or demo the UI without any instruments connected.

```
WARNING  lab_server: lab_api drivers not found. Running in STUB mode
```

---

## Command-line options

```
python server.py [options]

--psu-ip   IP     PSU IP address          (default: 192.168.1.100)
--psu-port PORT   PSU TCP port            (default: 5025)
--mm-ip    IP     Multimeter IP address   (default: 192.168.1.99)
--mm-port  PORT   Multimeter TCP port     (default: 3000)
--dcl-ip   IP     DC Load IP address      (default: 192.168.1.80)
--dcl-port PORT   DC Load UDP port        (default: 18190)
--port     PORT   Flask server port       (default: 5000)
--debug           Enable Flask debug mode
```

Example — instruments on non-default addresses:

```bash
python server.py --psu-ip 10.0.0.10 --mm-ip 10.0.0.11 --dcl-ip 10.0.0.12 --port 8080
```

---

## UI walkthrough

### Header bar

| Control | Purpose |
|---------|---------|
| SERVER field | Base URL of the Flask server (change if accessing remotely) |
| CONNECT ALL | Pings all three devices at once; coloured indicators show status |
| Poll rate | Interval for automatic measurement polling (1 / 2 / 5 / 10 s) |
| START POLLING | Begins automatic polling of all devices at the selected rate |

### Power Supply card

- **CH1–CH4 tabs** — select which channel all controls apply to
- **Voltage / Current sliders** — drag or type directly in the number field; slider fills with colour as it moves
- **APPLY** — sends the current voltage and current-limit setpoints to the selected channel
- **OUTPUT ON/OFF** — toggles the channel output; button turns green when on
- **MEASURE** — reads back actual voltage and current from the instrument and plots the values

### Multimeter card

- **Mode buttons** — select measurement type: DC V, AC V, DC A, AC A, Ω, continuity, diode, capacitance, frequency
- **MEASURE** — takes a single reading; updates the large display and min/max trackers
- **RESET MIN/MAX** — clears the running min/max without affecting the chart

### DC Load card

- **Mode buttons** — CC (constant current), CV (constant voltage), CP (constant power), CR (constant resistance); switching mode updates the slider range and unit automatically
- **Set value slider** — sets the target for the active mode
- **APPLY** — sends mode and setpoint to the instrument
- **LOAD ON/OFF** — engages or disengages the load; button turns green when on
- **MEASURE** — reads back voltage, current, and calculates dissipated power

### Live Data chart

- Plots PSU voltage, PSU current, DMM reading, load voltage, and load current on a shared time axis (up to 120 samples)
- Click any legend button to show/hide individual series
- **CLEAR** — wipes chart history
- **EXPORT CSV** — downloads all plotted data as a `.csv` file

### Config Manager

Saves and restores complete instrument setups (server URL, all setpoints, modes, and channel selection) to browser `localStorage`.

| Button | Action |
|--------|--------|
| SAVE CONFIG | Saves current state under the typed name (auto-named if blank) |
| LOAD | Restores that config — sliders, modes, and server URL all update |
| ✕ | Deletes that config |
| EXPORT JSON | Downloads all saved configs as a single `.json` file |
| IMPORT JSON | Merges configs from a previously exported `.json` file |

---

## Accessing from another machine

The server binds to `0.0.0.0` so it is reachable from anywhere on the local network. On the remote machine open:

```
http://<server-host-ip>:5000
```

And set the SERVER field in the UI to the same URL. CORS is enabled, so the browser will not block cross-origin API calls.

---

## Troubleshooting

**Instrument shows red indicator after CONNECT ALL**
- Verify the instrument is powered on and connected to the same network.
- Confirm the IP address with `ping <ip>` from the server machine.
- Check that no firewall is blocking the instrument's port (5025 / 3000 / 18190).
- Try the individual **PING** button on that device's card for a targeted test.

**Server starts in stub mode unexpectedly**
- Make sure `server.py` is in the root of the `lab_api` repo (same level as the `lab_api/` package folder).
- Check that all lab_api dependencies are installed: `pip install -r lab_api/requirements.txt`

**Browser shows "Failed to fetch"**
- The browser is being served from a different origin than the API. Make sure the SERVER field matches the actual server address (not `localhost` if you opened the HTML as a file).

**PSU APPLY has no effect**
- Make sure OUTPUT is ON for that channel — some instruments ignore setpoint changes while the output is disabled.
