from database import get_connection

#RULE 1
#UNKNOWN DEVICE DETECTION

def check_unknown_device(device_id):
    connection = get_connection()
    
    device = connection.execute(
        """
        SELECT * FROM devices
        WHERE device_id = ?
        """,
        (device_id,)
    ).fetchone()
    
    connection.close()
    
    #If device not registered
    
    if device is None:
        print("Security Alert!")
        print("Unknown Device Detected " + device_id)
        
        return {
            "is_suspicious": True,
            "event_type": "Unknown Device Detected",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated"
        }
        
    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "confidence": 1.0,
        "action": "No action"
    }
    
#RULE 2
#ABNORMAL TEMPERATURE DETECTION
def check_abnormal_temperature(temperature):

    # Check whether temperature is available
    if temperature is not None and temperature > 50:

        print("SECURITY ALERT")
        print("Abnormal temperature detected:", temperature)

        return {
            "is_suspicious": True,
            "event_type": "Abnormal temperature detected",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated"
        }

    # Normal temperature
    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "confidence": 1.0,
        "action": "No action"
    }
    
# RULE 3
# INVALID SENSOR DATA DETECTION
def check_invalid_sensor_data(data):

    # Check whether all required fields exist

    required_fields = [
        "temperature",
        "humidity",
        "motion"
    ]

    for field in required_fields:

        if field not in data:

            print("SECURITY ALERT")
            print("Invalid sensor data")
            print("Missing field:", field)

            return {
                "is_suspicious": True,
                "event_type": "Invalid sensor data",
                "prediction": "Suspicious",
                "confidence": 1.0,
                "action": "Alert generated"
            }


    # Check temperature data type

    if not isinstance(data["temperature"], (int, float)):

        print("SECURITY ALERT")
        print("Invalid temperature value")

        return {
            "is_suspicious": True,
            "event_type": "Invalid sensor data",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated"
        }


    # Check humidity data type

    if not isinstance(data["humidity"], (int, float)):

        print("SECURITY ALERT")
        print("Invalid humidity value")

        return {
            "is_suspicious": True,
            "event_type": "Invalid sensor data",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated"
        }


    # Check motion data type

    if not isinstance(data["motion"], int):

        print("SECURITY ALERT")
        print("Invalid motion value")

        return {
            "is_suspicious": True,
            "event_type": "Invalid sensor data",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated"
        }


    # Data is valid

    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "confidence": 1.0,
        "action": "No action"
    }
    
#RULE 4
#EXCESSIVE MQTT MESSAGE RATE DETECTION
def check_message_rate(message_count):
    
    # Maximum allowed messages
    # within the monitoring period
    if message_count > 10:
        print("SECURITY ALERT")
        print("Excessive MQTT message rate detected: ", message_count)
        
        return {
            "is_suspicious": True,
            "event_type": "Excessive MQTT message rate",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert Generated"
        }
    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "confidence": 1.0,
        "action": "No action"
    }