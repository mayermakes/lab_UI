#!/usr/bin/env python3
"""
server.py — Unified Flask server with dynamic device discovery for lab_api

This server automatically discovers available lab devices and exposes them via REST endpoints.
Devices are detected by scanning lab_api modules for device_config.py files.

Features:
  - Automatic device discovery (TCP and UDP)
  - Dynamic Flask endpoint generation
  - Configuration management for IP/port
  - Manual UDP device support
  - Graceful fallback to stub mode if drivers unavailable

Run:
  python server.py [--port 5000] [--debug]

The frontend fetches /api/discover to get available devices, then dynamically generates UI.
"""

import argparse
import os
import sys
import time
import threading
import logging
import json
import socket
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ─────────────────────────────────────────────────────────────────────────────
# CLI args
# ─────────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Lab API unified server with device discovery")
parser.add_argument("--port", default=5000, type=int, help="Flask server port")
parser.add_argument("--debug", action="store_true", help="Flask debug mode")
parser.add_argument("--config", type=str, help="Config JSON file for device IPs/ports")
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
# Device discovery and loading
# ─────────────────────────────────────────────────────────────────────────────
STUB_MODE = False

@dataclass
class DeviceConfig:
    """Runtime configuration for a device."""
    device_id: str
    ip: str
    port: int
    manual: bool = False  # True for manually added UDP devices

class DeviceRegistry:
    """
    Dynamically loads and manages device drivers.
    Discovers devices from lab_api modules.
    """

    def __init__(self):
        self.devices: Dict[str, Dict[str, Any]] = {}  # device_id -> metadata + driver
        self.device_configs: Dict[str, DeviceConfig] = {}  # device_id -> config
        self._instances: Dict[str, Any] = {}  # device_id -> driver instance
        self._lock = threading.Lock()
        self._load_config_file()
        self._discover_devices()

    def _load_config_file(self):
        """Load device configuration from JSON file if provided."""
        if args.config and Path(args.config).exists():
            try:
                with open(args.config) as f:
                    cfg = json.load(f)
                    log.info(f"Loaded device config from {args.config}")
                    for dev_id, dev_cfg in cfg.get("devices", {}).items():
                        self.device_configs[dev_id] = DeviceConfig(
                            device_id=dev_id,
                            ip=dev_cfg.get("ip"),
                            port=dev_cfg.get("port"),
                            manual=dev_cfg.get("manual", False),
                        )
            except Exception as e:
                log.warning(f"Failed to load config file {args.config}: {e}")

    def _discover_devices(self):
        """
        Scan lab_api directory for device modules with device_config.py.
        Load metadata and store for later use.
        """
        lab_api_path = Path(__file__).parent / "lab_api"
        if not lab_api_path.exists():
            log.warning(f"lab_api path not found: {lab_api_path}")
            return

        sys.path.insert(0, str(lab_api_path.parent))
        sys.path.insert(0, str(lab_api_path))

        # Scan for device modules
        for item in lab_api_path.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue

            config_file = item / "device_config.py"
            if not config_file.exists():
                continue

            device_id = None
            try:
                spec = importlib.util.spec_from_file_location(f"device_config_{item.name}", config_file)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)

                device_id = getattr(config_module, "DEVICE_ID")
                device_name = getattr(config_module, "DEVICE_NAME")
                default_ip = getattr(config_module, "DEFAULT_IP")
                default_port = getattr(config_module, "DEFAULT_PORT")
                protocol = getattr(config_module, "PROTOCOL")
                test_connection_fn = getattr(config_module, "test_connection")
                get_info_fn = getattr(config_module, "get_device_info")

                # Use configured values or defaults
                device_cfg = self.device_configs.get(device_id)
                if device_cfg:
                    ip, port = device_cfg.ip, device_cfg.port
                else:
                    ip, port = default_ip, default_port
                    device_cfg = DeviceConfig(device_id=device_id, ip=ip, port=port)
                    self.device_configs[device_id] = device_cfg

                # Store device metadata
                self.devices[device_id] = {
                    "id": device_id,
                    "name": device_name,
                    "module_name": item.name,
                    "module_path": item,
                    "config_module": config_module,
                    "driver_class_name": getattr(config_module, "DEVICE_NAME"),
                    "default_ip": default_ip,
                    "default_port": default_port,
                    "ip": ip,
                    "port": port,
                    "protocol": protocol,
                    "test_connection": test_connection_fn,
                    "get_info": get_info_fn,
                    "driver": None,
                }
                log.info(f"Discovered device: {device_name} ({device_id}) @ {ip}:{port}")

            except Exception as e:
                log.warning(f"Failed to load device config from {item.name}: {e}")
                continue

    def get_available_devices(self) -> List[Dict[str, Any]]:
        """
        Return all discovered devices with connectivity status.
        Marks each device as connected/disconnected based on reachability test.
        """
        available = []
        for device_id, device_meta in self.devices.items():
            ip = device_meta["ip"]
            port = device_meta["port"]
            protocol = device_meta["protocol"]

            # Test connectivity
            try:
                is_reachable = device_meta["test_connection"](ip, port, timeout=1.0)
            except Exception as e:
                log.debug(f"Connectivity test for {device_id} failed: {e}")
                is_reachable = False

            # Return ALL discovered devices, marking connection status
            info = device_meta["get_info"]()
            info["connected"] = is_reachable
            info["ip"] = ip
            info["port"] = port
            info["protocol"] = protocol
            available.append(info)

            if is_reachable:
                log.info(f"Device {device_id} is reachable @ {ip}:{port}")
            else:
                log.info(f"Device {device_id} unreachable @ {ip}:{port} (configure IP/port to use)")

        return available

    def get_driver(self, device_id: str):
        """
        Get or create driver instance for device.
        Lazy initialization with reconnect on error.
        """
        with self._lock:
            if device_id in self._instances:
                return self._instances[device_id]

            if device_id not in self.devices:
                raise RuntimeError(f"Unknown device: {device_id}")

            device_meta = self.devices[device_id]
            ip = device_meta["ip"]
            port = device_meta["port"]

            try:
                # Import the device driver
                module_name = device_meta["module_name"]
                module_path = device_meta["module_path"]
                sys.path.insert(0, str(module_path.parent))

                # Import from __init__.py
                init_file = module_path / "__init__.py"
                spec = importlib.util.spec_from_file_location(f"{module_name}.__init__", init_file)
                driver_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(driver_module)

                # Get the driver class (should be exposed in __init__.py)
                # Usually named after the model like MP711001, MP730027, etc.
                driver_classes = [
                    name for name in dir(driver_module)
                    if not name.startswith("_") and name[0].isupper()
                ]
                if not driver_classes:
                    raise RuntimeError(f"No driver class found in {module_name}")

                DriverClass = getattr(driver_module, driver_classes[0])
                log.info(f"Creating driver instance for {device_id} @ {ip}:{port}")
                driver = DriverClass(ip, port=port, timeout=2)
                self._instances[device_id] = driver
                return driver

            except Exception as e:
                log.error(f"Failed to create driver for {device_id}: {e}")
                raise RuntimeError(f"Failed to load driver for {device_id}: {e}")

    def reset_driver(self, device_id: str):
        """Reset driver instance (force reconnect on next use)."""
        with self._lock:
            if device_id in self._instances:
                del self._instances[device_id]

    def update_device_config(self, device_id: str, ip: str, port: int):
        """Update IP/port configuration for a device."""
        if device_id not in self.devices:
            raise RuntimeError(f"Unknown device: {device_id}")

        self.devices[device_id]["ip"] = ip
        self.devices[device_id]["port"] = port
        self.device_configs[device_id] = DeviceConfig(device_id=device_id, ip=ip, port=port)
        self.reset_driver(device_id)
        log.info(f"Updated {device_id} config to {ip}:{port}")

    def save_config(self, filepath: str):
        """Save current device configuration to JSON file."""
        cfg = {
            "devices": {
                dev_id: asdict(dev_cfg)
                for dev_id, dev_cfg in self.device_configs.items()
            }
        }
        with open(filepath, "w") as f:
            json.dump(cfg, f, indent=2)
        log.info(f"Saved device config to {filepath}")


# Initialize device registry
registry = DeviceRegistry()

# Try to load drivers; if they fail, fall back to stub mode
try:
    if not registry.devices:
        log.warning("No device drivers discovered. Starting in STUB mode.")
        STUB_MODE = True
except Exception as e:
    log.warning(f"Failed to load device drivers: {e}. Running in STUB mode.")
    STUB_MODE = True




# ─────────────────────────────────────────────────────────────────────────────
# STUB implementations
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
    if not s["load_on"]:
        return {"voltage": 0.0, "current": 0.0}
    mode = s["mode"]
    sv = s["set_value"]
    if mode == "CC":
        i = _stub_noise(sv)
        v = _stub_noise(5.0)
    elif mode == "CV":
        v = _stub_noise(sv)
        i = _stub_noise(1.0)
    elif mode == "CP":
        v = _stub_noise(5.0)
        i = round(sv / max(v, 0.001), 3)
    else:  # CR
        v = _stub_noise(5.0)
        i = round(v / max(sv, 0.001), 3)
    return {"voltage": round(v, 3), "current": round(i, 3)}


# ─────────────────────────────────────────────────────────────────────────────
# Flask app
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

def ok(data: dict):
    return jsonify({"status": "ok", **data})

def err(msg: str, code: int = 500):
    log.error(msg)
    return jsonify({"status": "error", "message": msg}), code


# ─────────────────────────────────────────────────────────────────────────────
# Serve HTML frontend
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    html_path = Path(__file__).parent / "lab_control.html"
    if html_path.exists():
        return send_from_directory(str(html_path.parent), "lab_control.html")
    return "<h2>lab_control.html not found</h2>", 404


# ─────────────────────────────────────────────────────────────────────────────
# Device Discovery Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/discover", methods=["GET"])
def discover_devices():
    """
    Discover and return all available devices.
    Tests connectivity to all configured devices.
    Returns metadata for UI generation.
    """
    if STUB_MODE:
        return ok({
            "devices": [
                {
                    "id": "psu",
                    "name": "MP711001",
                    "fullName": "MP711001 Power Supply",
                    "protocol": "TCP",
                    "apiPrefix": "/api/psu",
                    "iconClass": "icon-psu",
                    "accentColor": "#00dca0",
                    "channels": 4,
                    "connected": True,
                    "stub": True,
                },
                {
                    "id": "mm",
                    "name": "MP730027",
                    "fullName": "MP730027 Multimeter",
                    "protocol": "TCP",
                    "apiPrefix": "/api/mm",
                    "iconClass": "icon-mm",
                    "accentColor": "#00b8e0",
                    "connected": True,
                    "stub": True,
                },
                {
                    "id": "dcl",
                    "name": "MP71077x",
                    "fullName": "MP71077x DC Load",
                    "protocol": "UDP",
                    "apiPrefix": "/api/dcload",
                    "iconClass": "icon-dcl",
                    "accentColor": "#e07800",
                    "connected": True,
                    "stub": True,
                },
            ],
            "stubMode": True,
        })

    available = registry.get_available_devices()
    return ok({
        "devices": available,
        "stubMode": False,
    })


@app.route("/api/device/<device_id>/config", methods=["GET"])
def get_device_config(device_id):
    """Get current IP/port for a device."""
    if device_id not in registry.devices:
        return err(f"Unknown device: {device_id}", 404)

    meta = registry.devices[device_id]
    return ok({
        "device_id": device_id,
        "ip": meta["ip"],
        "port": meta["port"],
        "default_ip": meta["default_ip"],
        "default_port": meta["default_port"],
    })


@app.route("/api/device/<device_id>/config", methods=["POST"])
def set_device_config(device_id):
    """Update IP/port for a device."""
    if device_id not in registry.devices:
        return err(f"Unknown device: {device_id}", 404)

    body = request.get_json(silent=True) or {}
    new_ip = body.get("ip")
    new_port = body.get("port")

    if not new_ip or not new_port:
        return err("Missing 'ip' or 'port' in request body", 400)

    try:
        new_port = int(new_port)
        registry.update_device_config(device_id, new_ip, new_port)
        return ok({"device_id": device_id, "ip": new_ip, "port": new_port})
    except Exception as e:
        return err(str(e), 400)


# ─────────────────────────────────────────────────────────────────────────────
# Generic device API proxy (for extensibility)
# ─────────────────────────────────────────────────────────────────────────────

def device_call(device_id: str, fn, *a, **kw):
    """Helper: call fn(device, *a, **kw) with auto-reconnect on error."""
    for attempt in range(2):
        try:
            if STUB_MODE:
                # Return None for stub; handlers will use _stub_* functions
                return None
            driver = registry.get_driver(device_id)
            return fn(driver, *a, **kw)
        except (ConnectionError, OSError, TimeoutError) as e:
            log.warning(f"Device call failed for {device_id} (attempt {attempt+1}): {e}")
            registry.reset_driver(device_id)
            if attempt == 1:
                raise RuntimeError(str(e)) from e
            time.sleep(0.1)


# ─────────────────────────────────────────────────────────────────────────────
# PSU ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/psu/status")
def psu_status():
    if STUB_MODE:
        return ok({"device": "MP711001", "channels": 4, "stub": True})
    try:
        registry.get_driver("psu")
        return ok({"device": "MP711001", "channels": 4})
    except Exception as e:
        registry.reset_driver("psu")
        return err(f"PSU not reachable: {e}")


@app.route("/api/psu/channel/<int:ch>/voltage", methods=["POST"])
def psu_set_voltage(ch):
    if ch not in range(1, 5):
        return err("Channel must be 1–4", 400)
    body = request.get_json(silent=True) or {}
    v = body.get("voltage")
    if v is None:
        return err("Missing 'voltage'", 400)
    v = float(v)
    if STUB_MODE:
        _stub_state["psu"]["channels"][ch]["voltage_set"] = v
        log.info(f"[STUB] PSU CH{ch} voltage → {v}V")
        return ok({"channel": ch, "voltage": v})
    try:
        device_call("psu", lambda d, _ch=ch, _v=v: d.set_voltage(_ch, _v))
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
        return err("Missing 'current'", 400)
    i = float(i)
    if STUB_MODE:
        _stub_state["psu"]["channels"][ch]["current_set"] = i
        log.info(f"[STUB] PSU CH{ch} current → {i}A")
        return ok({"channel": ch, "current": i})
    try:
        device_call("psu", lambda d, _ch=ch, _i=i: d.set_current(_ch, _i))
        log.info(f"PSU CH{ch} current → {i}A")
        return ok({"channel": ch, "current": i})
    except Exception as e:
        return err(str(e))


@app.route("/api/psu/channel/<int:ch>/output_on", methods=["POST"])
def psu_output_on(ch):
    if ch not in range(1, 5):
        return err("Channel must be 1–4", 400)
    if STUB_MODE:
        _stub_state["psu"]["channels"][ch]["output"] = True
        return ok({"channel": ch, "output": True})
    try:
        device_call("psu", lambda d, _ch=ch: d.output_on(_ch))
        log.info(f"PSU CH{ch} OUTPUT ON")
        return ok({"channel": ch, "output": True})
    except Exception as e:
        return err(str(e))


@app.route("/api/psu/channel/<int:ch>/output_off", methods=["POST"])
def psu_output_off(ch):
    if ch not in range(1, 5):
        return err("Channel must be 1–4", 400)
    if STUB_MODE:
        _stub_state["psu"]["channels"][ch]["output"] = False
        return ok({"channel": ch, "output": False})
    try:
        device_call("psu", lambda d, _ch=ch: d.output_off(_ch))
        log.info(f"PSU CH{ch} OUTPUT OFF")
        return ok({"channel": ch, "output": False})
    except Exception as e:
        return err(str(e))


@app.route("/api/psu/channel/<int:ch>/measure")
def psu_measure(ch):
    if ch not in range(1, 5):
        return err("Channel must be 1–4", 400)
    if STUB_MODE:
        return ok(_stub_psu_measure(ch))
    try:
        result = device_call("psu", lambda d, _ch=ch: d.measure(_ch))
        return ok({
            "channel": ch,
            "voltage": float(result.get("voltage", 0)),
            "current": float(result.get("current", 0)),
        })
    except Exception as e:
        return err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# MULTIMETER ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

MM_MODE_MAP = {
    "dc_voltage": "measure_dc_voltage",
    "ac_voltage": "measure_ac_voltage",
    "dc_current": "measure_dc_current",
    "ac_current": "measure_ac_current",
    "resistance": "measure_resistance",
    "continuity": "measure_continuity",
    "diode": "measure_diode",
    "capacitance": "measure_capacitance",
    "frequency": "measure_frequency",
}


@app.route("/api/mm/status")
def mm_status():
    if STUB_MODE:
        return ok({"device": "MP730027", "stub": True})
    try:
        registry.get_driver("mm")
        return ok({"device": "MP730027"})
    except Exception as e:
        registry.reset_driver("mm")
        return err(f"MM not reachable: {e}")


@app.route("/api/mm/measure/<mode>")
def mm_measure(mode):
    if mode not in MM_MODE_MAP:
        return err(f"Unknown mode '{mode}'", 400)
    if STUB_MODE:
        return ok(_stub_mm_measure(mode))
    try:
        method_name = MM_MODE_MAP[mode]
        raw = device_call("mm", lambda d, _m=method_name: getattr(d, _m)())
        value = float(raw) if raw is not None else 0.0
        log.debug(f"MM {mode} = {value}")
        return ok({"mode": mode, "value": value})
    except Exception as e:
        return err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# DC LOAD ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

DCL_MODE_FN = {
    "CC": "set_mode_current",
    "CV": "set_mode_voltage",
    "CP": "set_mode_power",
    "CR": "set_mode_resistance",
}

DCL_SET_FN = {
    "current": "set_ci_current",
    "voltage": "set_cv_voltage",
    "power": "set_cp_power",
    "resistance": "set_cr_resistance",
}


@app.route("/api/dcload/status")
def dcl_status():
    if STUB_MODE:
        return ok({"device": "MP71077x", "stub": True})
    try:
        registry.get_driver("dcl")
        return ok({"device": "MP71077x"})
    except Exception as e:
        registry.reset_driver("dcl")
        return err(f"DCLoad not reachable: {e}")


@app.route("/api/dcload/mode", methods=["POST"])
def dcl_set_mode():
    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "").upper()
    if mode not in DCL_MODE_FN:
        return err(f"Unknown mode '{mode}'", 400)
    if STUB_MODE:
        _stub_state["dcl"]["mode"] = mode
        return ok({"mode": mode})
    try:
        fn_name = DCL_MODE_FN[mode]
        device_call("dcl", lambda d, _fn=fn_name: getattr(d, _fn)())
        log.info(f"DCLoad mode → {mode}")
        return ok({"mode": mode})
    except Exception as e:
        return err(str(e))


@app.route("/api/dcload/set/<parameter>", methods=["POST"])
def dcl_set_value(parameter):
    if parameter not in DCL_SET_FN:
        return err(f"Unknown parameter '{parameter}'", 400)
    body = request.get_json(silent=True) or {}
    value = body.get("value")
    if value is None:
        return err("Missing 'value'", 400)
    value = float(value)
    if STUB_MODE:
        _stub_state["dcl"]["set_value"] = value
        log.info(f"[STUB] DCLoad {parameter} → {value}")
        return ok({"parameter": parameter, "value": value})
    try:
        fn_name = DCL_SET_FN[parameter]
        device_call("dcl", lambda d, _fn=fn_name, _v=value: getattr(d, _fn)(_v))
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
        device_call("dcl", lambda d, *_: d.load_on())
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
        device_call("dcl", lambda d, *_: d.load_off())
        log.info("DCLoad LOAD OFF")
        return ok({"load": False})
    except Exception as e:
        return err(str(e))


@app.route("/api/dcload/measure")
def dcl_measure():
    if STUB_MODE:
        return ok(_stub_dcl_measure())
    try:
        result = device_call("dcl", lambda d, *_: d.measure())
        return ok({
            "voltage": float(result.get("voltage", 0)),
            "current": float(result.get("current", 0)),
        })
    except Exception as e:
        return err(str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Health & Config
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return ok({
        "stub_mode": STUB_MODE,
        "devices_count": len(registry.devices),
    })


if __name__ == "__main__":
    log.info("=" * 60)
    log.info(f"  Lab API Server with Device Discovery")
    log.info(f"  Port: {args.port}")
    log.info(f"  Stub Mode: {STUB_MODE}")
    log.info(f"  Devices Discovered: {len(registry.devices)}")
    log.info(f"  UI: http://localhost:{args.port}/")
    log.info("=" * 60)
    app.run(
        host="0.0.0.0",
        port=args.port,
        debug=args.debug,
        threaded=True,
        use_reloader=False,
    )
