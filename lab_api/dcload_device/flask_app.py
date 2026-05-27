from flask import Flask, request, jsonify, send_from_directory
from .mp71077x import MP71077x

app = Flask(__name__, static_folder="static")

load = MP71077x("192.168.1.80")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/input", methods=["POST"])
def input_control():
    d = request.json

    if d["state"]:
        load.input_on()
    else:
        load.input_off()

    return jsonify({"ok": True})


@app.route("/set/voltage", methods=["POST"])
def set_voltage():
    d = request.json

    if d.get("cv") is not None:
        load.set_cv_voltage(float(d["cv"]))

    if d.get("upper") is not None:
        load.set_upper_voltage_limit(float(d["upper"]))

    if d.get("lower") is not None:
        load.set_lower_voltage_limit(float(d["lower"]))

    return jsonify({"ok": True})


@app.route("/set/current", methods=["POST"])
def set_current():
    d = request.json

    if d.get("ci") is not None:
        load.set_ci_current(float(d["ci"]))

    if d.get("upper") is not None:
        load.set_upper_current_limit(float(d["upper"]))

    if d.get("lower") is not None:
        load.set_lower_current_limit(float(d["lower"]))

    return jsonify({"ok": True})


@app.route("/set/power", methods=["POST"])
def set_power():
    d = request.json

    if d.get("cp") is not None:
        load.set_cp_power(float(d["cp"]))

    if d.get("upper") is not None:
        load.set_upper_power_limit(float(d["upper"]))

    if d.get("lower") is not None:
        load.set_lower_power_limit(float(d["lower"]))

    return jsonify({"ok": True})


@app.route("/set/resistance", methods=["POST"])
def set_resistance():
    d = request.json

    if d.get("cr") is not None:
        load.set_cr_resistance(float(d["cr"]))

    if d.get("upper") is not None:
        load.set_upper_resistance_limit(float(d["upper"]))

    if d.get("lower") is not None:
        load.set_lower_resistance_limit(float(d["lower"]))

    return jsonify({"ok": True})


@app.route("/get/voltage")
def get_voltage():
    return jsonify({
        "cv": load.get_cv_voltage(),
        "upper": load.get_upper_voltage_limit(),
        "lower": load.get_lower_voltage_limit(),
    })


@app.route("/get/current")
def get_current():
    return jsonify({
        "ci": load.get_ci_current(),
        "upper": load.get_upper_current_limit(),
        "lower": load.get_lower_current_limit(),
    })


@app.route("/get/power")
def get_power():
    return jsonify({
        "cp": load.get_cp_power(),
        "upper": load.get_upper_power_limit(),
        "lower": load.get_lower_power_limit(),
    })


@app.route("/get/resistance")
def get_resistance():
    return jsonify({
        "cr": load.get_cr_resistance(),
        "upper": load.get_upper_resistance_limit(),
        "lower": load.get_lower_resistance_limit(),
    })


@app.route("/input/state")
def input_state():
    return jsonify({"state": load.get_input_state()})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
