"""
Device configuration and discovery for MP730027 Multimeter.
Allows dynamic device discovery and UI generation.
"""

from __future__ import annotations
import socket
import logging
from typing import Any, Dict

log = logging.getLogger(__name__)

# Device metadata
DEVICE_ID = "mm"
DEVICE_NAME = "MP730027"
DEVICE_FULL_NAME = "MP730027 Multimeter"
DEFAULT_IP = "192.168.1.99"
DEFAULT_PORT = 3000
PROTOCOL = "TCP"
ICON_CLASS = "icon-mm"
ACCENT_COLOR = "#00b8e0"

# API configuration
API_PREFIX = "/api/mm"

# Measurement modes configuration
MODES = {
    "dc_voltage": {"label": "DC Voltage", "unit": "V"},
    "ac_voltage": {"label": "AC Voltage", "unit": "V"},
    "dc_current": {"label": "DC Current", "unit": "A"},
    "ac_current": {"label": "AC Current", "unit": "A"},
    "resistance": {"label": "Resistance", "unit": "Ω"},
    "continuity": {"label": "Continuity", "unit": "Ω"},
    "diode": {"label": "Diode", "unit": "V"},
    "capacitance": {"label": "Capacitance", "unit": "F"},
    "frequency": {"label": "Frequency", "unit": "Hz"},
}

# UI controls configuration
UI_CONFIG = {
    "type": "multimeter",
    "modes": list(MODES.keys()),
    "controls": [
        {"type": "mode_selector", "name": "mode", "modes": MODES},
    ],
    "measurements": [
        {"name": "main", "label": "Reading", "unit": "", "precision": 4, "largeDisplay": True},
        {"name": "min", "label": "Min", "precision": 4},
        {"name": "max", "label": "Max", "precision": 4},
    ],
    "buttons": [
        {"id": "measure", "label": "MEASURE", "action": "measure"},
        {"id": "reset", "label": "RESET MIN/MAX", "action": "reset"},
    ],
}


def test_connection(ip: str, port: int, timeout: float = 1.0) -> bool:
    """
    Test TCP connection to device.
    Returns True if reachable, False otherwise.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        reachable = result == 0
        log.debug(f"MM connectivity test @ {ip}:{port} → {reachable}")
        return reachable
    except Exception as e:
        log.debug(f"MM connectivity test failed: {e}")
        return False


def get_device_info() -> Dict[str, Any]:
    """Return device metadata for UI generation."""
    return {
        "id": DEVICE_ID,
        "name": DEVICE_NAME,
        "fullName": DEVICE_FULL_NAME,
        "protocol": PROTOCOL,
        "apiPrefix": API_PREFIX,
        "iconClass": ICON_CLASS,
        "accentColor": ACCENT_COLOR,
        "uiConfig": UI_CONFIG,
    }
