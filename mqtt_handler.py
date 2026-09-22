import json
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt

from database import get_connection
from security_rules import (check_unknown_device, check_abnormal_temperature, 
                            check_invalid_sensor_data, check_message_rate)


# MQTT SETTINGS

MQTT_BROKER = "localhost"
MQTT_PORT = 1883

MQTT_TOPIC = "iot/esp32/+/sensor"

#Message Rate Tracker
message_tracker = {}

#Device Block
blocked_devices = {}
BLOCK_DURATION = 60

def unblock_expired_devices():
    while True:
        current_time = time.time()
        for device_id, blocked_until in list(blocked_devices.items()):
            if current_time >= blocked_until:
                del blocked_devices[device_id]
                connection = get_connection()
                connection.execute(
                    """
                    UPDATE devices
                    SET status = 'Online'
                    WHERE device_id = ?
                    """,
                    (device_id,)
                )
                connection.commit()
                connection.close()
                print("SECURITY BLOCK EXPIRED")
                print("Device automatically unblocked:", device_id)


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


        # GET DEVICE ID FROM TOPIC

        topic_parts = topic.split("/")

        if len(topic_parts) != 4:

            print("Invalid MQTT topic")
            return


        device_number = topic_parts[2]

        device_id = f"ESP32_{device_number}"

        print("Device:", device_id)
        
        # CHECK IF DEVICE IS CURRENTLY BLOCKED
        if device_id in blocked_devices:

            print("SECURITY BLOCK")
            print("Device is temporarily blocked:", device_id)
            print("Message rejected")
            return
        
        # CONVERT JSON MESSAGE
        data = json.loads(payload)

        temperature = data.get("temperature")
        humidity = data.get("humidity")
        motion = data.get("motion")


        print("Temperature:", temperature)
        print("Humidity:", humidity)
        print("Motion:", motion)
        
        #RULE 4
        # MQTT MESSAGE RATE TRACKING
        
        current_time = time.time()
        
        if device_id not in message_tracker:
            message_tracker[device_id] = []
        
        message_tracker[device_id].append(current_time)
        
        #Keep only message from the last 10 seconds
        
        message_tracker[device_id] = [
            timestamp
            for timestamp in message_tracker[device_id]
            if current_time - timestamp <=10
        ]
        
        message_count = len(message_tracker[device_id])
        print("Messages from", device_id, "in last 10 seconds:", message_count)
        
        # CHECK MESSAGE RATE
        rate_result = check_message_rate(message_count)
        
        if rate_result["is_suspicious"]:
        
            print("----------------------------------------")
            print("SECURITY ALERT")
            print("Device:", device_id)
            print("Event:", rate_result["event_type"])
            print("Message count:", message_count)
            print("Prediction:", rate_result["prediction"])
            print("Action:", rate_result["action"])
            print("----------------------------------------")
           
            blocked_devices[device_id] = time.time() + BLOCK_DURATION
            print("SECURITY BLOCK")
            print("Device blocked for", BLOCK_DURATION, "seconds:", device_id)
            
            connection = get_connection()

            connection.execute(
                """
                UPDATE devices
                SET status = 'Blocked'
                WHERE device_id = ?
                """,
                (device_id,)
            )
            connection.commit()
            connection.close()
        
            connection = get_connection()
            connection.execute(
                """
                INSERT INTO security_events
                (
                    device_id,
                    event_type,
                    prediction,
                    confidence,
                    action,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    rate_result["event_type"],
                    rate_result["prediction"],
                    rate_result["confidence"],
                    rate_result["action"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )
        
            connection.commit()
            connection.close()
        
            print("Security event was stored successfully!")
            return
        
        #RULE 3
        #INVALID SENSOR DATA DETECTION
        invalid_data_result = check_invalid_sensor_data(data)

        if invalid_data_result["is_suspicious"]:

            print("----------------------------------------")
            print("SECURITY ALERT")
            print("Device:", device_id)
            print("Event:", invalid_data_result["event_type"])
            print("Prediction:", invalid_data_result["prediction"])
            print("Action:", invalid_data_result["action"])
            print("----------------------------------------")

            connection = get_connection()
            connection.execute(
                """
                INSERT INTO security_events
                (
                    device_id,
                    event_type,
                    prediction,
                    confidence,
                    action,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    invalid_data_result["event_type"],
                    invalid_data_result["prediction"],
                    invalid_data_result["confidence"],
                    invalid_data_result["action"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

            connection.commit()
            connection.close()

            print("Security event was stored successfully!")
            return


        # RULE 1
        # UNKNOWN DEVICE DETECTION

        security_result = check_unknown_device(device_id)

        if security_result["is_suspicious"]:

            print("----------------------------------------")
            print("SECURITY EVENT DETECTED")
            print("Device:", device_id)
            print("Event:", security_result["event_type"])
            print("Prediction:", security_result["prediction"])
            print("Action:", security_result["action"])
            print("----------------------------------------")


            connection = get_connection()

            connection.execute(
                """
                INSERT INTO security_events
                (
                    device_id,
                    event_type,
                    prediction,
                    confidence,
                    action,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    security_result["event_type"],
                    security_result["prediction"],
                    security_result["confidence"],
                    security_result["action"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

            connection.commit()
            connection.close()

            print("Security event was stored successfully!")
            return


        # RULE 2
        # ABNORMAL TEMPERATURE DETECTION

        temperature_result = check_abnormal_temperature(
            temperature
        )

        if temperature_result["is_suspicious"]:

            print("----------------------------------------")
            print("SECURITY ALERT")
            print(
                "Abnormal temperature detected:",
                temperature
            )
            print("Device:", device_id)
            print("Event:", temperature_result["event_type"])
            print("Prediction:", temperature_result["prediction"])
            print("Action:", temperature_result["action"])
            print("----------------------------------------")


            connection = get_connection()

            connection.execute(
                """
                INSERT INTO security_events
                (
                    device_id,
                    event_type,
                    prediction,
                    confidence,
                    action,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    temperature_result["event_type"],
                    temperature_result["prediction"],
                    temperature_result["confidence"],
                    temperature_result["action"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

            connection.commit()
            connection.close()

            print("Security event was stored successfully!")

        # SAVE SENSOR DATA
        connection = get_connection()

        connection.execute(
            """
            INSERT INTO sensor_data
            (
                device_id,
                temperature,
                humidity,
                motion,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                device_id,
                temperature,
                humidity,
                motion,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        # UPDATE DEVICE STATUS
        connection.execute(
            """
            UPDATE devices
            SET status = 'Online',
                last_seen = ?
            WHERE device_id = ?
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                device_id
            )
        )


        connection.commit()
        connection.close()


        print("Sensor data saved to database")
        print("----------------------------------------")


    except json.JSONDecodeError:

        print("Error: MQTT message is not valid JSON")


    except Exception as error:

        print("Error processing MQTT message:")
        print(error)

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


        # Keep MQTT running in background

        mqtt_thread = threading.Thread(
            target=client.loop_forever,
            daemon=True
        )

        mqtt_thread.start()


        print("MQTT background thread started")
        
        threading.Thread(
            target=unblock_expired_devices,
            daemon=True
        ).start()


    except Exception as error:

        print("MQTT connection failed:")
        print(error)