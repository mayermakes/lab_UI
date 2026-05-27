from flask import Flask, request, jsonify, send_from_directory
from .mp711001 import MP711001

app = Flask(__name__, static_folder="static")

psu = MP711001("192.168.1.100")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/set", methods=["POST"])
def set_psu():
    d = request.json
    ch = int(d["channel"])

    if d.get("voltage") is not None:
        psu.set_voltage(ch, float(d["voltage"]))

    if d.get("current") is not None:
        psu.set_current(ch, float(d["current"]))

    return jsonify({"ok": True})


@app.route("/output", methods=["POST"])
def output():
    d = request.json
    ch = int(d["channel"])

    if d["state"]:
        psu.output_on(ch)
    else:
        psu.output_off(ch)

    return jsonify({"ok": True})


@app.route("/measure")
def measure():
    ch = 1  # keep simple: single active channel readback
    return jsonify(psu.measure(ch))


if __name__ == "__main__":
    app.run(port=5000, debug=True)
    