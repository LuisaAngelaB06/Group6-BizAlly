console.log("login.js loaded");

const form = document.getElementById("modalLoginForm");

if (form) {
    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        // Prevent the HTML's inline simulated script from running
        e.stopImmediatePropagation();

        const email = document.getElementById("modalEmail").value;
        const password = document.getElementById("modalPassword").value;
        const loginBtn = document.getElementById('modalLoginBtn');
        const loadingText = document.getElementById('modalLoadingText');
        const loadingOverlay = document.getElementById('modalLoadingOverlay');

        // Show loading UI
        if (loadingOverlay) loadingOverlay.style.display = 'flex';
        if (loadingText) loadingText.textContent = 'Authenticating...';
        loginBtn.disabled = true;

        try {
            const result = await loginUser(email, password);

            if (result.status === "success") {
                // Save real database user data
                localStorage.setItem("userData", JSON.stringify(result.user));
                console.log("Login success:", result.user);

                // REDIRECT BASED ON ROLE
                if (result.user.User_Type === 'admin' || result.user.User_Type === 'technician') {
                    window.location.href = "/admin/dashboard";
                } else {
                    window.location.href = "/user/dashboard";
                }

            } else {
                if (loadingOverlay) loadingOverlay.style.display = 'none';
                loginBtn.disabled = false;
                alert("Invalid email or password");
            }

        } catch (error) {
            if (loadingOverlay) loadingOverlay.style.display = 'none';
            loginBtn.disabled = false;
            console.error("Login error:", error);
            alert("Server connection failed. Please try again.");
        }
    });
}