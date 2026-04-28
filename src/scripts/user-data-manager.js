const userDataStr = localStorage.getItem("userData");
const currentPath = window.location.pathname.toLowerCase();

(function () {

    // If not logged in
    if (!userDataStr) {
        if (
            !currentPath.endsWith("index.html") &&
            currentPath !== "/"
        ) {
            window.location.href = "/";
        }
        return;
    }

    const user = JSON.parse(userDataStr);

    const role = (
        user.User_Type ||
        user.role ||
        "client"
    ).toLowerCase();

    // CLIENT trying to access ADMIN pages
    if (currentPath.includes("/admin/") && role === "client") {
        window.location.href = "/user/index-user.html";
    }

    // ADMIN trying to access USER pages
    if (currentPath.includes("/user/") && role === "admin") {
        window.location.href = "/admin/index-admin.html";
    }

})();

// ... Now your "class UserDataManager" and all your original ~300 lines follow below ...

// --- 3. THE USER DATA MANAGER CLASS (Your Original ~200 Lines of Logic) ---
class UserDataManager {
    constructor() {
        this.userDataKey = 'userData';
        this.userProfileKey = 'userProfile';
    }

    // Get combined user data (from both userData and userProfile)
    getUserData() {
        const userData = JSON.parse(localStorage.getItem(this.userDataKey) || '{}');
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        
        return {
            ...userData,
            ...userProfile,
            fullName: `${userProfile.firstName || userData.firstName || ''} ${userProfile.lastName || userData.lastName || ''}`.trim() || userData.name || userData.Name || 'User'
        };
    }

    // Update user data
    updateUserData(updates) {
        const userData = JSON.parse(localStorage.getItem(this.userDataKey) || '{}');
        const updatedData = { ...userData, ...updates };
        localStorage.setItem(this.userDataKey, JSON.stringify(updatedData));
        this.dispatchUserDataChanged();
        return updatedData;
    }

    // Update user profile (Used by profile-settings.html)
    updateUserProfile(updates) {
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        const updatedProfile = { ...userProfile, ...updates };
        localStorage.setItem(this.userProfileKey, JSON.stringify(updatedProfile));
        this.dispatchUserDataChanged();
        return updatedProfile;
    }

    // Get profile picture URL
    getProfilePicture() {
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        return userProfile.photo || null;
    }

    // Get user initials
    getUserInitials() {
        const userData = this.getUserData();
        const firstName = userData.firstName || userData.name?.split(' ')[0] || userData.Name?.split(' ')[0] || 'U';
        const lastName = userData.lastName || userData.name?.split(' ')[1] || userData.Name?.split(' ')[1] || '';
        return (firstName.charAt(0) + (lastName.charAt(0) || '')).toUpperCase();
    }

    dispatchUserDataChanged() {
        const event = new CustomEvent('userDataChanged', { detail: this.getUserData() });
        document.dispatchEvent(event);
    }

    initializeUserDisplay() {
        this.updateHeaderAvatar();
        this.updateUserInfo();
        
        // Listen for internal changes
        document.addEventListener('userDataChanged', () => {
            this.updateHeaderAvatar();
            this.updateUserInfo();
        });
    }

    updateHeaderAvatar() {
        const headerAvatar = document.getElementById('userAvatar');
        if (!headerAvatar) return;

        const profilePicture = this.getProfilePicture();
        const initials = this.getUserInitials();
        
        if (profilePicture) {
            headerAvatar.innerHTML = `<img src="${profilePicture}" alt="Profile" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">`;
        } else {
            headerAvatar.innerHTML = '';
            headerAvatar.textContent = initials;
        }
    }

    updateUserInfo() {
        const user = this.getUserData();
        const userNameElement = document.getElementById('userName');
        const userEmailElement = document.getElementById('userEmail');
        
        if (userNameElement) userNameElement.textContent = user.fullName;
        if (userEmailElement) userEmailElement.textContent = user.Email || user.email || "No Email";
    }
}

// Create global instance
window.userDataManager = new UserDataManager();

// --- 4. UI & TAB SYNC (Runs on every page) ---
document.addEventListener("DOMContentLoaded", function () {
    // FIXED: Uses Global variable so Admin page doesn't crash here
    if (!userDataStr) return; return; 
    
    window.userDataManager.initializeUserDisplay();

    const userData = JSON.parse(userDataStr);

    // Dropdown Logic
    const accountBtn = document.getElementById("accountBtn");
    const accountMenu = document.getElementById("accountMenu");

    if (accountBtn && accountMenu) {
        accountBtn.style.cursor = 'pointer';
        accountBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            accountMenu.classList.toggle("show");
        });
        document.addEventListener("click", (e) => {
            if (!accountBtn.contains(e.target) && !accountMenu.contains(e.target)) {
                accountMenu.classList.remove("show");
            }
        });
    }

    // Role-Based Menu Routing
    const role = (userData.User_Type || userData.role || '').toLowerCase();
    const isStaff = (role !== 'client');
    document.querySelectorAll('#accountMenu a').forEach(link => {
        const href = link.getAttribute('href');
        if (href?.includes('profile-settings.html')) {
            link.href = isStaff ? '/admin/profile-settings.html' : '/user/profile-settings.html';
        }
    });

    // Global Logout Button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.clear();
            window.location.href = '/';
        });
    }

    // Trigger Notifications check
    checkNewAnnouncements(userData);
});

// --- 5. THE TAB SYNC ENGINE (Makes Admin follow logout) ---
window.addEventListener('storage', (event) => {
    if (event.key === 'userData') {
        if (!event.newValue) {
            // Logout detected in another tab!
            window.location.href = '/';
        } else {
            // Account change detected!
            window.location.reload();
        }
    }
});

async function checkNewAnnouncements(userData) {
    const userId = userData.User_ID || userData.id;
    const redDot = document.getElementById('navRedDot');
    if (!userId || !redDot) return;
    try {
        const response = await fetch(`http://127.0.0.1:5000/api/user/announcements/unread/${userId}`);
        const unread = await response.json();
        redDot.style.display = (Array.isArray(unread) && unread.length > 0) ? 'inline-block' : 'none';
    } catch (e) { console.warn("Announcement check failed"); }
}