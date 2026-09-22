let knownDeviceIds = new Set();

async function populateDeviceDropdown() {
  try {
    const response = await fetch("/api/devices");
    if (!response.ok) return;

    const devices = await response.json();
    const select = document.getElementById("device-select");
    if (!select) return;

    const currentSelection = select.value;

    devices.forEach((device) => {
      if (!knownDeviceIds.has(device.device_id)) {
        knownDeviceIds.add(device.device_id);
        const option = document.createElement("option");
        option.value = device.device_id;
        option.textContent = `${device.device_id} - ${device.device_name}`;
        select.appendChild(option);
      }
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
    displaySensorData(data);
  } catch (error) {
    console.error("Error loading sensor data:", error);
    const tableBody = document.getElementById("sensor-data-table-body");
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="loading-cell">
            Unable to load sensor data
          </td>
        </tr>
      `;
    }
  }
}

function displaySensorData(records) {
  const tableBody = document.getElementById("sensor-data-table-body");
  const countBadge = document.getElementById("sensor-records-count");

  if (countBadge) {
    countBadge.textContent = `${records.length} Records`;
  }

  if (!tableBody) return;

  tableBody.innerHTML = "";

  if (records.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="5" class="loading-cell">
          No sensor data found for this selection
        </td>
      </tr>
    `;
    return;
  }

  records.forEach((record) => {
    const row = document.createElement("tr");

    const tempText =
      record.temperature !== null && record.temperature !== undefined
        ? `${record.temperature} °C`
        : "--";

    const humText =
      record.humidity !== null && record.humidity !== undefined
        ? `${record.humidity} %`
        : "--";

    const motionBadge =
      record.motion === 1
        ? `<span class="badge suspicious">Detected</span>`
        : `<span class="badge normal">None</span>`;

    row.innerHTML = `
      <td>${record.timestamp || "--"}</td>
      <td><strong>${record.device_id}</strong></td>
      <td>${tempText}</td>
      <td>${humText}</td>
      <td>${motionBadge}</td>
    `;

    tableBody.appendChild(row);
  });
}

// Attach listener to dropdown
const selectElement = document.getElementById("device-select");
if (selectElement) {
  selectElement.addEventListener("change", () => {
    loadSensorDataRecords();
  });
}

// Initial loads
populateDeviceDropdown().then(() => {
  loadSensorDataRecords();
});

// Periodic refresh: re-fetch devices and sensor data every 5 seconds
setInterval(() => {
  populateDeviceDropdown();
  loadSensorDataRecords();
}, 5000);
