function getEventSeverity(event) {
    if (event.severity) {
        return event.severity;
    }
    const type = event.event_type || "";
    if (type.includes("Unknown") || type.includes("Excessive")) {
        return "High";
    }
    if (type.includes("Abnormal") || type.includes("Invalid")) {
        return "Medium";
    }
    if (event.prediction === "Suspicious") {
        return "Medium";
    }
    return "Low";
}

async function loadSecurityEvents() {
    try {
        const response = await fetch("/api/security-events");

        if (!response.ok) {
            throw new Error("Failed to load security events");
        }

        const events = await response.json();

        updateEventSummary(events);
        displaySecurityEvents(events);

    } catch (error) {
        console.error("Error loading security events:", error);

        const tableBody = document.getElementById("events-table-body");
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="loading-cell" style="color: #ef4444;">
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

    const high = events.filter(
        event => getEventSeverity(event) === "High"
    ).length;

    const medium = events.filter(
        event => getEventSeverity(event) === "Medium"
    ).length;

    const totalEl = document.getElementById("total-events");
    const highEl = document.getElementById("high-events");
    const mediumEl = document.getElementById("medium-events");

    if (totalEl) totalEl.textContent = total;
    if (highEl) highEl.textContent = high;
    if (mediumEl) mediumEl.textContent = medium;
}


/* Display events in table */
function displaySecurityEvents(events) {
    const tableBody = document.getElementById("events-table-body");
    if (!tableBody) return;

    tableBody.innerHTML = "";

    if (events.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="loading-cell">
                    No security events found
                </td>
            </tr>
        `;
        return;
    }

    events.forEach(event => {
        const row = document.createElement("tr");

        const severity = getEventSeverity(event);
        let badgeClass = "normal";
        if (severity === "High") {
            badgeClass = "severity-high";
        } else if (severity === "Medium") {
            badgeClass = "severity-medium";
        } else if (severity === "Low") {
            badgeClass = "severity-low";
        }

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
                    ${severity}
                </span>
            </td>
            <td>
                ${event.action}
            </td>
        `;

        tableBody.appendChild(row);
    });
}


/* Export security events as CSV */
async function exportSecurityEventsCSV() {
    try {
        const response = await fetch("/api/security-events/export");
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        const blob = await response.blob();
        const disposition = response.headers.get("Content-Disposition");
        let filename = "security_events.csv";
        if (disposition && disposition.includes("filename=")) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, "");
            }
        }
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (err) {
        console.error("Export error:", err);
        alert("Unable to download CSV: " + err.message);
    }
}


/* Load data when page opens and poll every 5s */
loadSecurityEvents();
setInterval(loadSecurityEvents, 5000);