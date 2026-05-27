import socket
import time


class MP711001:
    """
    Simple SCPI driver for Multicomp-Pro MP711001 4-channel PSU.
    Designed to be stable, blocking, and safe (no polling loops inside).
    """

    def __init__(self, ip, port=5025, timeout=2):
        self.ip = ip
        self.port = port
        self.timeout = timeout

        self._connect()
        self.active_channel = 1

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
    # CHANNEL CONTROL
    # -----------------------------
    def select_channel(self, ch: int):
        self.active_channel = ch
        self.write(f"INST CH{ch}")
        time.sleep(0.2)

    # -----------------------------
    # OUTPUT CONTROL
    # -----------------------------
    def output_on(self, ch: int):
        self.select_channel(ch)
        self.write("OUTP ON")

    def output_off(self, ch: int):
        self.select_channel(ch)
        self.write("OUTP OFF")

    # -----------------------------
    # SET PARAMETERS
    # -----------------------------
    def set_voltage(self, ch: int, voltage: float):
        self.select_channel(ch)
        self.write(f"VOLT {voltage}")

    def set_current(self, ch: int, current: float):
        self.select_channel(ch)
        self.write(f"CURR {current}")

    # -----------------------------
    # MEASUREMENT (SAFE, SINGLE SHOT)
    # -----------------------------
    def measure(self, ch: int):
        self.select_channel(ch)

        v = self.query("MEAS:VOLT?")
        i = self.query("MEAS:CURR?")

        return {
            "channel": ch,
            "voltage": v,
            "current": i
        }
    