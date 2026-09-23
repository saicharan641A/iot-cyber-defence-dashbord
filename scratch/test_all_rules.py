import os
import sys

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import json
import time

import paho.mqtt.client as mqtt

from app import app
from database import get_connection, initialize_database
import mqtt_handler


# ============================================================
# INITIALIZE DATABASE
# ============================================================

initialize_database()


# ============================================================
# START MQTT RECEIVER
# ============================================================

print("Starting MQTT handler...")

mqtt_handler.start_mqtt()

time.sleep(2)


# ============================================================
# CREATE TEST MQTT PUBLISHER
# ============================================================

publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

publisher.connect(
    "localhost",
    1883,
    60
)

publisher.loop_start()

time.sleep(1)


# ============================================================
# TEST RESULT STORAGE
# ============================================================

results = []


# ============================================================
# HELPER: RECORD TEST RESULT
# ============================================================

def record_test(
    rule_name,
    trigger,
    expected_output,
    db_change,
    device_status,
    dashboard_change,
    events_change,
    sensor_change,
    passed,
    notes=""
):
    results.append({
        "rule_name": rule_name,
        "trigger": trigger,
        "expected_output": expected_output,
        "db_change": db_change,
        "device_status": device_status,
        "dashboard_change": dashboard_change,
        "events_change": events_change,
        "sensor_change": sensor_change,
        "passed": passed,
        "notes": notes
    })

    status = "PASS" if passed else "FAIL"

    print(
        f"[{status}] {rule_name}: "
        f"{trigger} -> {notes}"
    )


# ============================================================
# HELPER: GET LATEST SECURITY EVENT
# ============================================================

def get_latest_event():

    conn = get_connection()

    event = conn.execute(
        """
        SELECT *
        FROM security_events
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    conn.close()

    return dict(event) if event else None


# ============================================================
# HELPER: GET DEVICE
# ============================================================

def get_device(device_id):

    conn = get_connection()

    dev = conn.execute(
        """
        SELECT *
        FROM devices
        WHERE device_id = ?
        """,
        (device_id,)
    ).fetchone()

    conn.close()

    return dict(dev) if dev else None


# ============================================================
# HELPER: COUNT SENSOR DATA
# ============================================================

def count_sensor_data(device_id):

    conn = get_connection()

    count = conn.execute(
        """
        SELECT COUNT(*)
        FROM sensor_data
        WHERE device_id = ?
        """,
        (device_id,)
    ).fetchone()[0]

    conn.close()

    return count


# ============================================================
# TEST START
# ============================================================

print(
    "\n======================================================="
)

print(
    "RUNNING END-TO-END VERIFICATION OF SECURITY RULES"
)

print(
    "=======================================================\n"
)


# ============================================================
# TEST 0
# NORMAL VALID SENSOR TELEMETRY
# ============================================================

print("\n--- Test 0: Normal Telemetry ---")

sensor_count_before = count_sensor_data("ESP32_01")

normal_payload = {
    "temperature": 24.5
}

publisher.publish(
    "iot/esp32/01/sensor",
    json.dumps(normal_payload)
)

time.sleep(1.5)

sensor_count_after = count_sensor_data("ESP32_01")

dev_01 = get_device("ESP32_01")

passed_0 = (
    sensor_count_after == sensor_count_before + 1
    and dev_01 is not None
    and dev_01["status"] == "Online"
)

record_test(
    rule_name="NORMAL SENSOR TELEMETRY",
    trigger=(
        "ESP32_01 sends valid normal payload: "
        "temp=24.5, hum=55.0, motion=0"
    ),
    expected_output=(
        "Sensor data saved to database, "
        "status set to Online"
    ),
    db_change=(
        "New row in sensor_data, "
        "devices updated"
    ),
    device_status="Online",
    dashboard_change=(
        "Sensor gauges update, "
        "Online devices count incremented"
    ),
    events_change="No security event created",
    sensor_change="Telemetry saved in sensor_data",
    passed=passed_0,
    notes=(
        "Sensor data recorded and "
        "device status is Online"
    )
)


# ============================================================
# TEST 1
# RULE 1 — UNKNOWN DEVICE DETECTION
# ============================================================

print(
    "\n--- Test 1: Rule 1 - Unknown Device Detection ---"
)

sensor_count_99_before = count_sensor_data("ESP32_99")

unknown_payload = {
    "temperature": 22.0,
    "humidity": 45.0,
    "motion": 1
}

publisher.publish(
    "iot/esp32/99/sensor",
    json.dumps(unknown_payload)
)

time.sleep(1.5)

latest_event = get_latest_event()

dev_99 = get_device("ESP32_99")

sensor_count_99_after = count_sensor_data("ESP32_99")


passed_1 = (
    latest_event is not None
    and latest_event["device_id"] == "ESP32_99"
    and latest_event["event_type"]
        == "Unknown Device Detected"
    and latest_event["prediction"] == "Suspicious"
    and latest_event["confidence"] == 1.0
    and latest_event["action"]
        == "Alert generated"
    and latest_event["sensor_value"] is None
    and dev_99 is None
    and sensor_count_99_after
        == sensor_count_99_before
)


record_test(
    rule_name="RULE 1 — UNKNOWN DEVICE DETECTION",
    trigger=(
        "Publish message from "
        "unregistered device ESP32_99"
    ),
    expected_output=(
        "SECURITY ALERT: "
        "Unknown Device Detected"
    ),
    db_change=(
        "New security_events record with "
        "event_type='Unknown Device Detected', "
        "sensor_value=None"
    ),
    device_status=(
        "Device NOT added to devices table"
    ),
    dashboard_change=(
        "Security event appears in events list, "
        "unknown device does not appear"
    ),
    events_change=(
        "New event logged with "
        "prediction='Suspicious', confidence=1.0"
    ),
    sensor_change=(
        "Sensor data NOT stored in sensor_data"
    ),
    passed=passed_1,
    notes=(
        f"Event created={latest_event['event_type']}, "
        f"dev_99_exists={dev_99 is not None}, "
        f"sensor_stored="
        f"{sensor_count_99_after > sensor_count_99_before}"
    )
)


# ============================================================
# TEST 2
# RULE 2 — ABNORMAL TEMPERATURE DETECTION
# ============================================================

print(
    "\n--- Test 2: Rule 2 - "
    "Abnormal Temperature Detection ---"
)

sensor_count_01_before = count_sensor_data("ESP32_01")

abnormal_temp_payload = {
    "temperature": 75.0
}

publisher.publish(
    "iot/esp32/01/sensor",
    json.dumps(abnormal_temp_payload)
)

time.sleep(1.5)

latest_event_2 = get_latest_event()

dev_01_suspicious = get_device("ESP32_01")

sensor_count_01_after = count_sensor_data("ESP32_01")


passed_2 = (
    latest_event_2 is not None
    and latest_event_2["device_id"]
        == "ESP32_01"
    and latest_event_2["event_type"]
        == "Abnormal temperature detected"
    and latest_event_2["prediction"]
        == "Suspicious"
    and latest_event_2["confidence"]
        == 1.0
    and latest_event_2["action"]
        == "Alert generated"
    and latest_event_2["sensor_value"]
        == 75.0
    and dev_01_suspicious is not None
    and dev_01_suspicious["status"]
        == "Suspicious"
    and sensor_count_01_after
        == sensor_count_01_before + 1
)


# ============================================================
# TEST 2B
# NORMAL READING AFTER ABNORMAL TEMPERATURE
# ============================================================

normal_subsequent = {
    "temperature": 26.0
}

publisher.publish(
    "iot/esp32/01/sensor",
    json.dumps(normal_subsequent)
)

time.sleep(1.5)

dev_01_restored = get_device("ESP32_01")

latest_event_after_normal = get_latest_event()

passed_2b = (
    dev_01_restored is not None
    and dev_01_restored["status"] == "Online"
    and latest_event_after_normal is not None
    and latest_event_after_normal["id"]
        == latest_event_2["id"]
)


record_test(
    rule_name="RULE 2 — ABNORMAL TEMPERATURE DETECTION",
    trigger=(
        "ESP32_01 publishes temperature: "
        "75°C (> 50°C)"
    ),
    expected_output=(
        "SECURITY ALERT: "
        "Abnormal temperature detected (75°C)"
    ),
    db_change=(
        "security_events record with "
        "sensor_value=75.0, "
        "sensor_data record stored"
    ),
    device_status=(
        "Suspicious "
        "(resets to Online on subsequent "
        "normal reading)"
    ),
    dashboard_change=(
        "Suspicious Devices count incremented, "
        "Devices page shows Suspicious badge"
    ),
    events_change=(
        "Abnormal temp event appears"
    ),
    sensor_change=(
        "Valid abnormal sensor reading "
        "is stored in sensor_data"
    ),
    passed=(passed_2 and passed_2b),
    notes=(
        f"Abnormal event created with "
        f"sensor_value="
        f"{latest_event_2['sensor_value']}, "
        f"status="
        f"{dev_01_suspicious['status']}, "
        f"recovered_status="
        f"{dev_01_restored['status']}"
    )
)


# ============================================================
# TEST 3
# RULE 3 — INVALID SENSOR DATA DETECTION
# ============================================================

print(
    "\n--- Test 3: Rule 3 - "
    "Invalid Sensor Data Detection ---"
)


# ------------------------------------------------------------
# Test 3A: Missing field
# ------------------------------------------------------------

sensor_count_before_3a = count_sensor_data("ESP32_02")

test_3a_payload = {
    "humidity": 60,
    "motion": 1
}

publisher.publish(
    "iot/esp32/02/sensor",
    json.dumps(test_3a_payload)
)

time.sleep(1.5)

event_3a = get_latest_event()

sensor_count_after_3a = count_sensor_data("ESP32_02")

passed_3a = (
    event_3a is not None
    and event_3a["event_type"]
        == "Invalid sensor data"
    and sensor_count_after_3a
        == sensor_count_before_3a
)


# ------------------------------------------------------------
# Test 3B: Non-numeric temperature
# ------------------------------------------------------------

sensor_count_before_3b = count_sensor_data("ESP32_02")

test_3b_payload = {
    "temperature": "hot",
    "humidity": 60,
    "motion": 1
}

publisher.publish(
    "iot/esp32/02/sensor",
    json.dumps(test_3b_payload)
)

time.sleep(1.5)

event_3b = get_latest_event()

sensor_count_after_3b = count_sensor_data("ESP32_02")

passed_3b = (
    event_3b is not None
    and event_3b["event_type"]
        == "Invalid sensor data"
    and sensor_count_after_3b
        == sensor_count_before_3b
)


# ------------------------------------------------------------
# Test 3C: Non-integer motion
# ------------------------------------------------------------

sensor_count_before_3c = count_sensor_data("ESP32_02")

test_3c_payload = {
    "temperature": 30,
    "humidity": 60,
    "motion": "yes"
}

publisher.publish(
    "iot/esp32/02/sensor",
    json.dumps(test_3c_payload)
)

time.sleep(1.5)

event_3c = get_latest_event()

sensor_count_after_3c = count_sensor_data("ESP32_02")

passed_3c = (
    event_3c is not None
    and event_3c["event_type"]
        == "Invalid sensor data"
    and sensor_count_after_3c
        == sensor_count_before_3c
)


# ------------------------------------------------------------
# Final Rule 3 result
# ------------------------------------------------------------

passed_3 = (
    passed_3a
    and passed_3b
    and passed_3c
)


record_test(
    rule_name="RULE 3 — INVALID SENSOR DATA DETECTION",
    trigger=(
        "Missing field (3A), "
        "non-numeric temperature (3B), "
        "non-integer motion (3C)"
    ),
    expected_output=(
        "SECURITY ALERT: Invalid Sensor Data"
    ),
    db_change=(
        "security_events logged for each "
        "invalid payload with "
        "sensor_value=None"
    ),
    device_status=(
        "Device status NOT changed to Online "
        "because of invalid payload"
    ),
    dashboard_change=(
        "Security events table shows "
        "Invalid sensor data alerts"
    ),
    events_change=(
        "3 invalid sensor data events recorded"
    ),
    sensor_change=(
        "None of the invalid payloads "
        "stored in sensor_data"
    ),
    passed=passed_3,
    notes=(
        f"Test 3A (missing temp): {passed_3a}, "
        f"Test 3B (str temp): {passed_3b}, "
        f"Test 3C (str motion): {passed_3c}"
    )
)


# ============================================================
# TEST 4
# RULE 4 — EXCESSIVE MQTT MESSAGE RATE
# ============================================================

print(
    "\n--- Test 4: Rule 4 - "
    "Excessive MQTT Message Rate Detection ---"
)


# ------------------------------------------------------------
# Clear previous tracking state
# ------------------------------------------------------------

mqtt_handler.message_tracker["ESP32_02"] = []

if "ESP32_02" in mqtt_handler.blocked_devices:

    del mqtt_handler.blocked_devices[
        "ESP32_02"
    ]


# ------------------------------------------------------------
# Test 4A: Send 11 rapid messages
# ------------------------------------------------------------

for i in range(11):

    publisher.publish(
        "iot/esp32/02/sensor",
        json.dumps({
            "motion": 0
        })
    )

    time.sleep(0.05)


time.sleep(2)

event_4 = get_latest_event()

dev_02_blocked = get_device("ESP32_02")

is_in_blocked_dict = (
    "ESP32_02"
    in mqtt_handler.blocked_devices
)


# ------------------------------------------------------------
# Test 4B:
# 12th message while blocked must be rejected
# ------------------------------------------------------------

sensor_count_before_blocked = count_sensor_data(
    "ESP32_02"
)

publisher.publish(
    "iot/esp32/02/sensor",
    json.dumps({
        "motion": 0
    })
)

time.sleep(1)

sensor_count_after_blocked = count_sensor_data(
    "ESP32_02"
)

rejected_while_blocked = (
    sensor_count_after_blocked
    == sensor_count_before_blocked
)


# ------------------------------------------------------------
# Test 4C:
# Automatic unblocking
# ------------------------------------------------------------

mqtt_handler.blocked_devices[
    "ESP32_02"
] = time.time() - 1

time.sleep(2)

dev_02_unblocked = get_device(
    "ESP32_02"
)

unblocked_successfully = (
    dev_02_unblocked is not None
    and dev_02_unblocked["status"]
        == "Online"
    and "ESP32_02"
        not in mqtt_handler.blocked_devices
)


# ------------------------------------------------------------
# Test 4D:
# Post-unblock message accepted
# ------------------------------------------------------------

publisher.publish(
    "iot/esp32/02/sensor",
    json.dumps({
        "motion": 1
    })
)

time.sleep(1.5)

sensor_count_post_unblock = count_sensor_data(
    "ESP32_02"
)

accepted_after_unblock = (
    sensor_count_post_unblock
    == sensor_count_after_blocked + 1
)


# ------------------------------------------------------------
# Final Rule 4 result
# ------------------------------------------------------------

passed_4 = (
    event_4 is not None
    and event_4["event_type"]
        == "Excessive MQTT message rate"
    and event_4["prediction"]
        == "Suspicious"
    and event_4["confidence"] == 1.0
    and event_4["action"]
        == "Block device"
    and dev_02_blocked is not None
    and dev_02_blocked["status"]
        == "Blocked"
    and is_in_blocked_dict
    and rejected_while_blocked
    and unblocked_successfully
    and accepted_after_unblock
)


record_test(
    rule_name="RULE 4 — EXCESSIVE MQTT MESSAGE RATE",
    trigger=(
        "Send 11 rapid messages within "
        "10 seconds from ESP32_02"
    ),
    expected_output=(
        "SECURITY ALERT: Excessive MQTT "
        "message rate, Device blocked "
        "for 60 seconds"
    ),
    db_change=(
        "security_events logged with "
        "action='Block device'"
    ),
    device_status=(
        "Blocked -> Automatically "
        "unblocked to Online"
    ),
    dashboard_change=(
        "Blocked Devices count increments, "
        "device shows Blocked badge, "
        "restores to Online"
    ),
    events_change=(
        "Excessive rate security event logged"
    ),
    sensor_change=(
        "Messages while blocked are rejected "
        "and NOT stored; accepted after unblock"
    ),
    passed=passed_4,
    notes=(
        f"Triggered action={event_4['action']}, "
        f"Blocked status="
        f"{dev_02_blocked['status']}, "
        f"Rejected while blocked="
        f"{rejected_while_blocked}, "
        f"Unblocked to Online="
        f"{unblocked_successfully}, "
        f"Post-unblock accepted="
        f"{accepted_after_unblock}"
    )
)


# ============================================================
# TEST 5
# REST API + SENSOR DATA FILTERING
# ============================================================

print(
    "\n--- Test 5: REST API Endpoints ---"
)


with app.test_client() as client:

    # --------------------------------------------------------
    # Test Devices API
    # --------------------------------------------------------

    res_devices = client.get(
        "/api/devices"
    )

    devices_data = res_devices.get_json()


    # --------------------------------------------------------
    # Test Security Events API
    # --------------------------------------------------------

    res_events = client.get(
        "/api/security-events"
    )

    events_data = res_events.get_json()


    # --------------------------------------------------------
    # Test All Sensor Data API
    # --------------------------------------------------------

    res_sensor = client.get(
        "/api/sensor-data"
    )

    sensor_data = res_sensor.get_json()


    # --------------------------------------------------------
    # Test Device-Filtered Sensor Data API
    # --------------------------------------------------------

    res_sensor_filtered = client.get(
        "/api/sensor-data?device_id=ESP32_01"
    )

    filtered_sensor_data = (
        res_sensor_filtered.get_json()
    )


    # --------------------------------------------------------
    # Verify filtered sensor data
    # --------------------------------------------------------

    filtered_data_correct = (
        isinstance(
            filtered_sensor_data,
            list
        )
        and all(
            row["device_id"] == "ESP32_01"
            for row in filtered_sensor_data
        )
    )


    # --------------------------------------------------------
    # Final REST API result
    # --------------------------------------------------------

    passed_5 = (

        # Devices API
        res_devices.status_code == 200
        and isinstance(
            devices_data,
            list
        )
        and len(devices_data) > 0

        # Security Events API
        and res_events.status_code == 200
        and isinstance(
            events_data,
            list
        )
        and len(events_data) > 0

        # Sensor Data API
        and res_sensor.status_code == 200
        and isinstance(
            sensor_data,
            list
        )

        # Filtered Sensor Data API
        and res_sensor_filtered.status_code == 200
        and isinstance(
            filtered_sensor_data,
            list
        )
        and filtered_data_correct
    )


record_test(
    rule_name="REST API INTEGRATION",
    trigger=(
        "GET /api/devices, "
        "/api/security-events, "
        "/api/sensor-data and "
        "filtered sensor data"
    ),
    expected_output=(
        "All endpoints return HTTP 200 "
        "and valid JSON data"
    ),
    db_change=(
        "N/A (Read operations)"
    ),
    device_status=(
        "Reflects active device "
        "status accurately"
    ),
    dashboard_change=(
        "Frontend receives dynamic "
        "device and security data"
    ),
    events_change=(
        "Security events are returned correctly"
    ),
    sensor_change=(
        "All sensor data and "
        "device-filtered sensor data "
        "are returned correctly"
    ),
    passed=passed_5,
    notes=(
        f"Devices={res_devices.status_code}, "
        f"Events={res_events.status_code}, "
        f"Sensor Data={res_sensor.status_code}, "
        f"Filtered Sensor Data="
        f"{res_sensor_filtered.status_code}, "
        f"Filter Correct="
        f"{filtered_data_correct}"
    )
)


# ============================================================
# STOP MQTT PUBLISHER
# ============================================================

publisher.loop_stop()

publisher.disconnect()


# ============================================================
# FINAL TEST SUMMARY
# ============================================================

print(
    "\n======================================================="
)

print(
    "SUMMARY OF TEST RESULTS:"
)

print(
    "======================================================="
)


all_passed = True


for r in results:

    res_text = (
        "PASS"
        if r["passed"]
        else "FAIL"
    )

    if not r["passed"]:
        all_passed = False

    print(
        f"[{res_text}] "
        f"{r['rule_name']}"
    )


print(
    f"\nOverall Result: "
    f"{'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}"
)