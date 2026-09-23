from flask import Flask, render_template, jsonify, request, redirect
from database import (
    initialize_database,
    insert_sample_devices,
    insert_sample_events,
    get_connection,
    get_all_devices_with_sensors,
    get_device_by_id,
    get_device_sensors,
    add_device,
    update_device,
    delete_device,
    get_system_settings,
    update_system_settings
)
from mqtt_handler import start_mqtt, is_mqtt_connected, reconnect_mqtt


app = Flask(__name__)


# Initialize database
initialize_database()
insert_sample_devices()
insert_sample_events()


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/devices", methods=["GET"])
def get_devices():
    devices = get_all_devices_with_sensors()
    return jsonify(devices)


@app.route("/api/devices", methods=["POST"])
def create_device():
    data = request.get_json() or {}
    device_id = (data.get("device_id") or "").strip()
    device_name = (data.get("device_name") or "").strip()
    device_type = (data.get("device_type") or "ESP32").strip()
    ip_address = (data.get("ip_address") or "").strip()
    sensors = data.get("sensors") or []

    if not device_id:
        return jsonify({"error": "Device ID is required"}), 400

    if not device_name:
        return jsonify({"error": "Device Name is required"}), 400

    existing = get_device_by_id(device_id)
    if existing:
        return jsonify({"error": f"Device '{device_id}' already exists"}), 409

    if not isinstance(sensors, list):
        sensors = [sensors]

    add_device(device_id, device_name, device_type, ip_address, sensors)
    return jsonify({
        "message": "Device added successfully",
        "device": {
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "ip_address": ip_address,
            "sensors": sensors,
            "status": "Online"
        }
    }), 201


@app.route("/api/devices/<device_id>", methods=["PUT"])
def modify_device(device_id):
    existing = get_device_by_id(device_id)
    if not existing:
        return jsonify({"error": f"Device '{device_id}' not found"}), 404

    data = request.get_json() or {}
    device_name = (data.get("device_name") or existing["device_name"]).strip()
    device_type = (data.get("device_type") or existing["device_type"]).strip()
    ip_address = (data.get("ip_address") or existing["ip_address"]).strip()
    sensors = data.get("sensors")

    update_device(device_id, device_name, device_type, ip_address, sensors)
    return jsonify({"message": f"Device '{device_id}' updated successfully"}), 200


@app.route("/api/devices/<device_id>", methods=["DELETE"])
def remove_device(device_id):
    existing = get_device_by_id(device_id)
    if not existing:
        return jsonify({"error": f"Device '{device_id}' not found"}), 404

    delete_device(device_id)
    return jsonify({"message": f"Device '{device_id}' deleted successfully"}), 200


@app.route("/api/devices/<device_id>/sensors", methods=["GET"])
def get_device_sensors_api(device_id):
    existing = get_device_by_id(device_id)
    if not existing:
        return jsonify({"error": f"Device '{device_id}' not found"}), 404

    sensors = get_device_sensors(device_id)
    return jsonify({
        "device_id": device_id,
        "sensors": sensors
    })


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

@app.route("/sensor-data")
def sensor_data():
    return render_template("sensor_data.html")


@app.route("/reports")
def reports():
    return redirect("/sensor-data")


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.route("/api/settings", methods=["GET"])
def get_settings_api():
    settings = get_system_settings()
    settings["mqtt_connected"] = is_mqtt_connected()
    return jsonify(settings)


@app.route("/api/settings", methods=["PUT"])
def update_settings_api():
    data = request.get_json() or {}
    errors = []
    updates = {}

    if "mqtt_broker_host" in data:
        host = str(data["mqtt_broker_host"]).strip()
        if not host:
            errors.append("MQTT Broker Host cannot be empty")
        else:
            updates["mqtt_broker_host"] = host

    if "mqtt_broker_port" in data:
        try:
            port = int(data["mqtt_broker_port"])
            if not (1 <= port <= 65535):
                errors.append("MQTT Broker Port must be between 1 and 65535")
            else:
                updates["mqtt_broker_port"] = port
        except (ValueError, TypeError):
            errors.append("MQTT Broker Port must be a valid integer")

    if "mqtt_topic" in data:
        topic = str(data["mqtt_topic"]).strip()
        if not topic:
            errors.append("MQTT Topic cannot be empty")
        else:
            updates["mqtt_topic"] = topic

    if "temperature_threshold" in data:
        try:
            temp = float(data["temperature_threshold"])
            if not (-50 <= temp <= 150):
                errors.append("Temperature threshold must be between -50°C and 150°C")
            else:
                updates["temperature_threshold"] = temp
        except (ValueError, TypeError):
            errors.append("Temperature threshold must be a valid number")

    if "message_rate_limit" in data:
        try:
            limit = int(data["message_rate_limit"])
            if limit <= 0:
                errors.append("Message rate limit must be greater than 0")
            else:
                updates["message_rate_limit"] = limit
        except (ValueError, TypeError):
            errors.append("Message rate limit must be a valid integer")

    if "message_rate_window" in data:
        try:
            window = int(data["message_rate_window"])
            if window <= 0:
                errors.append("Message rate window must be greater than 0")
            else:
                updates["message_rate_window"] = window
        except (ValueError, TypeError):
            errors.append("Message rate window must be a valid integer")

    if "device_block_duration" in data:
        try:
            block_dur = int(data["device_block_duration"])
            if block_dur <= 0:
                errors.append("Device block duration must be greater than 0")
            else:
                updates["device_block_duration"] = block_dur
        except (ValueError, TypeError):
            errors.append("Device block duration must be a valid integer")

    if errors:
        return jsonify({"error": "; ".join(errors), "errors": errors}), 400

    if not updates:
        return jsonify({"message": "No valid settings provided to update"}), 400

    # Check if MQTT broker params changed
    mqtt_changed = any(k in updates for k in ("mqtt_broker_host", "mqtt_broker_port", "mqtt_topic"))

    update_system_settings(updates)

    if mqtt_changed:
        try:
            reconnect_mqtt()
        except Exception as e:
            print("Failed to reconnect MQTT:", e)

    current_settings = get_system_settings()
    current_settings["mqtt_connected"] = is_mqtt_connected()
    return jsonify({
        "message": "Settings updated successfully",
        "settings": current_settings
    }), 200


@app.route("/api/mqtt-status", methods=["GET"])
def get_mqtt_status_api():
    return jsonify({
        "connected": is_mqtt_connected()
    })


@app.route("/api/sensor-data")
def get_sensor_data():
    device_id = request.args.get("device_id")
    limit = request.args.get("limit", type=int)

    connection = get_connection()

    if device_id and device_id.lower() != "all":
        if limit:
            rows = connection.execute("""
                SELECT *
                FROM sensor_data
                WHERE device_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (device_id, limit)).fetchall()
        else:
            rows = connection.execute("""
                SELECT *
                FROM sensor_data
                WHERE device_id = ?
                ORDER BY id DESC
            """, (device_id,)).fetchall()
    else:
        if limit:
            rows = connection.execute("""
                SELECT *
                FROM sensor_data
                ORDER BY id DESC
                LIMIT ?
            """, (limit,)).fetchall()
        else:
            rows = connection.execute("""
                SELECT *
                FROM sensor_data
                ORDER BY id DESC
            """).fetchall()

    connection.close()

    return jsonify([
        dict(row)
        for row in rows
    ])

if __name__ == "__main__":
    start_mqtt()
    app.run(
        debug=True,
        use_reloader=False
    )