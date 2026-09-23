from database import get_device_by_id, get_setting


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
            "severity": "High",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": None
        }

    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "severity": "Low",
        "confidence": 1.0,
        "action": "No action",
        "sensor_value": None
    }


# RULE 2
# ABNORMAL TEMPERATURE DETECTION
def check_abnormal_temperature(temperature, threshold=None):
    if threshold is None:
        threshold = get_setting("temperature_threshold", 50.0)

    # Check whether temperature is available and exceeds threshold
    if temperature is not None and isinstance(temperature, (int, float)) and not isinstance(temperature, bool) and temperature > threshold:
        print(f"SECURITY ALERT: Abnormal temperature detected - {temperature} (threshold: {threshold})")

        return {
            "is_suspicious": True,
            "event_type": "Abnormal temperature detected",
            "prediction": "Suspicious",
            "severity": "Medium",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": float(temperature)
        }

    # Normal temperature
    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "severity": "Low",
        "confidence": 1.0,
        "action": "No action",
        "sensor_value": None
    }


# RULE 3
# DYNAMIC INVALID SENSOR DATA DETECTION
def check_invalid_sensor_data(data, configured_sensors=None):
    """
    Validates sensor payload dynamically against the device's configured sensors.
    Supports partial payloads (devices do NOT need to send every sensor at once).
    Rejects:
      - Non-dictionary payloads
      - Empty payloads
      - Unconfigured sensor fields
      - Invalid sensor data types
    """
    # 1. Check if payload is a dictionary
    if not isinstance(data, dict):
        print("SECURITY ALERT: Invalid sensor data format (not a dictionary)")
        return {
            "is_suspicious": True,
            "event_type": "Invalid sensor data",
            "prediction": "Suspicious",
            "severity": "Medium",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": None
        }

    # 2. Check if payload is empty
    if len(data) == 0:
        print("SECURITY ALERT: Invalid sensor data - empty payload")
        return {
            "is_suspicious": True,
            "event_type": "Invalid sensor data",
            "prediction": "Suspicious",
            "severity": "Medium",
            "confidence": 1.0,
            "action": "Alert generated",
            "sensor_value": None
        }

    # If configured_sensors is explicitly provided, validate against configured sensors
    if configured_sensors is not None:
        allowed_sensors = [s.strip().lower() for s in configured_sensors]

        # 3. Check for unconfigured / unknown sensor fields in payload
        for field in data.keys():
            if field.lower() not in allowed_sensors:
                print(f"SECURITY ALERT: Invalid sensor data - Unconfigured sensor field '{field}' for device")
                return {
                    "is_suspicious": True,
                    "event_type": "Invalid sensor data",
                    "prediction": "Suspicious",
                    "severity": "Medium",
                    "confidence": 1.0,
                    "action": "Alert generated",
                    "sensor_value": None
                }

        # 4. Check data types for fields present in payload
        if "temperature" in data:
            val = data["temperature"]
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                print("SECURITY ALERT: Invalid temperature value:", val)
                return {
                    "is_suspicious": True,
                    "event_type": "Invalid sensor data",
                    "prediction": "Suspicious",
                    "severity": "Medium",
                    "confidence": 1.0,
                    "action": "Alert generated",
                    "sensor_value": None
                }

        if "humidity" in data:
            val = data["humidity"]
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                print("SECURITY ALERT: Invalid humidity value:", val)
                return {
                    "is_suspicious": True,
                    "event_type": "Invalid sensor data",
                    "prediction": "Suspicious",
                    "severity": "Medium",
                    "confidence": 1.0,
                    "action": "Alert generated",
                    "sensor_value": None
                }

        if "motion" in data:
            val = data["motion"]
            if type(val) is not int or isinstance(val, bool) or val not in (0, 1):
                print("SECURITY ALERT: Invalid motion value:", val)
                return {
                    "is_suspicious": True,
                    "event_type": "Invalid sensor data",
                    "prediction": "Suspicious",
                    "severity": "Medium",
                    "confidence": 1.0,
                    "action": "Alert generated",
                    "sensor_value": None
                }

        # Any generic future sensor: must be numeric
        for field, val in data.items():
            if field.lower() not in ("temperature", "humidity", "motion"):
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    print(f"SECURITY ALERT: Invalid {field} value:", val)
                    return {
                        "is_suspicious": True,
                        "event_type": "Invalid sensor data",
                        "prediction": "Suspicious",
                        "severity": "Medium",
                        "confidence": 1.0,
                        "action": "Alert generated",
                        "sensor_value": None
                    }

    else:
        # Legacy fallback if configured_sensors is not passed:
        # Validate fixed fields if present
        for field in ["temperature", "humidity", "motion"]:
            if field not in data:
                print("SECURITY ALERT: Invalid sensor data - Missing field:", field)
                return {
                    "is_suspicious": True,
                    "event_type": "Invalid sensor data",
                    "prediction": "Suspicious",
                    "severity": "Medium",
                    "confidence": 1.0,
                    "action": "Alert generated",
                    "sensor_value": None
                }

        if isinstance(data["temperature"], bool) or not isinstance(data["temperature"], (int, float)):
            return {
                "is_suspicious": True,
                "event_type": "Invalid sensor data",
                "prediction": "Suspicious",
                "severity": "Medium",
                "confidence": 1.0,
                "action": "Alert generated",
                "sensor_value": None
            }

        if isinstance(data["humidity"], bool) or not isinstance(data["humidity"], (int, float)):
            return {
                "is_suspicious": True,
                "event_type": "Invalid sensor data",
                "prediction": "Suspicious",
                "severity": "Medium",
                "confidence": 1.0,
                "action": "Alert generated",
                "sensor_value": None
            }

        if type(data["motion"]) is not int or isinstance(data["motion"], bool):
            return {
                "is_suspicious": True,
                "event_type": "Invalid sensor data",
                "prediction": "Suspicious",
                "severity": "Medium",
                "confidence": 1.0,
                "action": "Alert generated",
                "sensor_value": None
            }

    # Data is valid
    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "severity": "Low",
        "confidence": 1.0,
        "action": "No action",
        "sensor_value": None
    }


# RULE 4
# EXCESSIVE MQTT MESSAGE RATE DETECTION
def check_message_rate(message_count, rate_limit=None):
    if rate_limit is None:
        rate_limit = get_setting("message_rate_limit", 10)

    # Maximum allowed messages within the monitoring period
    if message_count > rate_limit:
        print(f"SECURITY ALERT: Excessive MQTT message rate detected: {message_count} (limit: {rate_limit})")

        return {
            "is_suspicious": True,
            "event_type": "Excessive MQTT message rate",
            "prediction": "Suspicious",
            "severity": "High",
            "confidence": 1.0,
            "action": "Block device",
            "sensor_value": None
        }

    return {
        "is_suspicious": False,
        "event_type": None,
        "prediction": "Normal",
        "severity": "Low",
        "confidence": 1.0,
        "action": "No action",
        "sensor_value": None
    }