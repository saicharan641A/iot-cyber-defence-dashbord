from datetime import datetime
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

    # Device sensors table (device-specific sensor configuration)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_sensors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            sensor_type TEXT NOT NULL,
            UNIQUE(device_id, sensor_type)
        )
    """)

    # Safe schema migration for sensor_data:
    # Check if sensor_data has the flexible schema (sensor_type, sensor_value)
    cursor.execute("PRAGMA table_info(sensor_data)")
    sensor_cols = [col[1] for col in cursor.fetchall()]

    if sensor_cols and "sensor_type" not in sensor_cols:
        # Migrate from fixed columns (temperature, humidity, motion) to flexible key-value model
        cursor.execute("ALTER TABLE sensor_data RENAME TO sensor_data_legacy")
        cursor.execute("""
            CREATE TABLE sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                sensor_value REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        if "temperature" in sensor_cols:
            cursor.execute("""
                INSERT INTO sensor_data (device_id, sensor_type, sensor_value, timestamp)
                SELECT device_id, 'temperature', CAST(temperature AS REAL), timestamp
                FROM sensor_data_legacy
                WHERE temperature IS NOT NULL
            """)
        if "humidity" in sensor_cols:
            cursor.execute("""
                INSERT INTO sensor_data (device_id, sensor_type, sensor_value, timestamp)
                SELECT device_id, 'humidity', CAST(humidity AS REAL), timestamp
                FROM sensor_data_legacy
                WHERE humidity IS NOT NULL
            """)
        if "motion" in sensor_cols:
            cursor.execute("""
                INSERT INTO sensor_data (device_id, sensor_type, sensor_value, timestamp)
                SELECT device_id, 'motion', CAST(motion AS REAL), timestamp
                FROM sensor_data_legacy
                WHERE motion IS NOT NULL
            """)
    elif not sensor_cols:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                sensor_value REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

    # Security events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            event_type TEXT,
            prediction TEXT,
            severity TEXT,
            confidence REAL,
            action TEXT,
            sensor_value REAL,
            timestamp TEXT
        )
    """)

    # Safe schema migration: add sensor_value column if it doesn't already exist
    cursor.execute("PRAGMA table_info(security_events)")
    columns = [col[1] for col in cursor.fetchall()]
    if "sensor_value" not in columns:
        cursor.execute("ALTER TABLE security_events ADD COLUMN sensor_value REAL")

    # Safe schema migration: add severity column if it doesn't already exist
    if "severity" not in columns:
        cursor.execute("ALTER TABLE security_events ADD COLUMN severity TEXT")
        cursor.execute("""
            UPDATE security_events
            SET severity = CASE
                WHEN event_type LIKE '%Unknown%' THEN 'High'
                WHEN event_type LIKE '%Excessive%' THEN 'High'
                WHEN event_type LIKE '%Abnormal%' THEN 'Medium'
                WHEN event_type LIKE '%Invalid%' THEN 'Medium'
                ELSE 'Medium'
            END
            WHERE severity IS NULL
        """)

    # Safe initial seeding of default device_sensors if empty
    cursor.execute("SELECT COUNT(*) FROM device_sensors")
    if cursor.fetchone()[0] == 0:
        default_sensors = [
            ("ESP32_01", "temperature"),
            ("ESP32_02", "motion"),
            ("ESP32_03", "humidity")
        ]
        for dev_id, s_type in default_sensors:
            cursor.execute("""
                INSERT OR IGNORE INTO device_sensors (device_id, sensor_type)
                VALUES (?, ?)
            """, (dev_id, s_type))

    # Centralized System Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Seed sensible defaults if keys do not already exist
    default_settings = {
        "mqtt_broker_host": "localhost",
        "mqtt_broker_port": "1883",
        "mqtt_topic": "iot/esp32/+/sensor",
        "temperature_threshold": "50",
        "message_rate_limit": "10",
        "message_rate_window": "10",
        "device_block_duration": "60"
    }
    for s_key, s_val in default_settings.items():
        cursor.execute("""
            INSERT OR IGNORE INTO system_settings (key, value)
            VALUES (?, ?)
        """, (s_key, str(s_val)))

    connection.commit()
    connection.close()


def get_system_settings():
    """Return all system settings as a dictionary with typed values."""
    default_settings = {
        "mqtt_broker_host": "localhost",
        "mqtt_broker_port": 1883,
        "mqtt_topic": "iot/esp32/+/sensor",
        "temperature_threshold": 50.0,
        "message_rate_limit": 10,
        "message_rate_window": 10,
        "device_block_duration": 60
    }
    connection = get_connection()
    rows = connection.execute("SELECT key, value FROM system_settings").fetchall()
    connection.close()

    settings = dict(default_settings)
    for row in rows:
        k = row["key"]
        v = row["value"]
        if k in ("mqtt_broker_port", "message_rate_limit", "message_rate_window", "device_block_duration"):
            try:
                settings[k] = int(v)
            except (ValueError, TypeError):
                settings[k] = default_settings.get(k, v)
        elif k == "temperature_threshold":
            try:
                settings[k] = float(v)
            except (ValueError, TypeError):
                settings[k] = default_settings.get(k, v)
        else:
            settings[k] = v

    return settings


def get_setting(key, default=None):
    """Retrieve a single system setting with proper type conversion."""
    connection = get_connection()
    row = connection.execute("SELECT value FROM system_settings WHERE key = ?", (key,)).fetchone()
    connection.close()

    if row is None:
        return default

    v = row["value"]
    if key in ("mqtt_broker_port", "message_rate_limit", "message_rate_window", "device_block_duration"):
        try:
            return int(v)
        except (ValueError, TypeError):
            return default
    elif key == "temperature_threshold":
        try:
            return float(v)
        except (ValueError, TypeError):
            return default
    return v


def update_system_settings(settings_dict):
    """Update system settings with persistence in system_settings table."""
    connection = get_connection()
    cursor = connection.cursor()

    for k, v in settings_dict.items():
        cursor.execute("""
            INSERT INTO system_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (k, str(v)))

    connection.commit()
    connection.close()


def get_device_sensors(device_id):
    """Return a list of configured sensor types for the device."""
    connection = get_connection()
    rows = connection.execute(
        "SELECT sensor_type FROM device_sensors WHERE device_id = ? ORDER BY id ASC",
        (device_id,)
    ).fetchall()
    connection.close()
    return [row["sensor_type"] for row in rows]


def set_device_sensors(device_id, sensor_types):
    """Set the configured sensors for a device (replaces existing)."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM device_sensors WHERE device_id = ?", (device_id,))
    for sensor in sensor_types:
        sensor_clean = sensor.strip().lower()
        if sensor_clean:
            cursor.execute(
                "INSERT OR IGNORE INTO device_sensors (device_id, sensor_type) VALUES (?, ?)",
                (device_id, sensor_clean)
            )
    connection.commit()
    connection.close()


def add_device(device_id, device_name, device_type, ip_address, sensor_types=None):
    """Add a new registered device with its configured sensors."""
    connection = get_connection()
    cursor = connection.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO devices (device_id, device_name, device_type, ip_address, status, last_seen)
        VALUES (?, ?, ?, ?, 'Online', ?)
    """, (device_id, device_name, device_type, ip_address, now_str))

    connection.commit()
    connection.close()

    if sensor_types:
        set_device_sensors(device_id, sensor_types)


def update_device(device_id, device_name, device_type, ip_address, sensor_types=None):
    """Update an existing device's details and configured sensors."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE devices
        SET device_name = ?,
            device_type = ?,
            ip_address = ?
        WHERE device_id = ?
    """, (device_name, device_type, ip_address, device_id))

    connection.commit()
    connection.close()

    if sensor_types is not None:
        set_device_sensors(device_id, sensor_types)


def delete_device(device_id):
    """Remove a device and its sensor configurations."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
    cursor.execute("DELETE FROM device_sensors WHERE device_id = ?", (device_id,))
    # Also clean up sensor data for deleted device
    cursor.execute("DELETE FROM sensor_data WHERE device_id = ?", (device_id,))

    connection.commit()
    connection.close()


def get_all_devices_with_sensors():
    """Return all devices with their configured sensors attached."""
    connection = get_connection()
    devices = connection.execute("SELECT * FROM devices ORDER BY id ASC").fetchall()
    result = []
    for d in devices:
        d_dict = dict(d)
        s_rows = connection.execute(
            "SELECT sensor_type FROM device_sensors WHERE device_id = ? ORDER BY id ASC",
            (d_dict["device_id"],)
        ).fetchall()
        d_dict["sensors"] = [s["sensor_type"] for s in s_rows]
        result.append(d_dict)
    connection.close()
    return result


def record_security_event(device_id, event_type, prediction, confidence, action, sensor_value=None, timestamp=None, severity=None):
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if severity is None:
        if "Unknown" in str(event_type) or "Excessive" in str(event_type):
            severity = "High"
        else:
            severity = "Medium"

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO security_events
        (
            device_id,
            event_type,
            prediction,
            severity,
            confidence,
            action,
            sensor_value,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (device_id, event_type, prediction, severity, confidence, action, sensor_value, timestamp))

    connection.commit()
    connection.close()


def record_sensor_reading(device_id, sensor_type, sensor_value, timestamp=None):
    """Record a single sensor reading into the flexible sensor_data table."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO sensor_data (device_id, sensor_type, sensor_value, timestamp)
        VALUES (?, ?, ?, ?)
    """, (device_id, sensor_type, float(sensor_value), timestamp))

    connection.commit()
    connection.close()


def record_sensor_readings(device_id, readings_dict, timestamp=None):
    """Record multiple sensor readings from a dictionary payload."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for sensor_type, val in readings_dict.items():
        if val is not None and isinstance(val, (int, float)) and not isinstance(val, bool):
            record_sensor_reading(device_id, sensor_type, val, timestamp)


def record_sensor_data(device_id, temperature=None, humidity=None, motion=None, timestamp=None):
    """Backward-compatible helper for recording sensor readings."""
    readings = {}
    if temperature is not None:
        readings["temperature"] = temperature
    if humidity is not None:
        readings["humidity"] = humidity
    if motion is not None:
        readings["motion"] = motion
    record_sensor_readings(device_id, readings, timestamp)


def update_device_status(device_id, status, last_seen=None):
    if last_seen is None:
        last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE devices
        SET status = ?,
            last_seen = ?
        WHERE device_id = ?
    """, (status, last_seen, device_id))

    connection.commit()
    connection.close()


def get_device_by_id(device_id):
    connection = get_connection()
    device = connection.execute(
        "SELECT * FROM devices WHERE device_id = ?",
        (device_id,)
    ).fetchone()
    connection.close()
    return device
    
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
            "Online",
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
    
    result = cursor.execute(
        """
        SELECT COUNT(*)
        FROM security_events
        """
    ).fetchone()
    
    event_count = result[0]
    if event_count > 0:
        connection.close()
        return

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