const API_BASE = "https://group6-bizally.onrender.com/api";

// LOGIN REQUEST
async function loginUser(email, password) {
    const response = await fetch(`${API_BASE}/login`, {
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
    const response = await fetch(`${API_BASE}/tickets`);
    return await response.json();
}

// SIGNUP REQUEST
async function registerUser(firstName, lastName, email, password) {
    const response = await fetch(`${API_BASE}/signup`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ firstName, lastName, email, password })
    });

    return await response.json();
}