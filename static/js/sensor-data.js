let registeredDevices = [];
let deviceSensorsMap = {};

async function populateDeviceDropdown() {
  try {
    const response = await fetch("/api/devices");
    if (!response.ok) return;

    registeredDevices = await response.json();
    const select = document.getElementById("device-select");
    if (!select) return;

    const currentSelection = select.value;

    // Reset map
    deviceSensorsMap = {};
    registeredDevices.forEach((device) => {
      deviceSensorsMap[device.device_id] = device.sensors || [];
    });

    // Rebuild options while keeping current selection
    select.innerHTML = `<option value="all">All Devices</option>`;

    registeredDevices.forEach((device) => {
      const option = document.createElement("option");
      option.value = device.device_id;
      const sensorsText = (device.sensors || []).join(", ") || "No sensors";
      option.textContent = `${device.device_id} - ${device.device_name} (${sensorsText})`;
      select.appendChild(option);
    });

    if (currentSelection && select.querySelector(`option[value="${currentSelection}"]`)) {
      select.value = currentSelection;
    }
  } catch (error) {
    console.error("Error populating device dropdown:", error);
  }
}

async function loadSensorDataRecords() {
  const select = document.getElementById("device-select");
  const selectedDevice = select ? select.value : "all";

  let url = "/api/sensor-data";
  if (selectedDevice && selectedDevice !== "all") {
    url += `?device_id=${encodeURIComponent(selectedDevice)}`;
  }

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error("Failed to load sensor data");
    }

    const data = await response.json();
    displaySensorData(data, selectedDevice);
  } catch (error) {
    console.error("Error loading sensor data:", error);
    const tableBody = document.getElementById("sensor-data-table-body");
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="6" class="loading-cell" style="color: #ef4444;">
            Unable to load sensor data
          </td>
        </tr>
      `;
    }
  }
}

function formatSensorValue(sensorType, value) {
  if (value === null || value === undefined) return "--";

  const typeLower = sensorType.toLowerCase();
  if (typeLower === "temperature") {
    return `${Number(value).toFixed(1)} °C`;
  }
  if (typeLower === "humidity") {
    return `${Number(value).toFixed(1)} %`;
  }
  if (typeLower === "motion") {
    return Number(value) === 1
      ? `<span class="badge suspicious">Detected</span>`
      : `<span class="badge normal">None</span>`;
  }
  return String(value);
}

function getSensorIconLabel(sensorType) {
  const typeLower = sensorType.toLowerCase();
  if (typeLower === "temperature") return "🌡️ Temperature";
  if (typeLower === "humidity") return "💧 Humidity";
  if (typeLower === "motion") return "📡 Motion";
  return sensorType.charAt(0).toUpperCase() + sensorType.slice(1);
}

function displaySensorData(records, selectedDevice) {
  const tableHeaderRow = document.getElementById("sensor-table-header-row");
  const tableBody = document.getElementById("sensor-data-table-body");
  const countBadge = document.getElementById("sensor-records-count");

  if (countBadge) {
    countBadge.textContent = `${records.length} Records`;
  }

  if (!tableHeaderRow || !tableBody) return;

  tableBody.innerHTML = "";

  // CASE 1: "All Devices" is selected
  if (!selectedDevice || selectedDevice === "all") {
    tableHeaderRow.innerHTML = `
      <th>Timestamp</th>
      <th>Device ID</th>
      <th>Sensor Type</th>
      <th>Sensor Value</th>
    `;

    if (records.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="4" class="loading-cell" style="text-align: center; color: #64748b; padding: 25px;">
            No sensor telemetry recorded yet
          </td>
        </tr>
      `;
      return;
    }

    records.forEach((record) => {
      const row = document.createElement("tr");
      const sType = record.sensor_type || "unknown";
      const valHtml = formatSensorValue(sType, record.sensor_value);

      row.innerHTML = `
        <td>${record.timestamp || "--"}</td>
        <td><strong>${record.device_id}</strong></td>
        <td><span class="sensor-tag">${getSensorIconLabel(sType)}</span></td>
        <td>${valHtml}</td>
      `;
      tableBody.appendChild(row);
    });
    return;
  }

  // CASE 2: Specific device is selected
  // Determine sensors for this device
  let deviceSensors = deviceSensorsMap[selectedDevice] || [];

  // If no sensors are configured, inspect records to find any sensor types present
  if (deviceSensors.length === 0) {
    const presentTypes = new Set(records.map((r) => r.sensor_type).filter(Boolean));
    deviceSensors = Array.from(presentTypes);
  }

  // If still empty (device has no configured sensors and no records)
  if (deviceSensors.length === 0) {
    tableHeaderRow.innerHTML = `
      <th>Timestamp</th>
      <th>Device ID</th>
      <th>Sensor Value</th>
    `;
    tableBody.innerHTML = `
      <tr>
        <td colspan="3" class="loading-cell" style="text-align: center; color: #64748b; padding: 25px;">
          Device "${selectedDevice}" has no configured sensors
        </td>
      </tr>
    `;
    return;
  }

  // Render dynamic header with ONLY the configured sensors for this device
  let headerHtml = `<th>Timestamp</th><th>Device ID</th>`;
  deviceSensors.forEach((s) => {
    headerHtml += `<th>${getSensorIconLabel(s)}</th>`;
  });
  tableHeaderRow.innerHTML = headerHtml;

  const totalCols = 2 + deviceSensors.length;

  if (records.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="${totalCols}" class="loading-cell" style="text-align: center; color: #64748b; padding: 25px;">
          No sensor telemetry found for ${selectedDevice}
        </td>
      </tr>
    `;
    return;
  }

  // Group records by timestamp so multi-sensor readings for same packet show on one row
  const groupedByTime = new Map();
  records.forEach((rec) => {
    const timeKey = rec.timestamp || "unknown";
    if (!groupedByTime.has(timeKey)) {
      groupedByTime.set(timeKey, {
        timestamp: rec.timestamp,
        device_id: rec.device_id,
        readings: {}
      });
    }
    const group = groupedByTime.get(timeKey);
    if (rec.sensor_type) {
      group.readings[rec.sensor_type.toLowerCase()] = rec.sensor_value;
    }
  });

  groupedByTime.forEach((group) => {
    const row = document.createElement("tr");

    let cellsHtml = `
      <td>${group.timestamp || "--"}</td>
      <td><strong>${group.device_id}</strong></td>
    `;

    deviceSensors.forEach((sensorType) => {
      const val = group.readings[sensorType.toLowerCase()];
      const valFormatted = formatSensorValue(sensorType, val);
      cellsHtml += `<td>${valFormatted}</td>`;
    });

    row.innerHTML = cellsHtml;
    tableBody.appendChild(row);
  });
}

async function exportSensorDataCSV() {
  const select = document.getElementById("device-select");
  const selectedDevice = select ? select.value : "all";
  let url = "/api/sensor-data/export";
  if (selectedDevice && selectedDevice !== "all") {
    url += `?device_id=${encodeURIComponent(selectedDevice)}`;
  }

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}: ${response.statusText}`);
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition");
    let filename = "sensor_data.csv";
    if (disposition && disposition.includes("filename=")) {
      const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
      if (matches != null && matches[1]) {
        filename = matches[1].replace(/['"]/g, "");
      }
    }
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(blobUrl);
    document.body.removeChild(a);
  } catch (err) {
    console.error("Export error:", err);
    alert("Unable to download CSV: " + err.message);
  }
}

// Attach listener to dropdown
const selectElement = document.getElementById("device-select");
if (selectElement) {
  selectElement.addEventListener("change", () => {
    loadSensorDataRecords();
  });
}

// Initial load
populateDeviceDropdown().then(() => {
  loadSensorDataRecords();
});

// Periodic refresh every 5s
setInterval(() => {
  populateDeviceDropdown();
  loadSensorDataRecords();
}, 5000);
