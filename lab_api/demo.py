"""
Lab Equipment Accuracy & Voltage Drop Characterization
PSU (CH1) -> DC Load, Multimeter probed at PSU terminals

Measures:
  - Reading agreement between PSU, multimeter, and DC load
  - Voltage drop under increasing current (cable + connection resistance)
  - PSU regulation accuracy vs multimeter ground truth
"""

from psu_device import MP711001
from multimeter_device import MP730027
from dcload_device import MP71077x
from awg_device import MP750513
import time

SETTLE_AFTER_OUTPUT_ON  = 3.0   # s - PSU output enable to first reading
SETTLE_AFTER_VOLTAGE    = 2.0   # s - after changing PSU voltage setpoint
SETTLE_AFTER_CURRENT    = 1.5   # s - after changing load current setpoint
SETTLE_AFTER_OUTPUT_OFF = 2.0   # s - after disabling output before next test

PSU_IP   = "192.168.1.100"
MM_IP    = "192.168.1.99"
LOAD_IP  = "192.168.1.80"
AWG_IP   = "192.168.1.97"

print("=" * 70)
print("Lab Accuracy & Voltage Drop Characterization")
print("=" * 70)

# -----------------------------------------------------------------------
# Init
# -----------------------------------------------------------------------
print("\n[INIT] Connecting to devices...")
psu   = MP711001(PSU_IP)
mm    = MP730027(MM_IP, port=3000)
dcload = MP71077x(LOAD_IP, port=18190)

# Try to connect to AWG (optional - continues if not available)
awg = None
awg_available = False
try:
    awg = MP750513(AWG_IP, port=3000, timeout=5)
    if awg.is_connected():
        awg_available = True
        print("[OK] AWG connected")
except Exception as e:
    print(f"[WARNING] AWG not available: {e}")

if not dcload.is_connected():
    print("[WARNING] DC Load not responding - aborting.")
    exit(1)

print("[OK] Primary devices connected\n")

# Ensure everything is off before we start
psu.output_off(1)
dcload.load_off()
if awg_available:
    awg.output_off()
time.sleep(SETTLE_AFTER_OUTPUT_OFF)


# -----------------------------------------------------------------------
# TEST 1: No-load accuracy check at three voltage levels
# -----------------------------------------------------------------------
print("=" * 70)
print("TEST 1: No-Load Accuracy  (PSU vs Multimeter)")
print("=" * 70)
print(f"{'Set V':>6} | {'PSU V':>8} | {'MM V':>8} | {'Error (mV)':>10}")
print("-" * 70)

for target_v in [3.3, 5.0, 12.0]:
    psu.set_voltage(1, target_v)
    psu.set_current(1, 0.1)          # minimal current limit, no load connected
    psu.output_on(1)
    time.sleep(SETTLE_AFTER_OUTPUT_ON)

    psu_r = psu.measure(1)
    mm_v  = float(mm.measure_dc_voltage())
    psu_v = float(psu_r["voltage"])
    err   = (psu_v - mm_v) * 1000

    print(f"{target_v:>6.1f} | {psu_v:>8.4f} | {mm_v:>8.4f} | {err:>+10.1f}")

    psu.output_off(1)
    time.sleep(SETTLE_AFTER_OUTPUT_OFF)

print()


# -----------------------------------------------------------------------
# AWG TEST: Arbitrary Waveform Generator - 2-Channel Demo
# -----------------------------------------------------------------------
if awg_available:
    try:
        print("=" * 70)
        print("AWG DEMO: Setting and Activating Waveforms on 2 Channels")
        print("=" * 70)

        # Channel 1: 1 kHz sine wave
        print("\n[Channel 1] 1 kHz sine wave with 2.5 V offset")
        awg.set_waveform("SIN")
        awg.set_frequency(1000)
        awg.set_amplitude(3.3)
        awg.set_dc_offset(2.5)
        awg.set_phase(0)
        print(f"  Waveform:  {awg.get_waveform()}")
        print(f"  Frequency: {awg.get_frequency()} Hz")
        print(f"  Amplitude: {awg.get_amplitude()} V")
        print(f"  Offset:    {awg.get_dc_offset()} V")
        print(f"  Phase:     {awg.get_phase()} °")

        # Enable output
        awg.output_on()
        print("  Output:    ON")
        time.sleep(1.0)

        # Channel 2 note
        print("\n[Channel 2] Not currently supported")
        print("  Note: Only a single output channel is supported at this time.\n")

        # Keep output active for a moment
        time.sleep(2.0)

        # Disable output
        awg.output_off()
        print("[AWG] Output disabled\n")
    except Exception as e:
        print(f"[ERROR] AWG demo failed: {e}")
        print("Continuing with other tests...\n")
else:
    print("[SKIP] AWG demo skipped - device not available\n")


# -----------------------------------------------------------------------
# TEST 2: Voltage drop characterisation at 5 V
#         Sweep load current, record drop from PSU terminals to load sense
# -----------------------------------------------------------------------
print("=" * 70)
print("TEST 2: Voltage Drop vs Load Current  (5 V rail)")
print("=" * 70)

TARGET_V   = 5.0
LOAD_STEPS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]

psu.set_voltage(1, TARGET_V)
psu.set_current(1, 4.0)
psu.output_on(1)
time.sleep(SETTLE_AFTER_OUTPUT_ON)

dcload.set_mode_current()
dcload.set_ci_current(0.0)
dcload.load_on()
time.sleep(SETTLE_AFTER_CURRENT)

print(f"{'I set (A)':>10} | {'PSU V':>8} | {'MM V':>8} | {'Load V':>8} | {'Drop (mV)':>10} | {'Load I (A)':>11} | {'Power (W)':>10}")
print("-" * 90)

drop_results = []

for i_set in LOAD_STEPS:
    dcload.set_ci_current(i_set)
    time.sleep(SETTLE_AFTER_CURRENT)

    psu_r  = psu.measure(1)
    load_r = dcload.measure()
    mm_v   = float(mm.measure_dc_voltage())
    psu_v  = float(psu_r["voltage"])
    psu_i  = float(psu_r["current"])
    load_v = float(load_r["voltage"])
    load_i = float(load_r["current"])

    drop_mv = (psu_v - load_v) * 1000
    power   = load_v * load_i
    drop_results.append((i_set, drop_mv))

    print(f"{i_set:>10.2f} | {psu_v:>8.4f} | {mm_v:>8.4f} | {load_v:>8.4f} | {drop_mv:>+10.1f} | {load_i:>11.4f} | {power:>10.3f}")

dcload.load_off()
psu.output_off(1)
time.sleep(SETTLE_AFTER_OUTPUT_OFF)

# Derive cable+connection resistance from slope
if len(drop_results) >= 2:
    i0, d0 = drop_results[1]   # skip 0 A (no current, drop undefined)
    i1, d1 = drop_results[-1]
    if (i1 - i0) > 0:
        r_cable = (d1 - d0) / 1000 / (i1 - i0)
        print(f"\n  Estimated path resistance (cable + connectors): {r_cable*1000:.1f} mΩ")
print()


# -----------------------------------------------------------------------
# TEST 3: Regulation under load - three voltage rails
# -----------------------------------------------------------------------
print("=" * 70)
print("TEST 3: PSU Regulation  (3.3 V / 5 V / 12 V rails)")
print("=" * 70)

rails = [
    {"voltage": 3.3,  "loads": [0.5, 1.0, 1.5, 2.0]},
    {"voltage": 5.0,  "loads": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]},
    {"voltage": 12.0, "loads": [0.5, 1.0, 1.5, 2.0]},
]

for rail in rails:
    target_v = rail["voltage"]
    print(f"\n  {target_v} V rail:")
    print(f"  {'I (A)':>6} | {'PSU V':>8} | {'MM V':>8} | {'Load V':>8} | {'Sag (mV)':>9} | {'Reg err (mV)':>13}")
    print("  " + "-" * 68)

    psu.set_voltage(1, target_v)
    psu.set_current(1, 4.0)
    psu.output_on(1)
    time.sleep(SETTLE_AFTER_OUTPUT_ON)

    dcload.set_mode_current()
    dcload.set_ci_current(0.0)
    dcload.load_on()
    time.sleep(SETTLE_AFTER_CURRENT)

    # Baseline at no load
    base_r = psu.measure(1)
    base_v = float(base_r["voltage"])

    for i_set in rail["loads"]:
        dcload.set_ci_current(i_set)
        time.sleep(SETTLE_AFTER_CURRENT)

        psu_r  = psu.measure(1)
        load_r = dcload.measure()
        mm_v   = float(mm.measure_dc_voltage())
        psu_v  = float(psu_r["voltage"])
        load_v = float(load_r["voltage"])
        load_i = float(load_r["current"])

        sag_mv    = (base_v - load_v) * 1000    # voltage sag at load terminals
        reg_err   = (psu_v  - mm_v)   * 1000    # PSU display vs MM

        print(f"  {i_set:>6.2f} | {psu_v:>8.4f} | {mm_v:>8.4f} | {load_v:>8.4f} | {sag_mv:>+9.1f} | {reg_err:>+13.1f}")

    dcload.load_off()
    psu.output_off(1)
    time.sleep(SETTLE_AFTER_OUTPUT_OFF)

print()


# -----------------------------------------------------------------------
# TEST 4: Constant Resistance
# -----------------------------------------------------------------------
print("=" * 70)
print("TEST 4: Constant Resistance  (10 Ω)")
print("=" * 70)
print(f"{'Set V':>6} | {'PSU V':>8} | {'Load V':>8} | {'Load I':>8} | {'Calc I (V/R)':>13} | {'I error (mA)':>13}")
print("-" * 80)

dcload.set_mode_resistance()
dcload.set_cr_resistance(10.0)

for target_v in [3.3, 5.0, 10.0, 12.0]:
    psu.set_voltage(1, target_v)
    psu.set_current(1, 3.0)
    psu.output_on(1)
    time.sleep(SETTLE_AFTER_OUTPUT_ON)

    dcload.load_on()
    time.sleep(SETTLE_AFTER_CURRENT)

    psu_r  = psu.measure(1)
    load_r = dcload.measure()
    psu_v  = float(psu_r["voltage"])
    load_v = float(load_r["voltage"])
    load_i = float(load_r["current"])
    calc_i = load_v / 10.0
    i_err  = (load_i - calc_i) * 1000

    print(f"{target_v:>6.1f} | {psu_v:>8.4f} | {load_v:>8.4f} | {load_i:>8.4f} | {calc_i:>13.4f} | {i_err:>+13.1f}")

    dcload.load_off()
    psu.output_off(1)
    time.sleep(SETTLE_AFTER_OUTPUT_OFF)

print()


# -----------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------
print("=" * 70)
print("All tests completed.")
print("=" * 70)

# Cleanup
if awg_available:
    try:
        awg.output_off()
        print("\n[CLEANUP] AWG output disabled")
    except:
        pass