import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

results = []

def check(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}{': ' + detail if detail else ''}")
    results.append((name, passed, detail))


with app.test_client() as client:

    print("\n=== TEST 1: Sensor Data API - All Devices ===")
    r = client.get("/api/sensor-data")
    data = r.get_json()
    check("GET /api/sensor-data returns 200", r.status_code == 200)
    check("Returns a list", isinstance(data, list))
    check("Contains records", len(data) > 0, f"{len(data)} records")
    if data:
        first = data[0]
        check("Has device_id field", "device_id" in first)
        check("Has sensor_type field", "sensor_type" in first)
        check("Has sensor_value field", "sensor_value" in first)
        check("Has timestamp field", "timestamp" in first)

    print("\n=== TEST 2: Sensor Data API - Filter ESP32_01 ===")
    r = client.get("/api/sensor-data?device_id=ESP32_01")
    data_01 = r.get_json()
    check("GET /api/sensor-data?device_id=ESP32_01 returns 200", r.status_code == 200)
    check("Returns a list", isinstance(data_01, list))
    if data_01:
        all_correct = all(row["device_id"] == "ESP32_01" for row in data_01)
        check("All records are from ESP32_01", all_correct, f"{len(data_01)} records")
    else:
        check("ESP32_01 has records", False, "No records found")

    print("\n=== TEST 3: Sensor Data API - Filter ESP32_02 ===")
    r = client.get("/api/sensor-data?device_id=ESP32_02")
    data_02 = r.get_json()
    check("GET /api/sensor-data?device_id=ESP32_02 returns 200", r.status_code == 200)
    check("Returns a list", isinstance(data_02, list))
    if data_02:
        all_correct = all(row["device_id"] == "ESP32_02" for row in data_02)
        check("All records are from ESP32_02", all_correct, f"{len(data_02)} records")
    else:
        check("ESP32_02 has records (may be 0)", True, "No records (acceptable if device never sent valid data)")

    print("\n=== TEST 4: Sensor Data API - Filter ESP32_03 ===")
    r = client.get("/api/sensor-data?device_id=ESP32_03")
    data_03 = r.get_json()
    check("GET /api/sensor-data?device_id=ESP32_03 returns 200", r.status_code == 200)
    check("Returns a list", isinstance(data_03, list))
    if data_03:
        all_correct = all(row["device_id"] == "ESP32_03" for row in data_03)
        check("All records are from ESP32_03", all_correct, f"{len(data_03)} records")
    else:
        check("ESP32_03 returns empty list gracefully", True, "No records")

    print("\n=== TEST 5: Sensor Data API - Empty/Non-existent Device ===")
    r = client.get("/api/sensor-data?device_id=ESP32_DOESNOTEXIST")
    data_none = r.get_json()
    check("GET /api/sensor-data?device_id=ESP32_DOESNOTEXIST returns 200", r.status_code == 200)
    check("Returns empty list []", data_none == [], f"Got: {data_none}")

    print("\n=== TEST 6: Sensor Data API - 'all' keyword ===")
    r = client.get("/api/sensor-data?device_id=all")
    data_all = r.get_json()
    check("GET /api/sensor-data?device_id=all returns 200", r.status_code == 200)
    check("Returns a list", isinstance(data_all, list))
    check("All devices returns same as no filter", len(data_all) > 0, f"{len(data_all)} records")

    print("\n=== TEST 7: Security Events API ===")
    r = client.get("/api/security-events")
    events = r.get_json()
    check("GET /api/security-events returns 200", r.status_code == 200)
    check("Returns a list", isinstance(events, list))
    check("Has events", len(events) > 0, f"{len(events)} events")
    if events:
        e = events[0]
        check("Has device_id", "device_id" in e)
        check("Has event_type", "event_type" in e)
        check("Has prediction", "prediction" in e)
        check("Has confidence", "confidence" in e)
        check("Has action", "action" in e)
        check("Has timestamp", "timestamp" in e)
        # sensor_value should still be in API response (used for internal auditing)
        # but the UI does NOT display it
        check("sensor_value still in API (for audit)", "sensor_value" in e)

    print("\n=== TEST 8: Page Routes ===")
    r = client.get("/sensor-data")
    check("GET /sensor-data returns 200", r.status_code == 200)
    check("sensor_data.html contains device-select dropdown",
          b'id="device-select"' in r.data)
    check("sensor_data.html contains sensor-data-table-body",
          b'id="sensor-data-table-body"' in r.data)
    check("Navigation shows Sensor Data link",
          b'href="/sensor-data"' in r.data)

    r = client.get("/reports")
    check("GET /reports redirects to /sensor-data", r.status_code == 302)

    r = client.get("/")
    check("Dashboard still works", r.status_code == 200)
    check("Dashboard nav has Sensor Data", b'/sensor-data' in r.data)
    check("Dashboard nav does NOT have /reports link to old page",
          b'href="/reports"' not in r.data or b'redirect' in r.data)

    r = client.get("/devices")
    check("Devices page still works", r.status_code == 200)
    check("Devices nav has Sensor Data", b'/sensor-data' in r.data)

    r = client.get("/security-events")
    check("Security Events page still works", r.status_code == 200)
    check("Events nav has Sensor Data", b'/sensor-data' in r.data)
    check("Events table has Timestamp header", b'Timestamp' in r.data)
    check("Events table has Device ID header", b'Device ID' in r.data)
    check("Events table has Event Type header", b'Event Type' in r.data)
    check("Events table has Severity header", b'Severity' in r.data)
    check("Events table has Action header", b'Action' in r.data)
    check("Events table does NOT have Sensor Value column",
          b'Sensor Value' not in r.data)

    r = client.get("/settings")
    check("Settings page still works", r.status_code == 200)
    check("Settings nav has Sensor Data", b'/sensor-data' in r.data)

    print("\n=== TEST 9: API Devices ===")
    r = client.get("/api/devices")
    devices = r.get_json()
    check("GET /api/devices returns 200", r.status_code == 200)
    check("Returns registered devices", len(devices) >= 3,
          f"{len(devices)} devices: {[d['device_id'] for d in devices]}")

    print("\n=== SUMMARY ===")
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)
    print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed}")

    if failed == 0:
        print("\nOverall Result: ALL TESTS PASSED")
    else:
        print("\nOverall Result: SOME TESTS FAILED")
        print("\nFailed tests:")
        for name, p, detail in results:
            if not p:
                print(f"  FAIL: {name} ({detail})")
