import socket
import time


class MP730027:
    """
    Simple SCPI driver for Multicomp-Pro MP730027 Multimeter.
    Designed to be stable, blocking, and safe (no polling loops inside).
    """

    def __init__(self, ip, port=3000, timeout=2):
        self.ip = ip
        self.port = port
        self.timeout = timeout

        self._connect()

    # -----------------------------
    # CONNECTION
    # -----------------------------
    def _connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.ip, self.port))
        time.sleep(0.2)

    def _reconnect(self):
        try:
            self.sock.close()
        except:
            pass
        time.sleep(0.5)
        self._connect()

    # -----------------------------
    # LOW LEVEL IO
    # -----------------------------
    def write(self, cmd):
        try:
            self.sock.sendall((cmd + "\n").encode())
            time.sleep(0.1)
        except:
            self._reconnect()
            self.sock.sendall((cmd + "\n").encode())
            time.sleep(0.1)

    def query(self, cmd):
        try:
            self.sock.sendall((cmd + "\n").encode())
            time.sleep(0.15)
            return self.sock.recv(1024).decode().strip()
        except:
            self._reconnect()
            self.sock.sendall((cmd + "\n").encode())
            time.sleep(0.15)
            return self.sock.recv(1024).decode().strip()

    # -----------------------------
    # MEASUREMENT (SAFE, SINGLE SHOT)
    # -----------------------------
    def measure_dc_voltage(self):
        """Measure DC voltage (V)."""
        self.write("CONF:VOLT:DC")
        time.sleep(0.2)
        return self.query("MEAS:VOLT:DC?")

    def measure_ac_voltage(self):
        """Measure AC voltage (V)."""
        self.write("CONF:VOLT:AC")
        time.sleep(0.2)
        return self.query("MEAS:VOLT:AC?")

    def measure_dc_current(self):
        """Measure DC current (A)."""
        self.write("CONF:CURR:DC")
        time.sleep(0.2)
        return self.query("MEAS:CURR:DC?")

    def measure_ac_current(self):
        """Measure AC current (A)."""
        self.write("CONF:CURR:AC")
        time.sleep(0.2)
        return self.query("MEAS:CURR:AC?")

    def measure_resistance(self):
        """Measure resistance (Ω)."""
        self.write("CONF:RES")
        time.sleep(0.2)
        return self.query("MEAS:RES?")

    def measure_continuity(self):
        """Test continuity (beeps if <50Ω)."""
        self.write("CONF:CONT")
        time.sleep(0.2)
        return self.query("MEAS:CONT?")

    def measure_temperature(self):
        """Measure temperature (°C)."""
        self.write("CONF:TEMP")
        time.sleep(0.2)
        return self.query("MEAS:TEMP?")

    # Convenience: auto-range measurements
    def measure(self, mode="dc_voltage"):
        """
        Simple measurement with auto-selected mode.
        Modes: 'dc_voltage', 'ac_voltage', 'dc_current', 'ac_current', 'resistance', 'continuity', 'temperature'
        """
        modes = {
            "dc_voltage": self.measure_dc_voltage,
            "ac_voltage": self.measure_ac_voltage,
            "dc_current": self.measure_dc_current,
            "ac_current": self.measure_ac_current,
            "resistance": self.measure_resistance,
            "continuity": self.measure_continuity,
            "temperature": self.measure_temperature,
        }

        if mode not in modes:
            raise ValueError(f"Unknown mode: {mode}. Valid modes: {list(modes.keys())}")

        return {
            "mode": mode,
            "value": modes[mode]()
        }
