async function loadDevices() {

    try {

        const response = await fetch("/api/devices");

        const devices = await response.json();

        console.log("Devices received:", devices);

        updateDashboard(devices);

    } catch (error) {

        console.error("Error loading devices:", error);

    }
}


function updateDashboard(devices) {

    // Total devices
    const totalDevices = devices.length;

    // Online devices
    const onlineDevices = devices.filter(
        device => device.status === "Online"
    ).length;

    // Suspicious devices
    const suspiciousDevices = devices.filter(
        device => device.status === "Suspicious"
    ).length;


    // Update dashboard cards

    document.getElementById("total-devices").textContent =
        totalDevices;

    document.getElementById("online-devices").textContent =
        onlineDevices;

    document.getElementById("suspicious-devices").textContent =
        suspiciousDevices;


    // Display devices
    displayDevices(devices);
}


function displayDevices(devices) {

    const deviceList =
        document.getElementById("device-list");

    deviceList.innerHTML = "";


    devices.forEach(device => {

        const deviceElement =
            document.createElement("div");

        deviceElement.className = "device";


        let badgeClass = "normal";

        if (device.status === "Suspicious") {
            badgeClass = "suspicious";
        }


        deviceElement.innerHTML = `

            <div>

                <strong>
                    ${device.device_id}
                </strong>

                <p>
                    ${device.device_name}
                </p>

            </div>

            <span class="badge ${badgeClass}">
                ${device.status}
            </span>

        `;


        deviceList.appendChild(deviceElement);

    });
}


// Load devices when page opens

loadDevices();