/**
 * AlliTrack Admin Data Manager
 * FIXED: Added Security Bouncer and Multi-Tab Logout Sync
 */

// --- 1. GLOBAL SCOPE VARIABLES ---
const userDataStr = localStorage.getItem("userData");
const currentPath = window.location.pathname.toLowerCase();

// --- 2. THE BOUNCER (Ensures Admin side is locked) ---
(function() {
    const isPublic = currentPath.endsWith('index.html') || currentPath === '/' || currentPath.includes('landing');

    if (userDataStr && userDataStr !== "undefined") {
        const user = JSON.parse(userDataStr);
        const role = (user.User_Type || user.role || 'client').toLowerCase();

        // Specific folder check for "admin page" and "user page"
        const isTryingAdmin = currentPath.includes('admin');
        const isTryingUser = currentPath.includes('user');

        // BLOCK CLIENTS: Kick them out of the Admin section
        if (isTryingAdmin && role === 'client') {
            window.location.href = '/user/index-user.html';
            return;
        }
        // BLOCK STAFF: Kick them out of the User section
        if (isTryingUser && role !== 'client') {
            window.location.href = '/admin/index-admin.html';
            return;
        }
    } else if (!isPublic) {
        // FORCE LOGIN: If no session exists
        window.location.href = '/';
    }
})();

// --- 3. ORIGINAL USER DATA MANAGER CLASS (Unchanged) ---
class UserDataManager {
    constructor() {
        this.userDataKey = 'userData';
        this.userProfileKey = 'userProfile';
    }

    getUserData() {
        const userData = JSON.parse(localStorage.getItem(this.userDataKey) || '{}');
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        
        return {
            ...userData,
            ...userProfile,
            fullName: `${userProfile.firstName || userData.firstName || ''} ${userProfile.lastName || userData.lastName || ''}`.trim() || userData.name || 'User'
        };
    }

    updateUserData(updates) {
        const userData = JSON.parse(localStorage.getItem(this.userDataKey) || '{}');
        const updatedData = { ...userData, ...updates };
        localStorage.setItem(this.userDataKey, JSON.stringify(updatedData));
        this.dispatchUserDataChanged();
        return updatedData;
    }

    updateUserProfile(updates) {
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        const updatedProfile = { ...userProfile, ...updates };
        localStorage.setItem(this.userProfileKey, JSON.stringify(updatedProfile));
        this.dispatchUserDataChanged();
        return updatedProfile;
    }

    getProfilePicture() {
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        return userProfile.photo || null;
    }

    getUserInitials() {
        const userData = this.getUserData();
        const firstName = userData.firstName || userData.name?.split(' ')[0] || 'U';
        const lastName = userData.lastName || userData.name?.split(' ')[1] || '';
        return (firstName.charAt(0) + (lastName.charAt(0) || '')).toUpperCase();
    }

    dispatchUserDataChanged() {
        const event = new CustomEvent('userDataChanged', { detail: this.getUserData() });
        document.dispatchEvent(event);
    }

    initializeUserDisplay() {
        this.updateHeaderAvatar();
        this.updateUserInfo();
        
        window.addEventListener('storage', (event) => {
            if (event.key === this.userDataKey || event.key === this.userProfileKey) {
                this.updateHeaderAvatar();
                this.updateUserInfo();
            }
        });
        
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
            if (headerAvatar.querySelector('img')) {
                headerAvatar.querySelector('img').src = profilePicture;
            } else {
                headerAvatar.innerHTML = `<img src="${profilePicture}" alt="Profile" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
            }
        } else {
            headerAvatar.innerHTML = '';
            headerAvatar.textContent = initials;
        }
    }

    updateUserInfo() {
        const userData = this.getUserData();
        const userNameElement = document.getElementById('userName');
        if (userNameElement) userNameElement.textContent = userData.fullName;
        const userEmailElement = document.getElementById('userEmail');
        if (userEmailElement && userData.email) userEmailElement.textContent = userData.email;
    }
}

window.userDataManager = new UserDataManager();

// --- 4. YOUR ORIGINAL OVERRIDE LOGIC (Unchanged) ---
window.userDataManager.initializeUserDisplay = function() {
    const userDataStr = localStorage.getItem("userData");
    if (userDataStr) {
        const realUser = JSON.parse(userDataStr);
        const nameBox = document.getElementById("userNameDisplay") || document.getElementById("userName");
        const emailBox = document.getElementById("userEmailDisplay") || document.getElementById("userEmail");
        const avatarBox = document.getElementById("userAvatar");

        if (nameBox && realUser.Name) nameBox.innerText = realUser.Name;
        if (emailBox && realUser.Email) emailBox.innerText = realUser.Email;
        if (avatarBox && realUser.Name) avatarBox.innerText = realUser.Name.charAt(0).toUpperCase();
    }
};

// --- 5. MULTI-TAB SYNC (The Fix for Admin Logout) ---
window.addEventListener('storage', (event) => {
    if (event.key === 'userData') {
        if (!event.newValue) {
            // Logout detected in another tab! Redirect immediately.
            window.location.href = '/';
        } else {
            // Account change detected! Reload to let bouncer check roles.
            window.location.reload();
        }
    }
});

// Run initialization on load
document.addEventListener("DOMContentLoaded", () => {
    window.userDataManager.initializeUserDisplay();
    
    // Ensure logout button works
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.clear();
            window.location.href = '/';
        });
    }
});