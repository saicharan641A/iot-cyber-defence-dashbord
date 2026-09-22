import json
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt

from database import (
    get_connection,
    record_security_event,
    record_sensor_data,
    update_device_status
)
from security_rules import (
    check_unknown_device,
    check_abnormal_temperature,
    check_invalid_sensor_data,
    check_message_rate
)


# MQTT SETTINGS
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "iot/esp32/+/sensor"

# Message Rate Tracker
message_tracker = {}

# Device Block
blocked_devices = {}
BLOCK_DURATION = 60


def unblock_expired_devices():
    while True:
        current_time = time.time()
        for device_id, blocked_until in list(blocked_devices.items()):
            if current_time >= blocked_until:
                del blocked_devices[device_id]
                # Reset message tracker for this device
                message_tracker[device_id] = []
                update_device_status(device_id, "Online")
                print("========================================")
                print("SECURITY BLOCK EXPIRED")
                print("Device automatically unblocked:", device_id)
                print("========================================")
        time.sleep(1)


# WHEN MQTT CONNECTS
def on_connect(client, userdata, flags, reason_code, properties):
    print("========================================")
    print("MQTT connected successfully")
    print("MQTT Broker:", MQTT_BROKER)
    print("MQTT Port:", MQTT_PORT)
    print("========================================")

    client.subscribe(MQTT_TOPIC)
    print("Subscribed to:", MQTT_TOPIC)


# WHEN A MESSAGE ARRIVES
def on_message(client, userdata, message):
    try:
        # GET MQTT MESSAGE
        topic = message.topic
        payload = message.payload.decode("utf-8")

        print("\n----------------------------------------")
        print("MQTT Message Received")
        print("Topic:", topic)
        print("Message:", payload)

        # GET DEVICE ID FROM TOPIC (pattern: iot/esp32/<device_number>/sensor)
        topic_parts = topic.split("/")
        if len(topic_parts) != 4 or topic_parts[0] != "iot" or topic_parts[1] != "esp32" or topic_parts[3] != "sensor":
            print("Invalid MQTT topic format:", topic)
            return

        device_number = topic_parts[2]
        device_id = f"ESP32_{device_number}"
        print("Device:", device_id)

        # CHECK IF DEVICE IS CURRENTLY BLOCKED
        if device_id in blocked_devices:
            print("----------------------------------------")
            print("SECURITY BLOCK ACTIVE")
            print("Device is temporarily blocked:", device_id)
            print("Message rejected (sensor data NOT stored)")
            print("----------------------------------------")
            return

        # RULE 1: UNKNOWN DEVICE DETECTION
        unknown_result = check_unknown_device(device_id)
        if unknown_result["is_suspicious"]:
            print("----------------------------------------")
            print("SECURITY ALERT: Unknown Device Detected")
            print("Device:", device_id)
            print("Event:", unknown_result["event_type"])
            print("Prediction:", unknown_result["prediction"])
            print("Action:", unknown_result["action"])
            print("Message rejected (sensor data NOT stored, device NOT added)")
            print("----------------------------------------")

            record_security_event(
                device_id=device_id,
                event_type=unknown_result["event_type"],
                prediction=unknown_result["prediction"],
                confidence=unknown_result["confidence"],
                action=unknown_result["action"],
                sensor_value=None
            )
            return

        # RULE 4: EXCESSIVE MQTT MESSAGE RATE DETECTION
        current_time = time.time()
        if device_id not in message_tracker:
            message_tracker[device_id] = []

        message_tracker[device_id].append(current_time)

        # Keep only timestamps within sliding 10-second window
        message_tracker[device_id] = [
            t for t in message_tracker[device_id]
            if current_time - t <= 10
        ]
        message_count = len(message_tracker[device_id])
        print("Messages from", device_id, "in last 10 seconds:", message_count)

        rate_result = check_message_rate(message_count)
        if rate_result["is_suspicious"]:
            print("----------------------------------------")
            print("SECURITY ALERT: Excessive MQTT Message Rate")
            print("Device:", device_id)
            print("Message count:", message_count)
            print("Prediction:", rate_result["prediction"])
            print("Action:", rate_result["action"])
            print(f"Device blocked for {BLOCK_DURATION} seconds: {device_id}")
            print("Message rejected (sensor data NOT stored)")
            print("----------------------------------------")

            blocked_devices[device_id] = current_time + BLOCK_DURATION
            update_device_status(device_id, "Blocked")

            record_security_event(
                device_id=device_id,
                event_type=rate_result["event_type"],
                prediction=rate_result["prediction"],
                confidence=rate_result["confidence"],
                action=rate_result["action"],
                sensor_value=None
            )
            return

        # Parse JSON Payload
        try:
            data = json.loads(payload)
        except Exception:
            data = None

        # RULE 3: INVALID SENSOR DATA DETECTION
        invalid_data_result = check_invalid_sensor_data(data)
        if invalid_data_result["is_suspicious"]:
            print("----------------------------------------")
            print("SECURITY ALERT: Invalid Sensor Data")
            print("Device:", device_id)
            print("Event:", invalid_data_result["event_type"])
            print("Prediction:", invalid_data_result["prediction"])
            print("Action:", invalid_data_result["action"])
            print("Message rejected (sensor data NOT stored, device status NOT updated)")
            print("----------------------------------------")

            record_security_event(
                device_id=device_id,
                event_type=invalid_data_result["event_type"],
                prediction=invalid_data_result["prediction"],
                confidence=invalid_data_result["confidence"],
                action=invalid_data_result["action"],
                sensor_value=None
            )
            return

        temperature = data.get("temperature")
        humidity = data.get("humidity")
        motion = data.get("motion")

        print("Temperature:", temperature)
        print("Humidity:", humidity)
        print("Motion:", motion)

        # RULE 2: ABNORMAL TEMPERATURE DETECTION
        temp_result = check_abnormal_temperature(temperature)
        if temp_result["is_suspicious"]:
            print("----------------------------------------")
            print("SECURITY ALERT: Abnormal Temperature Detected")
            print("Device:", device_id)
            print("Abnormal temperature:", temperature)
            print("Event:", temp_result["event_type"])
            print("Prediction:", temp_result["prediction"])
            print("Action:", temp_result["action"])
            print("Setting device status to Suspicious")
            print("----------------------------------------")

            record_security_event(
                device_id=device_id,
                event_type=temp_result["event_type"],
                prediction=temp_result["prediction"],
                confidence=temp_result["confidence"],
                action=temp_result["action"],
                sensor_value=temperature
            )
            update_device_status(device_id, "Suspicious")
        else:
            # Normal reading -> Device status updated to Online
            update_device_status(device_id, "Online")

        # Record valid sensor telemetry
        record_sensor_data(device_id, temperature, humidity, motion)
        print("Sensor data saved to database")
        print("----------------------------------------")

    except Exception as error:
        print("Error processing MQTT message:", error)


# START MQTT
def start_mqtt():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2
    )

    client.on_connect = on_connect
    client.on_message = on_message

    print("Starting MQTT connection...")

    try:
        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        # Keep MQTT running in background thread
        mqtt_thread = threading.Thread(
            target=client.loop_forever,
            daemon=True
        )
        mqtt_thread.start()
        print("MQTT background thread started")

        # Keep unblock timer running in background thread
        threading.Thread(
            target=unblock_expired_devices,
            daemon=True
        ).start()

    except Exception as error:
        print("MQTT connection failed:", error)