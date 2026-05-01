async function loadTickets() {
    try {
        const response = await fetch("http://127.0.0.1:5000/api/tickets");
        const tickets = await response.json();

        console.log("Tickets from backend:", tickets);

        const tbody = document.querySelector("#ticketsTbody");
        if (!tbody) return;

        tbody.innerHTML = "";

        tickets.forEach(ticket => {
            const row = document.createElement("tr");

            row.innerHTML = `
                <td>#${ticket.Ticket_ID}</td>
                <td>${ticket.Concern_Title}</td>
                <td>User ${ticket.user_id}</td>
                <td>${convertStatus(ticket.Status_ID)}</td>
                <td>${ticket.Priority}</td>
                <td>${formatDate(ticket.Date_Created)}</td>
            `;

            tbody.appendChild(row);
        });

    } catch (error) {
        console.error("Error loading tickets:", error);
    }
}

function convertStatus(statusId) {
    if (statusId == 1) return "Open";
    if (statusId == 2) return "In Progress";
    if (statusId == 3) return "Resolved";
    return "Open";
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toISOString().split("T")[0];
}

document.addEventListener("DOMContentLoaded", loadTickets);