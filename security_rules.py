from database import get_device_by_id


# RULE 1
# UNKNOWN DEVICE DETECTION
def check_unknown_device(device_id):
    device = get_device_by_id(device_id)

    # If device not registered
    if device is None:
        print("SECURITY ALERT: Unknown Device Detected -", device_id)

        return {
            "is_suspicious": True,
            "event_type": "Unknown Device Detected",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": None
        }

    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "confidence": 1.0,
        "action": "No action",
        "sensor_value": None
    }


# RULE 2
# ABNORMAL TEMPERATURE DETECTION
def check_abnormal_temperature(temperature):
    # Check whether temperature is available and exceeds 50°C threshold
    if temperature is not None and isinstance(temperature, (int, float)) and not isinstance(temperature, bool) and temperature > 50:
        print("SECURITY ALERT: Abnormal temperature detected -", temperature)

        return {
            "is_suspicious": True,
            "event_type": "Abnormal temperature detected",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": temperature
        }

    # Normal temperature
    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "confidence": 1.0,
        "action": "No action",
        "sensor_value": None
    }


# RULE 3
# INVALID SENSOR DATA DETECTION
def check_invalid_sensor_data(data):
    # Check if payload is a dictionary
    if not isinstance(data, dict):
        print("SECURITY ALERT: Invalid sensor data format (not a dictionary)")
        return {
            "is_suspicious": True,
            "event_type": "Invalid sensor data",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": None
        }

    # Check whether all required fields exist
    required_fields = ["temperature", "humidity", "motion"]
    for field in required_fields:
        if field not in data:
            print("SECURITY ALERT: Invalid sensor data - Missing field:", field)
            return {
                "is_suspicious": True,
                "event_type": "Invalid sensor data",
                "prediction": "Suspicious",
                "confidence": 1.0,
                "action": "Alert generated",
                "sensor_value": None
            }

    # Check temperature data type (int or float, not bool)
    if isinstance(data["temperature"], bool) or not isinstance(data["temperature"], (int, float)):
        print("SECURITY ALERT: Invalid temperature value:", data["temperature"])
        return {
            "is_suspicious": True,
            "event_type": "Invalid sensor data",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": None
        }

    # Check humidity data type (int or float, not bool)
    if isinstance(data["humidity"], bool) or not isinstance(data["humidity"], (int, float)):
        print("SECURITY ALERT: Invalid humidity value:", data["humidity"])
        return {
            "is_suspicious": True,
            "event_type": "Invalid sensor data",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": None
        }

    # Check motion data type (must be int, not bool)
    if type(data["motion"]) is not int or isinstance(data["motion"], bool):
        print("SECURITY ALERT: Invalid motion value:", data["motion"])
        return {
            "is_suspicious": True,
            "event_type": "Invalid sensor data",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": None
        }

    # Data is valid
    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "confidence": 1.0,
        "action": "No action",
        "sensor_value": None
    }


# RULE 4
# EXCESSIVE MQTT MESSAGE RATE DETECTION
def check_message_rate(message_count):
    # Maximum allowed messages within the monitoring period (10 seconds)
    if message_count > 10:
        print("SECURITY ALERT: Excessive MQTT message rate detected:", message_count)

        return {
            "is_suspicious": True,
            "event_type": "Excessive MQTT message rate",
            "prediction": "Suspicious",
            "confidence": 1.0,
            "action": "Block device",
            "sensor_value": None
        }

    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "confidence": 1.0,
        "action": "No action",
        "sensor_value": None
    }