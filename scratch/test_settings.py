import sys
import os
import json

# Ensure app directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import get_system_settings, update_system_settings, get_setting
from security_rules import check_abnormal_temperature, check_message_rate

def test_settings_suite():
    client = app.test_client()

    print("=== TEST 1: GET /api/settings ===")
    res = client.get("/api/settings")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.get_json()
    print("Settings data:", data)
    assert "mqtt_broker_host" in data
    assert "mqtt_broker_port" in data
    assert "mqtt_topic" in data
    assert "temperature_threshold" in data
    assert "message_rate_limit" in data
    assert "message_rate_window" in data
    assert "device_block_duration" in data
    assert "mqtt_connected" in data
    print("PASS: GET /api/settings structure verified.")

    print("\n=== TEST 2: GET /api/mqtt-status ===")
    res = client.get("/api/mqtt-status")
    assert res.status_code == 200
    status_data = res.get_json()
    assert "connected" in status_data
    print(f"PASS: GET /api/mqtt-status returned connected={status_data['connected']}")

    print("\n=== TEST 3: GET /settings (HTML page) ===")
    res = client.get("/settings")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "MQTT Configuration" in html
    assert "Security Rules" in html
    assert "Security Actions" in html
    assert "System Information" in html
    assert "settings.js" in html
    assert "Enable AI-based anomaly detection" not in html
    print("PASS: Settings HTML rendered correctly without stale AI placeholders.")

    print("\n=== TEST 4: PUT /api/settings (Valid Update) ===")
    # Update temperature threshold to 42.5
    res = client.put("/api/settings", json={"temperature_threshold": 42.5})
    assert res.status_code == 200
    assert get_setting("temperature_threshold") == 42.5
    print("PASS: Settings updated successfully to 42.5°C.")

    print("\n=== TEST 5: Dynamic Rule 2 Behavior ===")
    # Temperature 45 is > 42.5 -> suspicious!
    r2_alert = check_abnormal_temperature(45.0)
    assert r2_alert["is_suspicious"] is True, "45°C should be suspicious when threshold is 42.5"
    # Temperature 40 is <= 42.5 -> normal
    r2_normal = check_abnormal_temperature(40.0)
    assert r2_normal["is_suspicious"] is False, "40°C should be normal when threshold is 42.5"
    print("PASS: Dynamic Rule 2 responded immediately to updated threshold.")

    print("\n=== TEST 6: Dynamic Rule 4 Behavior ===")
    # Update rate limit to 5
    res = client.put("/api/settings", json={"message_rate_limit": 5})
    assert res.status_code == 200
    assert get_setting("message_rate_limit") == 5
    # Message count 6 > 5 -> suspicious!
    r4_alert = check_message_rate(6)
    assert r4_alert["is_suspicious"] is True, "6 messages should trigger rate alert when limit is 5"
    # Message count 4 <= 5 -> normal
    r4_normal = check_message_rate(4)
    assert r4_normal["is_suspicious"] is False, "4 messages should be normal when limit is 5"
    print("PASS: Dynamic Rule 4 responded immediately to updated rate limit.")

    print("\n=== TEST 7: Reset to standard defaults ===")
    res = client.put("/api/settings", json={
        "temperature_threshold": 50.0,
        "message_rate_limit": 10,
        "message_rate_window": 10,
        "device_block_duration": 60,
        "mqtt_broker_host": "localhost",
        "mqtt_broker_port": 1883,
        "mqtt_topic": "iot/esp32/+/sensor"
    })
    assert res.status_code == 200
    assert get_setting("temperature_threshold") == 50.0
    assert get_setting("message_rate_limit") == 10
    print("PASS: Settings restored to standard defaults.")

    print("\n=== TEST 8: Input Validation Rejections ===")
    # Test invalid port (> 65535)
    res = client.put("/api/settings", json={"mqtt_broker_port": 99999})
    assert res.status_code == 400
    assert "between 1 and 65535" in res.get_json()["error"]

    # Test invalid temperature (< -50)
    res = client.put("/api/settings", json={"temperature_threshold": -99})
    assert res.status_code == 400
    assert "between -50°C and 150°C" in res.get_json()["error"]

    # Test invalid message rate limit (<= 0)
    res = client.put("/api/settings", json={"message_rate_limit": 0})
    assert res.status_code == 400
    assert "greater than 0" in res.get_json()["error"]

    # Test empty broker host
    res = client.put("/api/settings", json={"mqtt_broker_host": "   "})
    assert res.status_code == 400
    assert "cannot be empty" in res.get_json()["error"]
    print("PASS: All input validations correctly rejected bad payloads with 400.")

    print("\n========================================")
    print("ALL 8 SETTINGS TESTS PASSED SUCCESSFULLY!")
    print("========================================")

if __name__ == "__main__":
    test_settings_suite()
