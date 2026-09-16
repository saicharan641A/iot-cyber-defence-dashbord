async function loadDashboardData() {

    try {

        // LOAD DEVICES

        const deviceResponse = await fetch("/api/devices");

        if (!deviceResponse.ok) {
            throw new Error("Failed to load devices");
        }

        const devices = await deviceResponse.json();

        console.log("Devices:", devices);

        updateDeviceSummary(devices);
        displayDevices(devices);


        // LOAD SECURITY EVENTS

        const eventResponse = await fetch("/api/security-events");

        if (!eventResponse.ok) {
            throw new Error("Failed to load security events");
        }

        const events = await eventResponse.json();

        console.log("Security Events:", events);

        displayRecentEvents(events);


    } catch (error) {

        console.error("Error loading dashboard data:", error);

    }
}

// UPDATE DEVICE SUMMARY CARDS

function updateDeviceSummary(devices) {

    const total = devices.length;

    const online = devices.filter(
        device => device.status === "Online"
    ).length;

    const suspicious = devices.filter(
        device => device.status === "Suspicious"
    ).length;


    const totalDevices =
        document.getElementById("total-devices");

    const onlineDevices =
        document.getElementById("online-devices");

    const suspiciousDevices =
        document.getElementById("suspicious-devices");


    if (totalDevices) {
        totalDevices.textContent = total;
    }

    if (onlineDevices) {
        onlineDevices.textContent = online;
    }

    if (suspiciousDevices) {
        suspiciousDevices.textContent = suspicious;
    }

}


// DISPLAY DEVICES

function displayDevices(devices) {

    const deviceList =
        document.getElementById("device-list");


    // If dashboard does not have a device list,
    // simply stop here.

    if (!deviceList) {
        return;
    }


    deviceList.innerHTML = "";


    devices.forEach(device => {

        const item =
            document.createElement("div");


        item.className = "device-item";


        const badgeClass =
            device.status === "Suspicious"
                ? "suspicious"
                : "normal";


        item.innerHTML = `

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


        deviceList.appendChild(item);

    });

}

// DISPLAY RECENT SECURITY EVENTS

function displayRecentEvents(events) {

    const eventList =
        document.getElementById(
            "security-events-list"
        );


    // If the container does not exist,
    // stop here.

    if (!eventList) {
        return;
    }


    // Clear loading message

    eventList.innerHTML = "";


    // No events

    if (events.length === 0) {

        eventList.innerHTML = `

            <div class="event">

                <div>
                    <strong>No security events</strong>
                    <p>No events have been recorded.</p>
                </div>

                <span class="badge normal">
                    Normal
                </span>

            </div>

        `;

        return;
    }


    // Show only the latest 5 events

    const recentEvents =
        events.slice(0, 5);


    recentEvents.forEach(event => {

        const item =
            document.createElement("div");


        item.className = "event";


        // Suspicious or Normal

        const badgeClass =
            event.prediction === "Suspicious"
                ? "suspicious"
                : "normal";


        // Badge text

        const badgeText =
            event.prediction === "Suspicious"
                ? "Alert"
                : "Normal";


        item.innerHTML = `

            <div>

                <strong>
                    ${event.device_id}
                </strong>

                <p>
                    ${event.event_type}
                </p>

            </div>


            <span class="badge ${badgeClass}">
                ${badgeText}
            </span>

        `;


        eventList.appendChild(item);

    });

}


// START DASHBOARD
loadDashboardData();