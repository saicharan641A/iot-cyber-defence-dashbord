from flask import Flask, render_template, jsonify
from database import (
    initialize_database,
    insert_sample_devices,
    insert_sample_events,
    get_connection
)
from mqtt_handler import start_mqtt


app = Flask(__name__)


# Initialize database
initialize_database()
insert_sample_devices()
insert_sample_events()


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
    
@app.route('/security-events')
def security_events():
    return render_template("events.html")
     
@app.route("/devices")
def devices():
    return render_template("devices.html")

@app.route("/api/reports")
def get_reports():

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
    
@app.route("/reports")
def reports():
    return render_template("reports.html")


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.route("/api/sensor-data")
def get_sensor_data():

    connection = get_connection()

    sensor_data = connection.execute("""
        SELECT *
        FROM sensor_data
        ORDER BY id DESC
        LIMIT 20
    """).fetchall()

    connection.close()

    return jsonify([
        dict(row)
        for row in sensor_data
    ])

if __name__ == "__main__":
    start_mqtt()
    app.run(
        debug=True,
        use_reloader=False
    )