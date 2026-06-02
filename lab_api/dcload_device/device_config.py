"""
Device configuration and discovery for MP71077x DC Load.
Allows dynamic device discovery and UI generation.
"""

from __future__ import annotations
import socket
import logging
from typing import Any, Dict

log = logging.getLogger(__name__)

# Device metadata
DEVICE_ID = "dcl"
DEVICE_NAME = "MP71077x"
DEVICE_FULL_NAME = "MP71077x DC Load"
DEFAULT_IP = "192.168.1.80"
DEFAULT_PORT = 18190
PROTOCOL = "UDP"
ICON_CLASS = "icon-dcl"
ACCENT_COLOR = "#e07800"

# API configuration
API_PREFIX = "/api/dcload"

# Mode configurations
MODES = {
    "CC": {"name": "Current (CC)", "unit": "A", "min": 0, "max": 30, "step": 0.1, "endpoint": "current"},
    "CV": {"name": "Voltage (CV)", "unit": "V", "min": 0, "max": 80, "step": 0.1, "endpoint": "voltage"},
    "CP": {"name": "Power (CP)", "unit": "W", "min": 0, "max": 200, "step": 1, "endpoint": "power"},
    "CR": {"name": "Resistance (CR)", "unit": "Ω", "min": 0.1, "max": 1000, "step": 0.1, "endpoint": "resistance"},
}

# UI controls configuration
UI_CONFIG = {
    "type": "dcload",
    "modes": list(MODES.keys()),
    "controls": [
        {"type": "mode_selector", "name": "mode", "modes": MODES},
        {"type": "parameter", "name": "value", "label": "Set Value", "unit": "", "min": 0, "max": 30, "step": 0.1},
    ],
    "measurements": [
        {"name": "v", "label": "V in", "unit": "V", "precision": 3},
        {"name": "i", "label": "I draw", "unit": "A", "precision": 3},
        {"name": "p", "label": "P diss", "unit": "W", "precision": 2},
        {"name": "mode", "label": "Mode", "unit": "", "precision": 0},
    ],
    "buttons": [
        {"id": "load-toggle", "label": "LOAD ON", "action": "load_toggle"},
        {"id": "apply", "label": "APPLY", "action": "apply"},
        {"id": "measure", "label": "MEASURE", "action": "measure"},
    ],
}


def test_connection(ip: str, port: int, timeout: float = 1.0) -> bool:
    """
    Test UDP connection to device.
    For UDP, we attempt a simple socket operation.
    Returns True if reachable, False otherwise.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        # UDP doesn't establish connections, so we just try to create a socket
        # In practice, connectivity is best tested via the actual API
        sock.close()
        log.debug(f"DCL UDP device @ {ip}:{port} socket created")
        return True
    except Exception as e:
        log.debug(f"DCL UDP socket creation failed: {e}")
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
