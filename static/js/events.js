async function loadSecurityEvents() {
    try {
        const response = await fetch("/api/security-events");

        if (!response.ok) {
            throw new Error("Failed to load security events");
        }

        const events = await response.json();

        console.log("Security Events:", events);

        updateEventSummary(events);
        displaySecurityEvents(events);

    } catch (error) {
        console.error("Error loading security events:", error);

        const tableBody = document.getElementById("events-table-body");
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="loading-cell">
                        Unable to load security events
                    </td>
                </tr>
            `;
        }
    }
}


/* Update summary cards */
function updateEventSummary(events) {
    const total = events.length;

    const suspicious = events.filter(
        event => event.prediction === "Suspicious"
    ).length;

    const normal = events.filter(
        event => event.prediction === "Normal"
    ).length;

    const totalEl = document.getElementById("total-events");
    const suspiciousEl = document.getElementById("suspicious-events");
    const normalEl = document.getElementById("normal-events");

    if (totalEl) totalEl.textContent = total;
    if (suspiciousEl) suspiciousEl.textContent = suspicious;
    if (normalEl) normalEl.textContent = normal;
}


/* Display events in table */
function displaySecurityEvents(events) {
    const tableBody = document.getElementById("events-table-body");
    if (!tableBody) return;

    tableBody.innerHTML = "";

    if (events.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="loading-cell">
                    No security events found
                </td>
            </tr>
        `;
        return;
    }

    events.forEach(event => {
        const row = document.createElement("tr");

        let badgeClass = "normal";
        if (event.prediction === "Suspicious") {
            badgeClass = "suspicious";
        }

        const confidence = (event.confidence * 100).toFixed(0);

        row.innerHTML = `
            <td>
                ${event.timestamp || "--"}
            </td>
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
                ${confidence}%
            </td>
            <td>
                ${event.action}
            </td>
        `;

        tableBody.appendChild(row);
    });
}


/* Load data when page opens and poll every 5s */
loadSecurityEvents();
setInterval(loadSecurityEvents, 5000);