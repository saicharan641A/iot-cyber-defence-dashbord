async function loadDevices() {

    try {

        const response = await fetch("/api/devices");

        const devices = await response.json();

        console.log("Devices:", devices);

        updateSummary(devices);

        displayDevices(devices);

    } catch (error) {

        console.error("Error loading devices:", error);

    }

}


function updateSummary(devices) {

    const total = devices.length;

    const online = devices.filter(
        device => device.status === "Online"
    ).length;

    const suspicious = devices.filter(
        device => device.status === "Suspicious"
    ).length;


    document.getElementById(
        "total-devices"
    ).textContent = total;


    document.getElementById(
        "online-devices"
    ).textContent = online;


    document.getElementById(
        "suspicious-devices"
    ).textContent = suspicious;

}


function displayDevices(devices) {

    const tableBody =
        document.getElementById(
            "devices-table-body"
        );

    tableBody.innerHTML = "";


    devices.forEach(device => {

        const row =
            document.createElement("tr");


        let badgeClass = "normal";

        if (device.status === "Suspicious") {
            badgeClass = "suspicious";
        }


        row.innerHTML = `

            <td>
                <strong>
                    ${device.device_id}
                </strong>
            </td>

            <td>
                ${device.device_name}
            </td>

            <td>
                ${device.device_type}
            </td>

            <td>
                ${device.ip_address}
            </td>

            <td>

                <span class="badge ${badgeClass}">
                    ${device.status}
                </span>

            </td>

            <td>
                ${device.last_seen}
            </td>

        `;


        tableBody.appendChild(row);

    });

}


loadDevices();