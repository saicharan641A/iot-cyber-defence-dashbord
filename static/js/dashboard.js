let cachedDevices = [];
let cachedEvents = [];
let cachedSensorData = [];

async function loadDashboardData() {
  try {
    // 1. Fetch devices with configured sensors
    const devRes = await fetch("/api/devices");
    if (devRes.ok) {
      cachedDevices = await devRes.json();
      updateDeviceSummary(cachedDevices);
      displayDeviceStatusList(cachedDevices);
    }

    // 2. Fetch security events
    const evtRes = await fetch("/api/security-events");
    if (evtRes.ok) {
      cachedEvents = await evtRes.json();
      displayRecentSecurityEvents(cachedEvents);
    }

    // 3. Fetch sensor telemetry
    const senRes = await fetch("/api/sensor-data");
    if (senRes.ok) {
      cachedSensorData = await senRes.json();
    }

    // 4. Update dynamic live sensor cards
    displayLiveSensorActivity(cachedDevices, cachedSensorData);

  } catch (error) {
    console.error("Error loading dashboard data:", error);
  }
}

// 1. UPDATE SUMMARY CARDS
function updateDeviceSummary(devices) {
  const total = devices.length;
  const online = devices.filter((d) => d.status === "Online").length;
  const suspicious = devices.filter((d) => d.status === "Suspicious").length;
  const blocked = devices.filter((d) => d.status === "Blocked").length;

  const totalEl = document.getElementById("total-devices");
  const onlineEl = document.getElementById("online-devices");
  const suspiciousEl = document.getElementById("suspicious-devices");
  const blockedEl = document.getElementById("blocked-devices");

  if (totalEl) totalEl.textContent = total;
  if (onlineEl) onlineEl.textContent = online;
  if (suspiciousEl) suspiciousEl.textContent = suspicious;
  if (blockedEl) blockedEl.textContent = blocked;
}

// Helper: Sensor label formatting
function getSensorLabelWithIcon(sensor) {
  switch (sensor.toLowerCase()) {
    case "temperature":
      return "🌡️ Temp";
    case "humidity":
      return "💧 Hum";
    case "motion":
      return "📡 Motion";
    default:
      return sensor;
  }
}

// 2. DISPLAY DEVICE STATUS LIST
function displayDeviceStatusList(devices) {
  const deviceList = document.getElementById("device-list");
  if (!deviceList) return;

  deviceList.innerHTML = "";

  if (devices.length === 0) {
    deviceList.innerHTML = `<p style="color: #64748b; padding: 10px;">No registered devices</p>`;
    return;
  }

  devices.forEach((device) => {
    const item = document.createElement("div");
    item.className = "device-item";

    let badgeClass = "normal";
    if (device.status === "Suspicious") badgeClass = "suspicious";
    if (device.status === "Blocked") badgeClass = "blocked";

    let sensorsHtml = `<span style="color: #9ca3af; font-size: 12px;">None</span>`;
    if (device.sensors && device.sensors.length > 0) {
      sensorsHtml = device.sensors
        .map((s) => `<span class="sensor-tag">${getSensorLabelWithIcon(s)}</span>`)
        .join(" ");
    }

    item.innerHTML = `
      <div>
        <strong>${device.device_id}</strong>
        <p style="margin: 2px 0 4px 0; color: #4b5563;">${device.device_name}</p>
        <div style="display: flex; gap: 4px; flex-wrap: wrap;">
          ${sensorsHtml}
        </div>
      </div>
      <div style="text-align: right;">
        <span class="badge ${badgeClass}">${device.status}</span>
        <p style="font-size: 11px; color: #9ca3af; margin-top: 4px;">${device.last_seen || ""}</p>
      </div>
    `;

    deviceList.appendChild(item);
  });
}

// 3. DISPLAY RECENT SECURITY EVENTS (Rule-Based Severity)
function getEventSeverity(event) {
  if (event.severity) return event.severity;
  const type = event.event_type || "";
  if (type.includes("Unknown") || type.includes("Excessive")) return "High";
  if (type.includes("Abnormal") || type.includes("Invalid")) return "Medium";
  return "Low";
}

function displayRecentSecurityEvents(events) {
  const eventList = document.getElementById("security-events-list");
  if (!eventList) return;

  eventList.innerHTML = "";

  if (events.length === 0) {
    eventList.innerHTML = `
      <div class="event">
        <div>
          <strong>No Security Events</strong>
          <p>No anomalous activity detected.</p>
        </div>
        <span class="badge normal">Normal</span>
      </div>
    `;
    return;
  }

  const recent = events.slice(0, 5);

  recent.forEach((event) => {
    const item = document.createElement("div");
    item.className = "event";

    const severity = getEventSeverity(event);
    let badgeClass = "normal";
    if (severity === "High") badgeClass = "severity-high";
    else if (severity === "Medium") badgeClass = "severity-medium";
    else badgeClass = "severity-low";

    item.innerHTML = `
      <div>
        <strong>${event.device_id}</strong>
        <p>${event.event_type}</p>
        <small style="color: #9ca3af; font-size: 11px;">
          ${event.action} &bull; ${event.timestamp || ""}
        </small>
      </div>
      <span class="badge ${badgeClass}">${severity}</span>
    `;

    eventList.appendChild(item);
  });
}

// 4. DISPLAY LIVE SENSOR ACTIVITY (Dynamic per device)
function displayLiveSensorActivity(devices, sensorRecords) {
  const container = document.getElementById("live-sensors-container");
  if (!container) return;

  container.innerHTML = "";

  if (devices.length === 0) {
    container.innerHTML = `<p style="color: #64748b; padding: 15px;">No devices registered</p>`;
    return;
  }

  // Create a fast lookup for latest reading per (device_id, sensor_type)
  const latestReadings = {};
  sensorRecords.forEach((rec) => {
    const key = `${rec.device_id}_${(rec.sensor_type || "").toLowerCase()}`;
    if (!latestReadings[key]) {
      latestReadings[key] = rec;
    }
  });

  devices.forEach((device) => {
    const card = document.createElement("div");
    card.className = "live-device-card";

    let badgeClass = "normal";
    if (device.status === "Suspicious") badgeClass = "suspicious";
    if (device.status === "Blocked") badgeClass = "blocked";

    const configuredSensors = device.sensors || [];

    let readingsHtml = "";
    if (configuredSensors.length === 0) {
      readingsHtml = `<p style="color: #9ca3af; font-size: 13px;">No sensors configured</p>`;
    } else {
      readingsHtml = configuredSensors
        .map((sensor) => {
          const sLower = sensor.toLowerCase();
          const lookupKey = `${device.device_id}_${sLower}`;
          const latest = latestReadings[lookupKey];

          let valDisplay = "--";
          let label = sensor.charAt(0).toUpperCase() + sensor.slice(1);
          let icon = "⚙️";

          if (sLower === "temperature") {
            icon = "🌡️";
            label = "Temperature";
            valDisplay = latest ? `${Number(latest.sensor_value).toFixed(1)} °C` : "Awaiting data";
          } else if (sLower === "humidity") {
            icon = "💧";
            label = "Humidity";
            valDisplay = latest ? `${Number(latest.sensor_value).toFixed(1)} %` : "Awaiting data";
          } else if (sLower === "motion") {
            icon = "📡";
            label = "Motion";
            if (latest) {
              valDisplay = Number(latest.sensor_value) === 1
                ? `<span class="badge suspicious" style="font-size: 11px;">Detected</span>`
                : `<span class="badge normal" style="font-size: 11px;">None</span>`;
            } else {
              valDisplay = "Awaiting data";
            }
          } else {
            valDisplay = latest ? String(latest.sensor_value) : "Awaiting data";
          }

          const timeNote = latest && latest.timestamp ? `<small style="color: #9ca3af; font-size: 11px;"> (${latest.timestamp.split(" ")[1] || latest.timestamp})</small>` : "";

          return `
            <div class="live-sensor-row">
              <span class="live-sensor-label">${icon} ${label}</span>
              <span class="live-sensor-val">${valDisplay}${timeNote}</span>
            </div>
          `;
        })
        .join("");
    }

    card.innerHTML = `
      <div class="live-device-card-header">
        <div>
          <strong style="font-size: 15px; color: #111827;">${device.device_id}</strong>
          <p style="font-size: 12px; color: #64748b; margin-top: 2px;">${device.device_name}</p>
        </div>
        <span class="badge ${badgeClass}" style="font-size: 11px;">${device.status}</span>
      </div>
      <div class="live-device-readings">
        ${readingsHtml}
      </div>
    `;

    container.appendChild(card);
  });
}

// Initial run
loadDashboardData();
setInterval(loadDashboardData, 5000);
