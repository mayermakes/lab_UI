import socket
import ipaddress
import re
import time


class MP71077x:
    """
    Simple SCPI driver for MP71077x series DC Electronic Load.
    Designed to be stable, blocking, and safe (no polling loops inside).
    """

    def __init__(self, ip, port=18190, timeout=0.5):
        self._target_ip = ip
        self._port = port
        self._timeout = timeout
        self._udp_socket = None

        self._connect()

    # -----------------------------
    # CONNECTION
    # -----------------------------
    def _connect(self):
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._udp_socket.bind(('0.0.0.0', self._port))
        except OSError as e:
            raise ConnectionError(f"Failed to bind to 0.0.0.0:{self._port}: {e}")
        self._udp_socket.settimeout(self._timeout)

    def _reconnect(self):
        try:
            self._udp_socket.close()
        except:
            pass
        time.sleep(0.5)
        self._connect()

    def is_connected(self):
        try:
            self._udp_socket.sendto(":INP?\n".encode(), (self._target_ip, self._port))
            self._udp_socket.recvfrom(1024)
            return True
        except:
            return False

    # -----------------------------
    # LOW LEVEL IO
    # -----------------------------
    def write(self, cmd):
        try:
            self._udp_socket.sendto((cmd + "\n").encode(), (self._target_ip, self._port))
        except:
            self._reconnect()
            self._udp_socket.sendto((cmd + "\n").encode(), (self._target_ip, self._port))

    def query(self, cmd):
        try:
            self._udp_socket.sendto((cmd + "\n").encode(), (self._target_ip, self._port))
            data, _ = self._udp_socket.recvfrom(1024)
            return data.decode().strip()
        except:
            self._reconnect()
            self._udp_socket.sendto((cmd + "\n").encode(), (self._target_ip, self._port))
            data, _ = self._udp_socket.recvfrom(1024)
            return data.decode().strip()

    # MP71077x uses only 5 valid digits of floating point number
    def _round(self, x: float):
        if x < 10.0:
            return round(x, 4)
        if x < 100.0:
            return round(x, 3)
        return round(x, 2)

    # -----------------------------
    # INPUT CONTROL
    # -----------------------------
    def input_on(self, verify: bool = False):
        self.write(":INP 1")
        if verify:
            response = self.query(":INP?")
            if "ON" not in response:
                raise ConnectionError("Cannot verify load input was turned on!")

    def input_off(self, verify: bool = False):
        self.write(":INP 0")
        if verify:
            response = self.query(":INP?")
            if "OFF" not in response:
                raise ConnectionError("Cannot verify load input was turned off!")

    def get_input_state(self):
        return self.query(":INP?")

    # Aliases used by demo scripts
    def load_on(self, verify: bool = False):
        self.input_on(verify)

    def load_off(self, verify: bool = False):
        self.input_off(verify)

    # -----------------------------
    # MODE SELECTION
    # -----------------------------
    def set_mode_current(self):
        self.write(":MODE CC")

    def set_mode_voltage(self):
        self.write(":MODE CV")

    def set_mode_power(self):
        self.write(":MODE CP")

    def set_mode_resistance(self):
        self.write(":MODE CR")

    def get_mode(self):
        return self.query(":MODE?")

    # -----------------------------
    # MEASUREMENT
    # -----------------------------
    def measure(self):
        v = float(re.sub(r"[^\d\.]", "", self.query(":MEAS:VOLT?")))
        i = float(re.sub(r"[^\d\.]", "", self.query(":MEAS:CURR?")))
        return {
            "voltage": v,
            "current": i,
        }

    # -----------------------------
    # VOLTAGE SETTINGS
    # -----------------------------
    def get_upper_voltage_limit(self):
        raw = self.query(":VOLT:UPP?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_upper_voltage_limit(self, limit: float, verify: bool = False):
        limit = self._round(limit)
        self.write(f":VOLT:UPP {limit}V")
        if verify:
            response = self.get_upper_voltage_limit()
            if response != limit:
                raise ConnectionError(f"Upper voltage limit mismatch: SET {limit}V, GET {response}V")

    def get_lower_voltage_limit(self):
        raw = self.query(":VOLT:LOW?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_lower_voltage_limit(self, limit: float, verify: bool = False):
        limit = self._round(limit)
        self.write(f":VOLT:LOW {limit}V")
        if verify:
            response = self.get_lower_voltage_limit()
            if response != limit:
                raise ConnectionError(f"Lower voltage limit mismatch: SET {limit}V, GET {response}V")

    def get_voltage_limits(self):
        return (self.get_lower_voltage_limit(), self.get_upper_voltage_limit())

    def get_cv_voltage(self):
        raw = self.query(":VOLT?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_cv_voltage(self, voltage: float, verify: bool = False):
        voltage = self._round(voltage)
        self.write(f":VOLT {voltage}V")
        if verify:
            response = self.get_cv_voltage()
            if response != voltage:
                raise ConnectionError(f"CV voltage mismatch: SET {voltage}V, GET {response}V")

    # -----------------------------
    # CURRENT SETTINGS
    # -----------------------------
    def get_upper_current_limit(self):
        raw = self.query(":CURR:UPP?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_upper_current_limit(self, limit: float, verify: bool = False):
        limit = self._round(limit)
        self.write(f":CURR:UPP {limit}A")
        if verify:
            response = self.get_upper_current_limit()
            if response != limit:
                raise ConnectionError(f"Upper current limit mismatch: SET {limit}A, GET {response}A")

    def get_lower_current_limit(self):
        raw = self.query(":CURR:LOW?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_lower_current_limit(self, limit: float, verify: bool = False):
        limit = self._round(limit)
        self.write(f":CURR:LOW {limit}A")
        if verify:
            response = self.get_lower_current_limit()
            if response != limit:
                raise ConnectionError(f"Lower current limit mismatch: SET {limit}A, GET {response}A")

    def get_current_limits(self):
        return (self.get_lower_current_limit(), self.get_upper_current_limit())

    def get_ci_current(self):
        raw = self.query(":CURR?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_ci_current(self, current: float, verify: bool = False):
        current = self._round(current)
        self.write(f":CURR {current}A")
        if verify:
            response = self.get_ci_current()
            if response != current:
                raise ConnectionError(f"CI current mismatch: SET {current}A, GET {response}A")

    # -----------------------------
    # POWER SETTINGS
    # -----------------------------
    def get_upper_power_limit(self):
        raw = self.query(":POW:UPP?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_upper_power_limit(self, limit: float, verify: bool = False):
        limit = self._round(limit)
        self.write(f":POW:UPP {limit}W")
        if verify:
            response = self.get_upper_power_limit()
            if response != limit:
                raise ConnectionError(f"Upper power limit mismatch: SET {limit}W, GET {response}W")

    def get_lower_power_limit(self):
        raw = self.query(":POW:LOW?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_lower_power_limit(self, limit: float, verify: bool = False):
        limit = self._round(limit)
        self.write(f":POW:LOW {limit}W")
        if verify:
            response = self.get_lower_power_limit()
            if response != limit:
                raise ConnectionError(f"Lower power limit mismatch: SET {limit}W, GET {response}W")

    def get_power_limits(self):
        return (self.get_lower_power_limit(), self.get_upper_power_limit())

    def get_cp_power(self):
        raw = self.query(":POW?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_cp_power(self, power: float, verify: bool = False):
        power = self._round(power)
        self.write(f":POW {power}W")
        if verify:
            response = self.get_cp_power()
            if response != power:
                raise ConnectionError(f"CP power mismatch: SET {power}W, GET {response}W")

    # -----------------------------
    # RESISTANCE SETTINGS
    # -----------------------------
    def get_upper_resistance_limit(self):
        raw = self.query(":RES:UPP?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_upper_resistance_limit(self, limit: float, verify: bool = False):
        limit = self._round(limit)
        self.write(f":RES:UPP {limit}OHM")
        if verify:
            response = self.get_upper_resistance_limit()
            if response != limit:
                raise ConnectionError(f"Upper resistance limit mismatch: SET {limit}OHM, GET {response}OHM")

    def get_lower_resistance_limit(self):
        raw = self.query(":RES:LOW?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_lower_resistance_limit(self, limit: float, verify: bool = False):
        limit = self._round(limit)
        self.write(f":RES:LOW {limit}OHM")
        if verify:
            response = self.get_lower_resistance_limit()
            if response != limit:
                raise ConnectionError(f"Lower resistance limit mismatch: SET {limit}OHM, GET {response}OHM")

    def get_resistance_limits(self):
        return (self.get_lower_resistance_limit(), self.get_upper_resistance_limit())

    def get_cr_resistance(self):
        raw = self.query(":RES?")
        return float(re.sub(r"[^\d\.]", "", raw))

    def set_cr_resistance(self, resistance: float, verify: bool = False):
        resistance = self._round(resistance)
        self.write(f":RES {resistance}OHM")
        if verify:
            response = self.get_cr_resistance()
            if response != resistance:
                raise ConnectionError(f"CR resistance mismatch: SET {resistance}OHM, GET {response}OHM")
            