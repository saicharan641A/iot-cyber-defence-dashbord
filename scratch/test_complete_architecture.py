import os
import sys
import json
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import (
    initialize_database,
    get_connection,
    get_device_by_id,
    get_device_sensors,
    delete_device
)
from security_rules import (
    check_unknown_device,
    check_abnormal_temperature,
    check_invalid_sensor_data,
    check_message_rate
)

results = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}{': ' + detail if detail else ''}")
    results.append((name, condition, detail))


def run_all_tests():
    initialize_database()

    with app.test_client() as client:
        print("\n=======================================================")
        print("PHASE A: DEVICE MANAGEMENT CRUD (Tests 1 - 7)")
        print("=======================================================")

        # Clean up any leftover test devices first
        for dev_id in ["TEST_DEV_A", "TEST_DEV_TEMP", "TEST_DEV_MOT", "TEST_DEV_HUM", "TEST_DEV_MULTI"]:
            delete_device(dev_id)

        # 1. Add device
        r = client.post("/api/devices", json={
            "device_id": "TEST_DEV_A",
            "device_name": "Generic Sensor Node",
            "device_type": "ESP32",
            "ip_address": "192.168.1.150",
            "sensors": []
        })
        check("Test 1: Add device", r.status_code == 201, f"Status: {r.status_code}")

        # 2. Add device with Temperature sensor
        r = client.post("/api/devices", json={
            "device_id": "TEST_DEV_TEMP",
            "device_name": "Boiler Temperature Node",
            "device_type": "ESP32",
            "ip_address": "192.168.1.151",
            "sensors": ["temperature"]
        })
        s = get_device_sensors("TEST_DEV_TEMP")
        check("Test 2: Add device with Temperature sensor", r.status_code == 201 and "temperature" in s, f"Sensors: {s}")

        # 3. Add device with Motion sensor
        r = client.post("/api/devices", json={
            "device_id": "TEST_DEV_MOT",
            "device_name": "Hallway PIR Sensor",
            "device_type": "ESP32",
            "ip_address": "192.168.1.152",
            "sensors": ["motion"]
        })
        s = get_device_sensors("TEST_DEV_MOT")
        check("Test 3: Add device with Motion sensor", r.status_code == 201 and "motion" in s, f"Sensors: {s}")

        # 4. Add device with Humidity sensor
        r = client.post("/api/devices", json={
            "device_id": "TEST_DEV_HUM",
            "device_name": "Greenhouse Humidity",
            "device_type": "ESP32",
            "ip_address": "192.168.1.153",
            "sensors": ["humidity"]
        })
        s = get_device_sensors("TEST_DEV_HUM")
        check("Test 4: Add device with Humidity sensor", r.status_code == 201 and "humidity" in s, f"Sensors: {s}")

        # 5. Add device with multiple sensors
        r = client.post("/api/devices", json={
            "device_id": "TEST_DEV_MULTI",
            "device_name": "Weather Station",
            "device_type": "ESP32",
            "ip_address": "192.168.1.154",
            "sensors": ["temperature", "humidity"]
        })
        s = get_device_sensors("TEST_DEV_MULTI")
        check("Test 5: Add device with multiple sensors", r.status_code == 201 and set(s) == {"temperature", "humidity"}, f"Sensors: {s}")

        # 6. Edit device
        r = client.put("/api/devices/TEST_DEV_A", json={
            "device_name": "Updated Gateway Node",
            "device_type": "ESP32-S3",
            "ip_address": "192.168.1.199",
            "sensors": ["motion", "temperature"]
        })
        dev_a = get_device_by_id("TEST_DEV_A")
        sensors_a = get_device_sensors("TEST_DEV_A")
        check("Test 6: Edit device", r.status_code == 200 and dev_a["device_name"] == "Updated Gateway Node" and set(sensors_a) == {"motion", "temperature"}, f"Name: {dev_a['device_name']}, Sensors: {sensors_a}")

        # 7. Remove device
        r = client.delete("/api/devices/TEST_DEV_A")
        dev_a_after = get_device_by_id("TEST_DEV_A")
        check("Test 7: Remove device", r.status_code == 200 and dev_a_after is None, f"Deleted successfully")

        print("\n=======================================================")
        print("PHASE B: DYNAMIC SENSOR PAYLOAD VALIDATION (Tests 8 - 12)")
        print("=======================================================")

        # 8. Valid temperature-only payload
        res8 = check_invalid_sensor_data({"temperature": 28.5}, configured_sensors=["temperature"])
        check("Test 8: Valid temperature-only payload", res8["is_suspicious"] is False, f"Result: {res8['prediction']}")

        # 9. Valid motion-only payload
        res9 = check_invalid_sensor_data({"motion": 1}, configured_sensors=["motion"])
        check("Test 9: Valid motion-only payload", res9["is_suspicious"] is False, f"Result: {res9['prediction']}")

        # 10. Valid humidity-only payload
        res10 = check_invalid_sensor_data({"humidity": 65.0}, configured_sensors=["humidity"])
        check("Test 10: Valid humidity-only payload", res10["is_suspicious"] is False, f"Result: {res10['prediction']}")

        # 11. Valid multi-sensor payload
        res11 = check_invalid_sensor_data({"temperature": 24.2, "humidity": 55.0}, configured_sensors=["temperature", "humidity"])
        check("Test 11: Valid multi-sensor payload", res11["is_suspicious"] is False, f"Result: {res11['prediction']}")

        # 12. Invalid/unconfigured sensor field
        res12 = check_invalid_sensor_data({"humidity": 60}, configured_sensors=["temperature"])
        check("Test 12: Invalid/unconfigured sensor field rejection", res12["is_suspicious"] is True and res12["severity"] == "Medium", f"Alert: {res12['event_type']}, Severity: {res12['severity']}")

        print("\n=======================================================")
        print("PHASE C: SECURITY RULES & SEVERITY (Tests 13 - 17)")
        print("=======================================================")

        # 13. Unknown device (Rule 1)
        res13 = check_unknown_device("ROGUE_ESP32_999")
        check("Test 13: Unknown device detection (Rule 1)", res13["is_suspicious"] is True and res13["severity"] == "High" and res13["action"] == "Alert generated", f"Severity: {res13['severity']}, Action: {res13['action']}")

        # 14. Abnormal temperature (Rule 2)
        res14 = check_abnormal_temperature(75.5)
        check("Test 14: Abnormal temperature detection (Rule 2)", res14["is_suspicious"] is True and res14["severity"] == "Medium" and res14["sensor_value"] == 75.5, f"Value: {res14['sensor_value']}, Severity: {res14['severity']}")

        # 15. Invalid JSON / Not a dictionary (Rule 3)
        res15 = check_invalid_sensor_data("not-a-dict", configured_sensors=["temperature"])
        check("Test 15: Invalid JSON / non-dictionary payload (Rule 3)", res15["is_suspicious"] is True and res15["severity"] == "Medium", f"Event: {res15['event_type']}")

        # 16. Invalid sensor value type (Rule 3)
        res16_str = check_invalid_sensor_data({"temperature": "seventy-five"}, configured_sensors=["temperature"])
        res16_bool = check_invalid_sensor_data({"motion": True}, configured_sensors=["motion"])
        check("Test 16: Invalid sensor value types (string/bool rejection)", res16_str["is_suspicious"] is True and res16_bool["is_suspicious"] is True, "Both rejected properly")

        # 17. Excessive MQTT rate (Rule 4)
        res17 = check_message_rate(11)
        check("Test 17: Excessive MQTT rate detection (Rule 4)", res17["is_suspicious"] is True and res17["severity"] == "High" and res17["action"] == "Block device", f"Severity: {res17['severity']}, Action: {res17['action']}")

        print("\n=======================================================")
        print("PHASE D: APIS & DASHBOARD INTEGRATION (Tests 18 - 21)")
        print("=======================================================")

        # 18. Sensor Data API (all devices)
        r18 = client.get("/api/sensor-data")
        data18 = r18.get_json()
        check("Test 18: Sensor Data API (all devices)", r18.status_code == 200 and isinstance(data18, list) and len(data18) > 0, f"Returned {len(data18)} records")

        # 19. Device-filtered Sensor Data API
        r19 = client.get("/api/sensor-data?device_id=ESP32_01")
        data19 = r19.get_json()
        all_esp01 = all(row["device_id"] == "ESP32_01" for row in data19)
        check("Test 19: Device-filtered Sensor Data API", r19.status_code == 200 and len(data19) > 0 and all_esp01, f"{len(data19)} records all ESP32_01")

        # 20. Security Events API with severity
        r20 = client.get("/api/security-events")
        events20 = r20.get_json()
        has_severity = all("severity" in e for e in events20)
        check("Test 20: Security Events API includes Severity field", r20.status_code == 200 and len(events20) > 0 and has_severity, f"{len(events20)} events with severity")

        # 21. Dashboard API integration & devices with configured sensors
        r21 = client.get("/api/devices")
        devs21 = r21.get_json()
        has_sensors_field = all("sensors" in d for d in devs21)
        check("Test 21: Dashboard API integration (devices with configured sensors)", r21.status_code == 200 and has_sensors_field, f"{len(devs21)} devices returned with sensors")

        # Clean up remaining test devices
        for dev_id in ["TEST_DEV_TEMP", "TEST_DEV_MOT", "TEST_DEV_HUM", "TEST_DEV_MULTI"]:
            delete_device(dev_id)

    print("\n=======================================================")
    print("FINAL SUMMARY OF 21 ARCHITECTURE TESTS")
    print("=======================================================")
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)
    print(f"Total Tests: {total} | Passed: {passed} | Failed: {failed}")

    if failed == 0:
        print("Overall Result: ALL 21 TESTS PASSED SUCCESSFULLY")
    else:
        print("Overall Result: SOME TESTS FAILED")
        for name, p, detail in results:
            if not p:
                print(f"  FAIL: {name} - {detail}")

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
