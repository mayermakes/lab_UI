from flask import Flask, request, jsonify, send_from_directory
from .mp730027 import MP730027

app = Flask(__name__, static_folder="static")

multimeter = MP730027("192.168.1.99", port=3000)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/measure", methods=["POST"])
def measure():
    """
    POST body: {"mode": "dc_voltage"}
    Valid modes: dc_voltage, ac_voltage, dc_current, ac_current, resistance, continuity, temperature
    """
    d = request.json
    mode = d.get("mode", "dc_voltage")

    try:
        result = multimeter.measure(mode)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/measure/<mode>")
def measure_get(mode):
    """GET endpoint for quick measurement (mode in URL)."""
    try:
        result = multimeter.measure(mode)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(port=5001, debug=True)
