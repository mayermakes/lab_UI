"""
Device configuration and discovery for MP711001 PSU.
Allows dynamic device discovery and UI generation.
"""

from __future__ import annotations
import socket
import logging
from typing import Any, Dict

log = logging.getLogger(__name__)

# Device metadata
DEVICE_ID = "psu"
DEVICE_NAME = "MP711001"
DEVICE_FULL_NAME = "MP711001 Power Supply"
DEFAULT_IP = "192.168.1.100"
DEFAULT_PORT = 5025
PROTOCOL = "TCP"
ICON_CLASS = "icon-psu"
ACCENT_COLOR = "#00dca0"

# API configuration
API_PREFIX = "/api/psu"
CHANNELS = 4

# Mode/measurement configurations
MODES = {
    "voltage": {"name": "Voltage", "unit": "V", "min": 0, "max": 30, "step": 0.1},
    "current": {"name": "Current Limit", "unit": "A", "min": 0, "max": 10, "step": 0.1},
}

# UI controls configuration
UI_CONFIG = {
    "type": "psu",
    "channels": CHANNELS,
    "controls": [
        {"type": "parameter", "name": "voltage", "label": "Voltage", "unit": "V", "min": 0, "max": 30, "step": 0.1},
        {"type": "parameter", "name": "current", "label": "Current Limit", "unit": "A", "min": 0, "max": 10, "step": 0.1},
    ],
    "measurements": [
        {"name": "v", "label": "V actual", "unit": "V", "precision": 3},
        {"name": "i", "label": "I actual", "unit": "A", "precision": 3},
    ],
    "buttons": [
        {"id": "output-toggle", "label": "OUTPUT ON", "action": "output_toggle"},
        {"id": "apply", "label": "APPLY", "action": "apply"},
        {"id": "measure", "label": "MEASURE", "action": "measure"},
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
        log.debug(f"PSU connectivity test @ {ip}:{port} → {reachable}")
        return reachable
    except Exception as e:
        log.debug(f"PSU connectivity test failed: {e}")
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
        "channels": CHANNELS,
        "uiConfig": UI_CONFIG,
    }
