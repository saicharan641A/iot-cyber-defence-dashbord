/**
 * Settings Page JavaScript
 * Handles dynamic configuration for MQTT, Security Rules, and real-time status
 */

let alertTimeout = null;

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  // Poll MQTT connection status every 5 seconds
  setInterval(pollMQTTStatus, 5000);
});

/**
 * Fetch and display current settings from backend
 */
async function loadSettings() {
  try {
    const response = await fetch("/api/settings");
    if (!response.ok) {
      throw new Error(`Failed to fetch settings: ${response.statusText}`);
    }

    const settings = await response.json();

    // Populate MQTT settings
    if (settings.mqtt_broker_host !== undefined) {
      document.getElementById("mqtt-host").value = settings.mqtt_broker_host;
    }
    if (settings.mqtt_broker_port !== undefined) {
      document.getElementById("mqtt-port").value = settings.mqtt_broker_port;
    }
    if (settings.mqtt_topic !== undefined) {
      document.getElementById("mqtt-topic").value = settings.mqtt_topic;
    }

    // Populate Security Rules settings
    if (settings.temperature_threshold !== undefined) {
      document.getElementById("temp-threshold").value = settings.temperature_threshold;
    }
    if (settings.message_rate_limit !== undefined) {
      document.getElementById("rate-limit").value = settings.message_rate_limit;
    }
    if (settings.message_rate_window !== undefined) {
      document.getElementById("rate-window").value = settings.message_rate_window;
    }
    if (settings.device_block_duration !== undefined) {
      document.getElementById("block-duration").value = settings.device_block_duration;
    }

    // Update real-time MQTT status indicator
    updateMQTTStatusUI(settings.mqtt_connected);
  } catch (error) {
    console.error("Error loading settings:", error);
    showAlert("Failed to load settings from server. Check server connection.", "error");
  }
}

/**
 * Poll real-time MQTT broker status
 */
async function pollMQTTStatus() {
  try {
    const response = await fetch("/api/mqtt-status");
    if (response.ok) {
      const data = await response.json();
      updateMQTTStatusUI(data.connected);
    }
  } catch (error) {
    console.warn("MQTT status poll error:", error);
    updateMQTTStatusUI(false);
  }
}

/**
 * Update the visual MQTT connection badge
 */
function updateMQTTStatusUI(isConnected) {
  const badge = document.getElementById("mqtt-status-badge");
  const text = document.getElementById("mqtt-status-text");

  if (!badge || !text) return;

  if (isConnected) {
    badge.className = "connection-badge connected";
    text.textContent = "Connected";
  } else {
    badge.className = "connection-badge disconnected";
    text.textContent = "Disconnected";
  }
}

/**
 * Handle saving MQTT configuration
 */
async function handleSaveMQTT(event) {
  event.preventDefault();

  const hostInput = document.getElementById("mqtt-host");
  const portInput = document.getElementById("mqtt-port");
  const topicInput = document.getElementById("mqtt-topic");
  const submitBtn = document.getElementById("save-mqtt-btn");

  const host = hostInput.value.trim();
  const port = parseInt(portInput.value, 10);
  const topic = topicInput.value.trim();

  // Client-side validation
  if (!host) {
    showAlert("MQTT Broker Host cannot be empty.", "error");
    hostInput.focus();
    return;
  }

  if (isNaN(port) || port < 1 || port > 65535) {
    showAlert("MQTT Broker Port must be a number between 1 and 65535.", "error");
    portInput.focus();
    return;
  }

  if (!topic) {
    showAlert("MQTT Topic cannot be empty.", "error");
    topicInput.focus();
    return;
  }

  const payload = {
    mqtt_broker_host: host,
    mqtt_broker_port: port,
    mqtt_topic: topic
  };

  submitBtn.disabled = true;
  submitBtn.textContent = "Saving...";

  try {
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (response.ok) {
      showAlert("MQTT settings saved successfully! Reconnecting broker...", "success");
      if (result.settings && result.settings.mqtt_connected !== undefined) {
        updateMQTTStatusUI(result.settings.mqtt_connected);
      }
      // Poll shortly to reflect reconnection status
      setTimeout(pollMQTTStatus, 1500);
    } else {
      showAlert(result.error || "Failed to save MQTT settings.", "error");
    }
  } catch (error) {
    console.error("Error saving MQTT settings:", error);
    showAlert("Network error while saving MQTT settings.", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Save MQTT Settings";
  }
}

/**
 * Handle saving Security Rules configuration
 */
async function handleSaveSecurityRules(event) {
  event.preventDefault();

  const tempInput = document.getElementById("temp-threshold");
  const rateLimitInput = document.getElementById("rate-limit");
  const rateWindowInput = document.getElementById("rate-window");
  const blockDurationInput = document.getElementById("block-duration");
  const submitBtn = document.getElementById("save-rules-btn");

  const tempThreshold = parseFloat(tempInput.value);
  const rateLimit = parseInt(rateLimitInput.value, 10);
  const rateWindow = parseInt(rateWindowInput.value, 10);
  const blockDuration = parseInt(blockDurationInput.value, 10);

  // Client-side validation
  if (isNaN(tempThreshold) || tempThreshold < -50 || tempThreshold > 150) {
    showAlert("Abnormal temperature threshold must be a number between -50°C and 150°C.", "error");
    tempInput.focus();
    return;
  }

  if (isNaN(rateLimit) || rateLimit <= 0) {
    showAlert("Maximum MQTT messages must be an integer greater than 0.", "error");
    rateLimitInput.focus();
    return;
  }

  if (isNaN(rateWindow) || rateWindow <= 0) {
    showAlert("Rate time window must be an integer greater than 0 seconds.", "error");
    rateWindowInput.focus();
    return;
  }

  if (isNaN(blockDuration) || blockDuration <= 0) {
    showAlert("Device block duration must be an integer greater than 0 seconds.", "error");
    blockDurationInput.focus();
    return;
  }

  const payload = {
    temperature_threshold: tempThreshold,
    message_rate_limit: rateLimit,
    message_rate_window: rateWindow,
    device_block_duration: blockDuration
  };

  submitBtn.disabled = true;
  submitBtn.textContent = "Saving...";

  try {
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (response.ok) {
      showAlert("Security rules updated successfully! Changes are active immediately.", "success");
    } else {
      showAlert(result.error || "Failed to update security rules.", "error");
    }
  } catch (error) {
    console.error("Error saving security rules:", error);
    showAlert("Network error while saving security rules.", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Save Security Rules";
  }
}

/**
 * Display top alert banner for user feedback
 */
function showAlert(message, type = "success") {
  const alertBox = document.getElementById("settings-alert");
  if (!alertBox) return;

  if (alertTimeout) {
    clearTimeout(alertTimeout);
  }

  alertBox.className = `settings-alert ${type}`;
  alertBox.innerHTML = `
    <span>${message}</span>
    <button class="alert-close-btn" onclick="this.parentElement.style.display='none'">&times;</button>
  `;
  alertBox.style.display = "flex";

  alertTimeout = setTimeout(() => {
    alertBox.style.display = "none";
  }, 5000);
}
