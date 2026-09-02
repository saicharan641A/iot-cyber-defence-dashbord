import sqlite3
from pathlib import Path


DATABASE_PATH = Path("database/iot_security.db")


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():

    DATABASE_PATH.parent.mkdir(exist_ok=True)

    connection = get_connection()
    cursor = connection.cursor()

    # Devices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE NOT NULL,
            device_name TEXT NOT NULL,
            device_type TEXT,
            ip_address TEXT,
            status TEXT,
            last_seen TEXT
        )
    """)

    # Sensor data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            motion INTEGER,
            timestamp TEXT
        )
    """)

    # Security events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            event_type TEXT,
            prediction TEXT,
            confidence REAL,
            action TEXT,
            timestamp TEXT
        )
    """)

    connection.commit()
    connection.close()
    
def insert_sample_devices():

    connection = get_connection()
    cursor = connection.cursor()

    devices = [
        (
            "ESP32_01",
            "Temperature Sensor",
            "ESP32",
            "192.168.1.101",
            "Online",
            "Just now"
        ),
        (
            "ESP32_02",
            "Motion Sensor",
            "ESP32",
            "192.168.1.102",
            "Online",
            "Just now"
        ),
        (
            "ESP32_03",
            "IoT Device",
            "ESP32",
            "192.168.1.103",
            "Suspicious",
            "2 minutes ago"
        )
    ]

    for device in devices:

        cursor.execute("""
            INSERT OR IGNORE INTO devices
            (
                device_id,
                device_name,
                device_type,
                ip_address,
                status,
                last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, device)

    connection.commit()
    connection.close()
    
def insert_sample_events():

    connection = get_connection()
    cursor = connection.cursor()

    events = [
        (
            "ESP32_03",
            "Abnormal network activity",
            "Suspicious",
            0.92,
            "Alert generated",
            "Today"
        ),
        (
            "ESP32_01",
            "Normal sensor activity",
            "Normal",
            0.98,
            "No action",
            "Today"
        ),
        (
            "ESP32_02",
            "Device connected",
            "Normal",
            0.99,
            "No action",
            "Today"
        ),
        (
            "ESP32_03",
            "Unusual traffic pattern",
            "Suspicious",
            0.87,
            "Alert generated",
            "Yesterday"
        ),
        (
            "ESP32_01",
            "Normal sensor activity",
            "Normal",
            0.97,
            "No action",
            "Yesterday"
        )
    ]

    for event in events:

        cursor.execute("""
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
        """, event)

    connection.commit()
    connection.close()
    
if __name__ == "__main__":
    initialize_database()
    insert_sample_devices()
    insert_sample_events()

    print("Database created successfully!")