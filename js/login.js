document.querySelector("form").addEventListener("submit", async function(e) {
    e.preventDefault();

    const email = document.querySelector("#email").value;
    const password = document.querySelector("#password").value;

    const result = await loginUser(email, password);

    if (result.status === "success") {
        alert("Login successful!");
        window.location.href = "../../user dashboard/pages/dashboard.html";
    } else {
        alert("Invalid login.");
    }
});