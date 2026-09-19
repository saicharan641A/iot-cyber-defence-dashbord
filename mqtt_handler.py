import json
import threading
from datetime import datetime

import paho.mqtt.client as mqtt

from database import get_connection


# MQTT SETTINGS

MQTT_BROKER = "localhost"
MQTT_PORT = 1883

MQTT_TOPIC = "iot/esp32/+/sensor"


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

        # Get topic
        topic = message.topic

        # Get message payload
        payload = message.payload.decode("utf-8")

        print("\n----------------------------------------")
        print("MQTT Message Received")
        print("Topic:", topic)
        print("Message:", payload)


        # ==================================
        # GET DEVICE ID FROM TOPIC
        # ==================================

        # Example topic:
        #
        # iot/esp32/01/sensor
        #
        # Split:
        #
        # ["iot", "esp32", "01", "sensor"]

        topic_parts = topic.split("/")

        if len(topic_parts) != 4:

            print("Invalid MQTT topic")
            return


        device_number = topic_parts[2]

        device_id = f"ESP32_{device_number}"

        print("Device:", device_id)


        # CONVERT JSON MESSAGE

        data = json.loads(payload)


        temperature = data.get("temperature")
        humidity = data.get("humidity")
        motion = data.get("motion")


        print("Temperature:", temperature)
        print("Humidity:", humidity)
        print("Motion:", motion)


        # SAVE DATA TO DATABASE
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


        # Update device status and last seen time

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


    except Exception as error:

        print("MQTT connection failed:")
        print(error)