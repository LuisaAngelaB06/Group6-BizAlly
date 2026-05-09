let API_BASE;

// Check if you are running the site locally on your laptop
if (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost") {
    console.log("Running in LOCAL mode");
    API_BASE = "http://127.0.0.1:5000/api";
} else {
    // Otherwise, assume it is live on Render
    console.log("Running in PRODUCTION mode");
    API_BASE = "https://group6-bizally.onrender.com/api";
}

// LOGIN REQUEST
async function loginUser(email, password) {
    const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password })
    });

    return await response.json();
}

// GET TICKETS
async function getTickets() {
    const response = await fetch(`${API_BASE}/auth/tickets`);
    return await response.json();
}

// SIGNUP REQUEST
async function registerUser(firstName, lastName, email, password) {
    const response = await fetch(`${API_BASE}/auth/signup`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ firstName, lastName, email, password })
    });

    return await response.json();
}