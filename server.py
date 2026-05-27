#!/usr/bin/env python3
"""
server.py — Unified Flask server for lab_api
Serves lab_control.html and provides REST endpoints for:
  - MP711001  PSU       → /api/psu/...       (port 5000)
  - MP730027  Multimeter → /api/mm/...        (port 5000)
  - MP71077x  DC Load   → /api/dcload/...     (port 5000)

All three devices share one Flask app on one port.
The HTML frontend hits:
  http://<host>:5000/api/psu/...
  http://<host>:5000/api/mm/...
  http://<host>:5000/api/dcload/...

Run:
  pip install flask flask-cors
  python server.py [--psu-ip 192.168.1.100] [--mm-ip 192.168.1.99] [--dcl-ip 192.168.1.80] [--port 5000]

Hardware defaults (from lab_api README):
  PSU  MP711001  192.168.1.100  TCP :5025
  MM   MP730027  192.168.1.99   TCP :3000
  DCL  MP71077x  192.168.1.80   UDP :18190
"""

import argparse
import os
import sys
import time
import threading
import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ─────────────────────────────────────────────────────────────────────────────
# CLI args — override device IPs at startup
# ─────────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Lab API unified server")
parser.add_argument("--psu-ip",  default="192.168.1.100", help="PSU IP")
parser.add_argument("--psu-port",default=5025, type=int,  help="PSU TCP port")
parser.add_argument("--mm-ip",   default="192.168.1.99",  help="Multimeter IP")
parser.add_argument("--mm-port", default=3000, type=int,  help="Multimeter TCP port")
parser.add_argument("--dcl-ip",  default="192.168.1.80",  help="DC Load IP")
parser.add_argument("--dcl-port",default=18190,type=int,  help="DC Load UDP port")
parser.add_argument("--port",    default=5000, type=int,  help="Flask server port")
parser.add_argument("--debug",   action="store_true",     help="Flask debug mode")
args = parser.parse_args()

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if args.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("lab_server")

# ─────────────────────────────────────────────────────────────────────────────
# Import lab_api drivers (graceful fallback to stub mode if not installed)
# ─────────────────────────────────────────────────────────────────────────────
STUB_MODE = False

try:
    # lab_api package lives one directory up when running from repo root
    repo_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "lab_api"))

    from psu_device    import MP711001
    from multimeter_device import MP730027
    from dcload_device import MP71077x
    log.info("lab_api drivers loaded OK")

except ImportError as e:
    log.warning(f"lab_api drivers not found ({e}). Running in STUB mode — "
                "all API calls return simulated data.")
    STUB_MODE = True


# ─────────────────────────────────────────────────────────────────────────────
# Device manager — lazy init, reconnect on error
# ─────────────────────────────────────────────────────────────────────────────
_lock = threading.Lock()

class DeviceManager:
    """Holds live driver instances. Re-creates them after connection errors."""

    def __init__(self):
        self._psu = None
        self._mm  = None
        self._dcl = None

    # ── PSU ──────────────────────────────────────────────────────────────────
    def psu(self) -> "MP711001":
        with _lock:
            if self._psu is None:
                log.info(f"Connecting PSU @ {args.psu_ip}:{args.psu_port}")
                self._psu = MP711001(args.psu_ip, port=args.psu_port, timeout=2)
            return self._psu

    def reset_psu(self):
        with _lock:
            self._psu = None

    # ── Multimeter ───────────────────────────────────────────────────────────
    def mm(self) -> "MP730027":
        with _lock:
            if self._mm is None:
                log.info(f"Connecting MM  @ {args.mm_ip}:{args.mm_port}")
                self._mm = MP730027(args.mm_ip, port=args.mm_port)
            return self._mm

    def reset_mm(self):
        with _lock:
            self._mm = None

    # ── DC Load ──────────────────────────────────────────────────────────────
    def dcl(self) -> "MP71077x":
        with _lock:
            if self._dcl is None:
                log.info(f"Connecting DCL @ {args.dcl_ip}:{args.dcl_port}")
                self._dcl = MP71077x(args.dcl_ip, port=args.dcl_port, timeout=0.5)
            return self._dcl

    def reset_dcl(self):
        with _lock:
            self._dcl = None


dm = DeviceManager()


def device_call(getter, reset_fn, fn, *a, **kw):
    """
    Helper: call fn(device, *a, **kw) with automatic reconnect on error.
    Returns the result or raises RuntimeError.
    """
    for attempt in range(2):
        try:
            dev = getter()
            return fn(dev, *a, **kw)
        except (ConnectionError, OSError, TimeoutError) as e:
            log.warning(f"Device call failed (attempt {attempt+1}): {e}")
            reset_fn()
            if attempt == 1:
                raise RuntimeError(str(e)) from e
            time.sleep(0.1)


# ─────────────────────────────────────────────────────────────────────────────
# STUB implementations (used when drivers are not installed)
# ─────────────────────────────────────────────────────────────────────────────
import math, random

_stub_state = {
    "psu": {
        "connected": True,
        "channels": {
            ch: {"voltage_set": 5.0, "current_set": 1.0, "output": False}
            for ch in range(1, 5)
        },
    },
    "mm": {
        "connected": True,
        "mode": "dc_voltage",
    },
    "dcl": {
        "connected": True,
        "mode": "CC",
        "set_value": 1.0,
        "load_on": False,
    },
    "_t": 0,
}

def _stub_noise(base, pct=0.005):
    return round(base * (1 + random.uniform(-pct, pct)), 4)

def _stub_psu_measure(ch):
    s = _stub_state["psu"]["channels"][ch]
    v = _stub_noise(s["voltage_set"]) if s["output"] else 0.0
    i = _stub_noise(s["current_set"] * 0.6) if s["output"] else 0.0
    return {"channel": ch, "voltage": round(v, 3), "current": round(i, 3)}

def _stub_mm_measure(mode):
    _stub_state["_t"] += 0.1
    t = _stub_state["_t"]
    val_map = {
        "dc_voltage":   round(5.0 + 0.1 * math.sin(t), 4),
        "ac_voltage":   round(230.0 + random.uniform(-0.5, 0.5), 3),
        "dc_current":   round(1.0 + 0.05 * math.cos(t), 4),
        "ac_current":   round(0.5 + random.uniform(-0.01, 0.01), 4),
        "resistance":   round(100.0 + random.uniform(-0.5, 0.5), 2),
        "continuity":   round(0.1 + random.uniform(0, 0.05), 3),
        "diode":        round(0.65 + random.uniform(-0.005, 0.005), 4),
        "capacitance":  round(100e-9 + random.uniform(-1e-9, 1e-9), 12),
        "frequency":    round(50.0 + random.uniform(-0.01, 0.01), 4),
    }
    return {"mode": mode, "value": val_map.get(mode, 0.0)}

def _stub_dcl_measure():
    s = _stub_state["dcl"]
    v = _stub_noise(5.0) if s["load_on"] else 0.0
    i = _stub_noise(s["set_value"]) if s["load_on"] and s["mode"] == "CC" else 0.0
    return {"voltage": round(v, 3), "current": round(i, 3)}


# ─────────────────────────────────────────────────────────────────────────────
# Flask app
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)  # Allow browser requests from file:// or different port

def ok(data: dict):
    return jsonify({"status": "ok", **data})

def err(msg: str, code: int = 500):
    log.error(msg)
    return jsonify({"status": "error", "message": msg}), code


# ─────────────────────────────────────────────────────────────────────────────
# Serve the HTML frontend
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    html_path = Path(__file__).parent / "lab_control.html"
    if html_path.exists():
        return send_from_directory(str(html_path.parent), "lab_control.html")
    return "<h2>lab_control.html not found next to server.py</h2>", 404


# ═════════════════════════════════════════════════════════════════════════════
# PSU ENDPOINTS  →  /api/psu/...
# HTML calls:
#   GET  /api/psu/status
#   POST /api/psu/channel/<ch>/voltage        body: {"voltage": <float>}
#   POST /api/psu/channel/<ch>/current        body: {"current": <float>}
#   POST /api/psu/channel/<ch>/output_on
#   POST /api/psu/channel/<ch>/output_off
#   GET  /api/psu/channel/<ch>/measure
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/psu/status")
def psu_status():
    if STUB_MODE:
        return ok({"device": "MP711001", "ip": args.psu_ip, "channels": 4, "stub": True})
    try:
        psu = dm.psu()
        return ok({"device": "MP711001", "ip": args.psu_ip, "channels": 4})
    except Exception as e:
        dm.reset_psu()
        return err(f"PSU not reachable: {e}")


@app.route("/api/psu/channel/<int:ch>/voltage", methods=["POST"])
def psu_set_voltage(ch):
    if ch not in range(1, 5):
        return err("Channel must be 1–4", 400)
    body = request.get_json(silent=True) or {}
    v = body.get("voltage")
    if v is None:
        return err("Missing 'voltage' in body", 400)
    v = float(v)
    if STUB_MODE:
        _stub_state["psu"]["channels"][ch]["voltage_set"] = v
        log.info(f"[STUB] PSU CH{ch} voltage → {v}V")
        return ok({"channel": ch, "voltage": v})
    try:
        device_call(dm.psu, dm.reset_psu, lambda d, *_: d.set_voltage(ch, v))
        log.info(f"PSU CH{ch} voltage → {v}V")
        return ok({"channel": ch, "voltage": v})
    except Exception as e:
        return err(str(e))


@app.route("/api/psu/channel/<int:ch>/current", methods=["POST"])
def psu_set_current(ch):
    if ch not in range(1, 5):
        return err("Channel must be 1–4", 400)
    body = request.get_json(silent=True) or {}
    i = body.get("current")
    if i is None:
        return err("Missing 'current' in body", 400)
    i = float(i)
    if STUB_MODE:
        _stub_state["psu"]["channels"][ch]["current_set"] = i
        log.info(f"[STUB] PSU CH{ch} current → {i}A")
        return ok({"channel": ch, "current": i})
    try:
        device_call(dm.psu, dm.reset_psu, lambda d, *_: d.set_current(ch, i))
        log.info(f"PSU CH{ch} current → {i}A")
        return ok({"channel": ch, "current": i})
    except Exception as e:
        return err(str(e))


@app.route("/api/psu/channel/<int:ch>/output_on", methods=["POST"])
def psu_output_on(ch):
    if STUB_MODE:
        _stub_state["psu"]["channels"][ch]["output"] = True
        return ok({"channel": ch, "output": True})
    try:
        device_call(dm.psu, dm.reset_psu, lambda d, *_: d.output_on(ch))
        log.info(f"PSU CH{ch} OUTPUT ON")
        return ok({"channel": ch, "output": True})
    except Exception as e:
        return err(str(e))


@app.route("/api/psu/channel/<int:ch>/output_off", methods=["POST"])
def psu_output_off(ch):
    if STUB_MODE:
        _stub_state["psu"]["channels"][ch]["output"] = False
        return ok({"channel": ch, "output": False})
    try:
        device_call(dm.psu, dm.reset_psu, lambda d, *_: d.output_off(ch))
        log.info(f"PSU CH{ch} OUTPUT OFF")
        return ok({"channel": ch, "output": False})
    except Exception as e:
        return err(str(e))


@app.route("/api/psu/channel/<int:ch>/measure")
def psu_measure(ch):
    if STUB_MODE:
        return ok(_stub_psu_measure(ch))
    try:
        result = device_call(dm.psu, dm.reset_psu, lambda d, *_: d.measure(ch))
        # driver returns {"channel": int, "voltage": str|float, "current": str|float}
        return ok({
            "channel": ch,
            "voltage": float(result.get("voltage", 0)),
            "current": float(result.get("current", 0)),
        })
    except Exception as e:
        return err(str(e))


# ═════════════════════════════════════════════════════════════════════════════
# MULTIMETER ENDPOINTS  →  /api/mm/...
# HTML calls:
#   GET  /api/mm/status
#   GET  /api/mm/measure/<mode>
#     modes: dc_voltage, ac_voltage, dc_current, ac_current,
#            resistance, continuity, diode, capacitance, frequency
# ═════════════════════════════════════════════════════════════════════════════

MM_MODE_MAP = {
    "dc_voltage":  "measure_dc_voltage",
    "ac_voltage":  "measure_ac_voltage",
    "dc_current":  "measure_dc_current",
    "ac_current":  "measure_ac_current",
    "resistance":  "measure_resistance",
    "continuity":  "measure_continuity",
    "diode":       "measure_diode",
    "capacitance": "measure_capacitance",
    "frequency":   "measure_frequency",
}


@app.route("/api/mm/status")
def mm_status():
    if STUB_MODE:
        return ok({"device": "MP730027", "ip": args.mm_ip, "stub": True})
    try:
        dm.mm()
        return ok({"device": "MP730027", "ip": args.mm_ip})
    except Exception as e:
        dm.reset_mm()
        return err(f"MM not reachable: {e}")


@app.route("/api/mm/measure/<mode>")
def mm_measure(mode):
    if mode not in MM_MODE_MAP:
        return err(f"Unknown mode '{mode}'. Valid: {list(MM_MODE_MAP)}", 400)
    if STUB_MODE:
        return ok(_stub_mm_measure(mode))
    try:
        method_name = MM_MODE_MAP[mode]
        raw = device_call(dm.mm, dm.reset_mm, lambda d, *_: getattr(d, method_name)())
        # Driver returns a float or a string; normalise to float
        value = float(raw) if raw is not None else 0.0
        log.debug(f"MM {mode} = {value}")
        return ok({"mode": mode, "value": value})
    except Exception as e:
        return err(str(e))


# ═════════════════════════════════════════════════════════════════════════════
# DC LOAD ENDPOINTS  →  /api/dcload/...
# HTML calls:
#   GET  /api/dcload/status
#   POST /api/dcload/mode              body: {"mode": "CC"|"CV"|"CP"|"CR"}
#   POST /api/dcload/set/current       body: {"value": <float>}
#   POST /api/dcload/set/voltage       body: {"value": <float>}
#   POST /api/dcload/set/power         body: {"value": <float>}
#   POST /api/dcload/set/resistance    body: {"value": <float>}
#   POST /api/dcload/load_on
#   POST /api/dcload/load_off
#   GET  /api/dcload/measure
# ═════════════════════════════════════════════════════════════════════════════

DCL_MODE_FN = {
    "CC": "set_mode_current",
    "CV": "set_mode_voltage",
    "CP": "set_mode_power",
    "CR": "set_mode_resistance",
}

DCL_SET_FN = {
    "current":    "set_ci_current",   # CC mode
    "voltage":    "set_cv_voltage",   # CV mode
    "power":      "set_cp_power",     # CP mode
    "resistance": "set_cr_resistance",# CR mode
}


@app.route("/api/dcload/status")
def dcl_status():
    if STUB_MODE:
        return ok({"device": "MP71077x", "ip": args.dcl_ip, "stub": True})
    try:
        dm.dcl()
        return ok({"device": "MP71077x", "ip": args.dcl_ip})
    except Exception as e:
        dm.reset_dcl()
        return err(f"DCLoad not reachable: {e}")


@app.route("/api/dcload/mode", methods=["POST"])
def dcl_set_mode():
    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "").upper()
    if mode not in DCL_MODE_FN:
        return err(f"Unknown mode '{mode}'. Valid: CC CV CP CR", 400)
    if STUB_MODE:
        _stub_state["dcl"]["mode"] = mode
        return ok({"mode": mode})
    try:
        fn_name = DCL_MODE_FN[mode]
        device_call(dm.dcl, dm.reset_dcl, lambda d, *_: getattr(d, fn_name)())
        log.info(f"DCLoad mode → {mode}")
        return ok({"mode": mode})
    except Exception as e:
        return err(str(e))


@app.route("/api/dcload/set/<parameter>", methods=["POST"])
def dcl_set_value(parameter):
    if parameter not in DCL_SET_FN:
        return err(f"Unknown parameter '{parameter}'. Valid: current voltage power resistance", 400)
    body = request.get_json(silent=True) or {}
    value = body.get("value")
    if value is None:
        return err("Missing 'value' in body", 400)
    value = float(value)
    if STUB_MODE:
        _stub_state["dcl"]["set_value"] = value
        log.info(f"[STUB] DCLoad {parameter} → {value}")
        return ok({"parameter": parameter, "value": value})
    try:
        fn_name = DCL_SET_FN[parameter]
        device_call(dm.dcl, dm.reset_dcl, lambda d, *_: getattr(d, fn_name)(value))
        log.info(f"DCLoad {parameter} → {value}")
        return ok({"parameter": parameter, "value": value})
    except Exception as e:
        return err(str(e))


@app.route("/api/dcload/load_on", methods=["POST"])
def dcl_load_on():
    if STUB_MODE:
        _stub_state["dcl"]["load_on"] = True
        return ok({"load": True})
    try:
        device_call(dm.dcl, dm.reset_dcl, lambda d, *_: d.load_on())
        log.info("DCLoad LOAD ON")
        return ok({"load": True})
    except Exception as e:
        return err(str(e))


@app.route("/api/dcload/load_off", methods=["POST"])
def dcl_load_off():
    if STUB_MODE:
        _stub_state["dcl"]["load_on"] = False
        return ok({"load": False})
    try:
        device_call(dm.dcl, dm.reset_dcl, lambda d, *_: d.load_off())
        log.info("DCLoad LOAD OFF")
        return ok({"load": False})
    except Exception as e:
        return err(str(e))


@app.route("/api/dcload/measure")
def dcl_measure():
    if STUB_MODE:
        return ok(_stub_dcl_measure())
    try:
        result = device_call(dm.dcl, dm.reset_dcl, lambda d, *_: d.measure())
        # driver returns {"voltage": float, "current": float}
        return ok({
            "voltage": float(result.get("voltage", 0)),
            "current": float(result.get("current", 0)),
        })
    except Exception as e:
        return err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Health check  →  /health
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return ok({
        "stub_mode": STUB_MODE,
        "psu_ip":  args.psu_ip,
        "mm_ip":   args.mm_ip,
        "dcl_ip":  args.dcl_ip,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("=" * 60)
    log.info(f"  Lab API Server   port={args.port}   stub={STUB_MODE}")
    log.info(f"  PSU  {args.psu_ip}:{args.psu_port}")
    log.info(f"  MM   {args.mm_ip}:{args.mm_port}")
    log.info(f"  DCL  {args.dcl_ip}:{args.dcl_port}")
    log.info(f"  UI   http://localhost:{args.port}/")
    log.info("=" * 60)
    app.run(
        host="0.0.0.0",
        port=args.port,
        debug=args.debug,
        threaded=True,
        use_reloader=False,  # avoid double-init of device manager
    )
