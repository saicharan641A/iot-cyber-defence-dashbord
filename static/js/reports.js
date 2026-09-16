async function loadReports() {

    try {

        const response = await fetch("/api/reports");

        const events = await response.json();

        console.log("Reports:", events);

        updateReportSummary(events);

        displayReports(events);

    } catch (error) {

        console.error("Error loading reports:", error);

    }
}


function updateReportSummary(events) {

    const total = events.length;

    const suspicious = events.filter(
        event => event.prediction === "Suspicious"
    ).length;

    const normal = events.filter(
        event => event.prediction === "Normal"
    ).length;


    document.getElementById("total-events").textContent = total;

    document.getElementById("suspicious-events").textContent =
        suspicious;

    document.getElementById("normal-events").textContent =
        normal;
}


function displayReports(events) {

    const tableBody =
        document.getElementById("reports-table-body");

    tableBody.innerHTML = "";


    events.forEach(event => {

        const row = document.createElement("tr");


        let badgeClass = "normal";

        if (event.prediction === "Suspicious") {
            badgeClass = "suspicious";
        }


        row.innerHTML = `

            <td>
                <strong>${event.device_id}</strong>
            </td>

            <td>
                ${event.event_type}
            </td>

            <td>
                <span class="badge ${badgeClass}">
                    ${event.prediction}
                </span>
            </td>

            <td>
                ${(event.confidence * 100).toFixed(0)}%
            </td>

            <td>
                ${event.action}
            </td>

            <td>
                ${event.timestamp}
            </td>

        `;


        tableBody.appendChild(row);

    });
}


loadReports();