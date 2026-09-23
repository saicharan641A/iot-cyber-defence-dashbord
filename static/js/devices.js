let allDevices = [];
let editingDeviceId = null;

async function loadDevices() {
  try {
    const response = await fetch("/api/devices");
    if (!response.ok) {
      throw new Error("Failed to load devices");
    }
    allDevices = await response.json();

    updateSummary(allDevices);
    filterAndDisplayDevices();
  } catch (error) {
    console.error("Error loading devices:", error);
  }
}

function updateSummary(devices) {
  const total = devices.length;
  const online = devices.filter((device) => device.status === "Online").length;
  const suspicious = devices.filter(
    (device) => device.status === "Suspicious"
  ).length;
  const blocked = devices.filter(
    (device) => device.status === "Blocked"
  ).length;

  const totalEl = document.getElementById("total-devices");
  const onlineEl = document.getElementById("online-devices");
  const suspiciousEl = document.getElementById("suspicious-devices");
  const blockedEl = document.getElementById("blocked-devices");

  if (totalEl) totalEl.textContent = total;
  if (onlineEl) onlineEl.textContent = online;
  if (suspiciousEl) suspiciousEl.textContent = suspicious;
  if (blockedEl) blockedEl.textContent = blocked;
}

function filterAndDisplayDevices() {
  const searchInput = document.getElementById("device-search");
  const query = searchInput ? searchInput.value.toLowerCase().trim() : "";

  const filtered = allDevices.filter((device) => {
    if (!query) return true;
    const sensorsStr = (device.sensors || []).join(" ").toLowerCase();
    return (
      (device.device_id && device.device_id.toLowerCase().includes(query)) ||
      (device.device_name && device.device_name.toLowerCase().includes(query)) ||
      (device.device_type && device.device_type.toLowerCase().includes(query)) ||
      (device.ip_address && device.ip_address.toLowerCase().includes(query)) ||
      (device.status && device.status.toLowerCase().includes(query)) ||
      sensorsStr.includes(query)
    );
  });

  displayDevices(filtered);
}

function getSensorIcon(sensor) {
  switch (sensor.toLowerCase()) {
    case "temperature":
      return "🌡️ Temp";
    case "humidity":
      return "💧 Humidity";
    case "motion":
      return "📡 Motion";
    default:
      return `⚙️ ${sensor}`;
  }
}

function displayDevices(devices) {
  const tableBody = document.getElementById("devices-table-body");
  if (!tableBody) return;

  tableBody.innerHTML = "";

  if (devices.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: #64748b; padding: 25px;">
          No devices found
        </td>
      </tr>
    `;
    return;
  }

  devices.forEach((device) => {
    const row = document.createElement("tr");

    let badgeClass = "normal";
    if (device.status === "Suspicious") {
      badgeClass = "suspicious";
    }
    if (device.status === "Blocked") {
      badgeClass = "blocked";
    }

    // Render sensor tags
    let sensorsHtml = `<span style="color: #9ca3af; font-size: 13px;">None</span>`;
    if (device.sensors && device.sensors.length > 0) {
      sensorsHtml = device.sensors
        .map(
          (s) => `<span class="sensor-tag">${getSensorIcon(s)}</span>`
        )
        .join(" ");
    }

    row.innerHTML = `
      <td>
        <strong>${device.device_id}</strong>
      </td>
      <td>${device.device_name}</td>
      <td>${device.device_type || "ESP32"}</td>
      <td><code>${device.ip_address || "--"}</code></td>
      <td>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
          ${sensorsHtml}
        </div>
      </td>
      <td>
        <span class="badge ${badgeClass}">
          ${device.status}
        </span>
      </td>
      <td>${device.last_seen || "--"}</td>
      <td>
        <div style="display: flex; gap: 8px;">
          <button class="btn-action-edit" onclick="openEditDeviceModal('${device.device_id}')">
            Edit
          </button>
          <button class="btn-action-delete" onclick="handleDeleteDevice('${device.device_id}')">
            Remove
          </button>
        </div>
      </td>
    `;

    tableBody.appendChild(row);
  });
}

// Modal handlers
function openAddDeviceModal() {
  editingDeviceId = null;
  document.getElementById("modal-title").textContent = "Add New Device";
  document.getElementById("modal-device-id").value = "";
  document.getElementById("modal-device-id").disabled = false;
  document.getElementById("modal-device-name").value = "";
  document.getElementById("modal-device-type").value = "ESP32";
  document.getElementById("modal-device-ip").value = "";

  document.querySelectorAll('input[name="sensors"]').forEach((cb) => {
    cb.checked = false;
  });

  const errEl = document.getElementById("modal-error-message");
  if (errEl) {
    errEl.style.display = "none";
    errEl.textContent = "";
  }

  document.getElementById("device-modal").style.display = "flex";
}

function openEditDeviceModal(deviceId) {
  const device = allDevices.find((d) => d.device_id === deviceId);
  if (!device) return;

  editingDeviceId = deviceId;
  document.getElementById("modal-title").textContent = `Edit Device: ${deviceId}`;
  const idInput = document.getElementById("modal-device-id");
  idInput.value = device.device_id;
  idInput.disabled = true; // Device ID cannot be edited

  document.getElementById("modal-device-name").value = device.device_name;
  document.getElementById("modal-device-type").value = device.device_type || "ESP32";
  document.getElementById("modal-device-ip").value = device.ip_address || "";

  const activeSensors = device.sensors || [];
  document.querySelectorAll('input[name="sensors"]').forEach((cb) => {
    cb.checked = activeSensors.includes(cb.value);
  });

  const errEl = document.getElementById("modal-error-message");
  if (errEl) {
    errEl.style.display = "none";
    errEl.textContent = "";
  }

  document.getElementById("device-modal").style.display = "flex";
}

function closeDeviceModal() {
  document.getElementById("device-modal").style.display = "none";
  editingDeviceId = null;
}

async function handleDeviceFormSubmit(event) {
  event.preventDefault();

  const deviceId = document.getElementById("modal-device-id").value.trim();
  const deviceName = document.getElementById("modal-device-name").value.trim();
  const deviceType = document.getElementById("modal-device-type").value.trim();
  const ipAddress = document.getElementById("modal-device-ip").value.trim();

  const selectedSensors = [];
  document.querySelectorAll('input[name="sensors"]:checked').forEach((cb) => {
    selectedSensors.push(cb.value);
  });

  const errorEl = document.getElementById("modal-error-message");

  try {
    let response;
    if (editingDeviceId) {
      // Edit device
      response = await fetch(`/api/devices/${encodeURIComponent(editingDeviceId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          device_name: deviceName,
          device_type: deviceType,
          ip_address: ipAddress,
          sensors: selectedSensors
        })
      });
    } else {
      // Add new device
      response = await fetch("/api/devices", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          device_id: deviceId,
          device_name: deviceName,
          device_type: deviceType,
          ip_address: ipAddress,
          sensors: selectedSensors
        })
      });
    }

    const data = await response.json();

    if (!response.ok) {
      if (errorEl) {
        errorEl.textContent = data.error || "An error occurred";
        errorEl.style.display = "block";
      }
      return;
    }

    closeDeviceModal();
    await loadDevices();
  } catch (error) {
    console.error("Error saving device:", error);
    if (errorEl) {
      errorEl.textContent = "Network error. Please try again.";
      errorEl.style.display = "block";
    }
  }
}

async function handleDeleteDevice(deviceId) {
  const confirmed = confirm(
    `Are you sure you want to remove device "${deviceId}"?\nThis will also remove its sensor configurations and telemetry history.`
  );
  if (!confirmed) return;

  try {
    const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}`, {
      method: "DELETE"
    });

    if (!response.ok) {
      const data = await response.json();
      alert(`Error deleting device: ${data.error || "Unknown error"}`);
      return;
    }

    await loadDevices();
  } catch (error) {
    console.error("Error deleting device:", error);
    alert("Network error while trying to delete device.");
  }
}

// Attach search listener
const searchInput = document.getElementById("device-search");
if (searchInput) {
  searchInput.addEventListener("input", filterAndDisplayDevices);
}

// Initial load
loadDevices();
setInterval(loadDevices, 5000);
