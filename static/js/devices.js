let allDevices = [];

async function loadDevices() {
  try {
    const response = await fetch("/api/devices");
    allDevices = await response.json();

    console.log("Devices:", allDevices);

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
    return (
      (device.device_id && device.device_id.toLowerCase().includes(query)) ||
      (device.device_name && device.device_name.toLowerCase().includes(query)) ||
      (device.device_type && device.device_type.toLowerCase().includes(query)) ||
      (device.ip_address && device.ip_address.toLowerCase().includes(query)) ||
      (device.status && device.status.toLowerCase().includes(query))
    );
  });

  displayDevices(filtered);
}

function displayDevices(devices) {
  const tableBody = document.getElementById("devices-table-body");
  if (!tableBody) return;

  tableBody.innerHTML = "";

  if (devices.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: #64748b; padding: 20px;">
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

    row.innerHTML = `
      <td>
        <strong>${device.device_id}</strong>
      </td>
      <td>${device.device_name}</td>
      <td>${device.device_type}</td>
      <td>${device.ip_address}</td>
      <td>
        <span class="badge ${badgeClass}">
          ${device.status}
        </span>
      </td>
      <td>${device.last_seen}</td>
    `;

    tableBody.appendChild(row);
  });
}

const searchInput = document.getElementById("device-search");
if (searchInput) {
  searchInput.addEventListener("input", filterAndDisplayDevices);
}

loadDevices();
setInterval(loadDevices, 5000);

