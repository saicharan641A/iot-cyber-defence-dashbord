import sys
import os
import csv
import io
import re
from datetime import datetime

# Ensure app directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app


def test_csv_export_suite():
    client = app.test_client()
    today_str = datetime.now().strftime("%Y-%m-%d")

    print("\n=======================================================")
    print("PART 1: SECURITY EVENTS CSV EXPORT TESTS (Tests 1 - 7)")
    print("=======================================================")

    # Test 1: GET /api/security-events/export returns 200
    res = client.get("/api/security-events/export")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print("[PASS] Test 1: GET /api/security-events/export returns 200")

    # Test 2: Content-Type is text/csv
    content_type = res.headers.get("Content-Type", "")
    assert "text/csv" in content_type, f"Expected text/csv in Content-Type, got '{content_type}'"
    print(f"[PASS] Test 2: Content-Type is CSV ('{content_type}')")

    # Test 3: Content-Disposition contains a CSV filename
    content_disp = res.headers.get("Content-Disposition", "")
    assert "attachment" in content_disp, f"Expected attachment in Content-Disposition, got '{content_disp}'"
    expected_filename = f"security_events_{today_str}.csv"
    assert expected_filename in content_disp, f"Expected filename '{expected_filename}', got '{content_disp}'"
    print(f"[PASS] Test 3: Content-Disposition contains valid CSV filename ('{content_disp}')")

    # Test 4: CSV contains the expected headers
    csv_text = res.get_data(as_text=True)
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) > 0, "CSV output was empty"
    header = rows[0]
    expected_headers = ["Timestamp", "Device ID", "Event Type", "Severity", "Action"]
    assert header == expected_headers, f"Expected headers {expected_headers}, got {header}"
    print(f"[PASS] Test 4: CSV contains exact expected headers: {header}")

    # Test 5: CSV contains security event records without AI/ML fields
    assert len(rows) > 1, f"Expected at least 1 record row, got {len(rows)}"
    first_record = rows[1]
    assert len(first_record) == 5, f"Expected 5 columns in record row, got {len(first_record)}"
    # Check no AI/Prediction/Confidence words in header
    for h in header:
        assert "prediction" not in h.lower(), "Header must not contain 'prediction'"
        assert "confidence" not in h.lower(), "Header must not contain 'confidence'"
        assert "ai" not in h.lower(), "Header must not contain 'ai'"
    print(f"[PASS] Test 5: CSV contains {len(rows)-1} security event records without AI fields. Sample: {first_record}")

    # Test 6: Device filter works (?device_id=ESP32_01)
    res_filtered = client.get("/api/security-events/export?device_id=ESP32_01")
    assert res_filtered.status_code == 200
    rows_filtered = list(csv.reader(io.StringIO(res_filtered.get_data(as_text=True))))
    assert rows_filtered[0] == expected_headers
    data_rows_filtered = rows_filtered[1:]
    for r in data_rows_filtered:
        assert r[1] == "ESP32_01", f"Expected device_id ESP32_01, got '{r[1]}'"
    print(f"[PASS] Test 6: Device filter (?device_id=ESP32_01) returned {len(data_rows_filtered)} rows, all ESP32_01")

    # Test 7: Empty-result export does not crash
    res_empty = client.get("/api/security-events/export?device_id=NONEXISTENT_DEVICE_99999")
    assert res_empty.status_code == 200
    assert "text/csv" in res_empty.headers.get("Content-Type", "")
    rows_empty = list(csv.reader(io.StringIO(res_empty.get_data(as_text=True))))
    assert len(rows_empty) == 1, f"Expected exactly header row for empty result, got {len(rows_empty)}"
    assert rows_empty[0] == expected_headers
    print("[PASS] Test 7: Empty-result export does not crash, returns valid CSV with headers")


    print("\n=======================================================")
    print("PART 2: SENSOR DATA CSV EXPORT TESTS (Tests 8 - 14)")
    print("=======================================================")

    # Test 8: GET /api/sensor-data/export returns 200
    res_sd = client.get("/api/sensor-data/export")
    assert res_sd.status_code == 200, f"Expected 200, got {res_sd.status_code}"
    print("[PASS] Test 8: GET /api/sensor-data/export returns 200")

    # Test 9: Content-Type is text/csv
    content_type_sd = res_sd.headers.get("Content-Type", "")
    assert "text/csv" in content_type_sd, f"Expected text/csv in Content-Type, got '{content_type_sd}'"
    print(f"[PASS] Test 9: Content-Type is CSV ('{content_type_sd}')")

    # Test 10: Content-Disposition contains a CSV filename
    content_disp_sd = res_sd.headers.get("Content-Disposition", "")
    assert "attachment" in content_disp_sd, f"Expected attachment in Content-Disposition, got '{content_disp_sd}'"
    expected_filename_sd = f"sensor_data_{today_str}.csv"
    assert expected_filename_sd in content_disp_sd, f"Expected filename '{expected_filename_sd}', got '{content_disp_sd}'"
    print(f"[PASS] Test 10: Content-Disposition contains valid CSV filename ('{content_disp_sd}')")

    # Test 11: CSV contains: Timestamp, Device ID, Sensor Type, Sensor Value
    csv_text_sd = res_sd.get_data(as_text=True)
    rows_sd = list(csv.reader(io.StringIO(csv_text_sd)))
    assert len(rows_sd) > 0, "Sensor data CSV output was empty"
    header_sd = rows_sd[0]
    expected_headers_sd = ["Timestamp", "Device ID", "Sensor Type", "Sensor Value"]
    assert header_sd == expected_headers_sd, f"Expected headers {expected_headers_sd}, got {header_sd}"
    print(f"[PASS] Test 11: CSV contains exact expected headers: {header_sd}")

    # Test 12: Different sensor types export correctly (flexible format)
    assert len(rows_sd) > 1, f"Expected data records in sensor export, got {len(rows_sd)}"
    sensor_types_seen = set(r[2] for r in rows_sd[1:])
    print(f"       Observed sensor types in export: {sensor_types_seen}")
    assert any("temp" in st.lower() or "motion" in st.lower() or "humidity" in st.lower() for st in sensor_types_seen), "Should contain registered sensor types"
    print(f"[PASS] Test 12: Flexible sensor types exported correctly across {len(rows_sd)-1} total telemetry records")

    # Test 13: Device filter works (?device_id=ESP32_02)
    res_sd_filtered = client.get("/api/sensor-data/export?device_id=ESP32_02")
    assert res_sd_filtered.status_code == 200
    rows_sd_filtered = list(csv.reader(io.StringIO(res_sd_filtered.get_data(as_text=True))))
    assert rows_sd_filtered[0] == expected_headers_sd
    data_rows_sd_filtered = rows_sd_filtered[1:]
    for r in data_rows_sd_filtered:
        assert r[1] == "ESP32_02", f"Expected device_id ESP32_02, got '{r[1]}'"
    print(f"[PASS] Test 13: Device filter (?device_id=ESP32_02) returned {len(data_rows_sd_filtered)} records, all ESP32_02")

    # Test 14: Empty-result export does not crash
    res_sd_empty = client.get("/api/sensor-data/export?device_id=NONEXISTENT_DEVICE_99999")
    assert res_sd_empty.status_code == 200
    assert "text/csv" in res_sd_empty.headers.get("Content-Type", "")
    rows_sd_empty = list(csv.reader(io.StringIO(res_sd_empty.get_data(as_text=True))))
    assert len(rows_sd_empty) == 1, f"Expected exactly header row for empty result, got {len(rows_sd_empty)}"
    assert rows_sd_empty[0] == expected_headers_sd
    print("[PASS] Test 14: Empty-result sensor export does not crash, returns valid CSV with headers")


    print("\n=======================================================")
    print("PART 3: FRONTEND UI & BUTTON VERIFICATION (Tests 15 - 18)")
    print("=======================================================")

    # Test 15: Events page contains Export CSV button
    res_events_page = client.get("/security-events")
    assert res_events_page.status_code == 200
    events_html = res_events_page.get_data(as_text=True)
    assert "exportSecurityEventsCSV" in events_html or "Export CSV" in events_html
    print("[PASS] Test 15: templates/events.html contains Export CSV button")

    # Test 16: Sensor Data page contains Export CSV button
    res_sensor_page = client.get("/sensor-data")
    assert res_sensor_page.status_code == 200
    sensor_html = res_sensor_page.get_data(as_text=True)
    assert "exportSensorDataCSV" in sensor_html or "Export CSV" in sensor_html
    print("[PASS] Test 16: templates/sensor_data.html contains Export CSV button")

    # Test 17: events.js contains export function
    with open(os.path.join(os.path.dirname(__file__), "..", "static", "js", "events.js"), "r", encoding="utf-8") as f:
        events_js = f.read()
    assert "exportSecurityEventsCSV" in events_js
    assert "/api/security-events/export" in events_js
    print("[PASS] Test 17: static/js/events.js contains exportSecurityEventsCSV function")

    # Test 18: sensor_data.js contains export function with device filter
    with open(os.path.join(os.path.dirname(__file__), "..", "static", "js", "sensor_data.js"), "r", encoding="utf-8") as f:
        sensor_js = f.read()
    assert "exportSensorDataCSV" in sensor_js
    assert "/api/sensor-data/export" in sensor_js
    assert "device_id=" in sensor_js
    print("[PASS] Test 18: static/js/sensor_data.js contains exportSensorDataCSV with dynamic device filter")


    print("\n=======================================================")
    print("ALL 18 CSV EXPORT TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")


if __name__ == "__main__":
    test_csv_export_suite()
