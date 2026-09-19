from database import get_connection

#RULE 1
#UNKNOWN DEVICE DETECTION

def check_unknown_device(device_id):
    connection = get_connection()
    
    device = connection.execute(
        """
        SELECT * FROM device
        WHERE device_id = ?
        """,
        (device_id)
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