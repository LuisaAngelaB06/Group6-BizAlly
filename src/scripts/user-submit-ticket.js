document.addEventListener("DOMContentLoaded", function () {

    // Check if userDataManager is available
    const form = document.getElementById("ticketForm");

    if (!form) {
        console.error("ticketForm not found! Check your HTML <form> ID.");
        return;
    }

    form.addEventListener("submit", async function (e) {
        e.preventDefault(); // Stop the page from reloading

        // Grab the input elements
        const subjectInput = document.getElementById("ticketSubject");
        const descriptionInput = document.getElementById("ticketDescription");

        if (!subjectInput || !descriptionInput) {
            alert("Error: Cannot find input fields. Check the IDs in your HTML!");
            return;
        }

        const ticketData = {
            Service_Type_ID: 1, // 1 = Technical Support
            user_id: userData.user_id,
            Status_ID: 1, // 1 = Open
            Concern_Title: subjectInput.value,
            Description: descriptionInput.value,
            Priority: "Medium"
        };

        // Optional: Change button text so the user knows it's sending
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn ? submitBtn.innerHTML : "Submit";
        if (submitBtn) submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';

        try {
            const response = await fetch("http://127.0.0.1:5000/api/tickets", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(ticketData)
            });

            if (response.ok) {
                alert("✅ Ticket submitted successfully!");
                form.reset();
                // Redirect them to see their new ticket!
                window.location.href = "/user/my-tickets.html";
            } else {
                alert("❌ Server error submitting ticket.");
                if (submitBtn) submitBtn.innerHTML = originalBtnText;
            }

        } catch (error) {
            console.error("Network error:", error);
            alert("Network error. Please try again.");
            if (submitBtn) submitBtn.innerHTML = originalBtnText;
        }
    });
});