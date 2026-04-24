window.addEventListener("DOMContentLoaded", async () => {
    const tickets = await getTickets();

    const tableBody = document.querySelector("#ticketTableBody");

    tableBody.innerHTML = "";

    tickets.forEach(ticket => {
        const row = `
            <tr>
                <td>${ticket.Ticket_ID}</td>
                <td>${ticket.Concern_Title}</td>
                <td>${ticket.Priority}</td>
                <td>${ticket.Status_ID}</td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
});