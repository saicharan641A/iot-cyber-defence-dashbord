from flask import Flask, render_template, jsonify

from database import (
    initialize_database,
    insert_sample_devices,
    get_connection
)


app = Flask(__name__)


# Initialize database
initialize_database()
insert_sample_devices()


@app.route("/")
def dashboard():

    return render_template("dashboard.html")


@app.route("/api/devices")
def get_devices():

    connection = get_connection()

    devices = connection.execute(
        "SELECT * FROM devices"
    ).fetchall()

    connection.close()

    return jsonify([
        dict(device)
        for device in devices
    ])
    
@app.route("/api/security-events")
def get_security_events():

    connection = get_connection()

    events = connection.execute("""
        SELECT *
        FROM security_events
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return jsonify([
        dict(event)
        for event in events
    ])


if __name__ == "__main__":
    app.run(debug=True)