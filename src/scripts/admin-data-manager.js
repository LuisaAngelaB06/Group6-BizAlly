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

// --- 3. ADMIN USER DATA MANAGER CLASS ---
class UserDataManager {
    constructor() {
        this.userDataKey = 'userData';
        this.adminProfileKey = 'adminProfile';
        this.displayInitialized = false;
    }

    getUserData() {
        const userData = JSON.parse(localStorage.getItem(this.userDataKey) || '{}');
        const adminProfile = JSON.parse(localStorage.getItem(this.adminProfileKey) || '{}');
        const adminProfileName = `${adminProfile.firstName || ''} ${adminProfile.lastName || ''}`.trim();
        const userDataName = `${userData.firstName || userData.FirstName || ''} ${userData.lastName || userData.LastName || ''}`.trim();
        const displayName = adminProfile.name ||
            userData.Name ||
            userData.name ||
            userData.displayName ||
            userData.fullName ||
            adminProfileName ||
            userDataName ||
            'Admin';
        const displayEmail = adminProfile.email ||
            userData.Email ||
            userData.email ||
            userData.userEmail ||
            userData.emailAddress ||
            'admin@allitrack.com';
        const profilePicture = adminProfile.photo ||
            adminProfile.profilePicture ||
            adminProfile.avatar ||
            userData.photo ||
            userData.profilePicture ||
            userData.avatar ||
            null;

        return {
            ...userData,
            ...adminProfile,
            fullName: displayName,
            displayName,
            name: displayName,
            email: displayEmail,
            Email: displayEmail,
            photo: profilePicture,
            profilePicture,
            avatar: profilePicture
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
        const adminProfile = JSON.parse(localStorage.getItem(this.adminProfileKey) || '{}');
        const updatedProfile = { ...adminProfile, ...updates };
        localStorage.setItem(this.adminProfileKey, JSON.stringify(updatedProfile));
        this.dispatchUserDataChanged();
        return updatedProfile;
    }

    getProfilePicture() {
        const userData = this.getUserData();
        return userData.photo || userData.profilePicture || userData.avatar || null;
    }

    getUserInitials() {
        const userData = this.getUserData();
        const nameParts = (userData.displayName || userData.fullName || 'Admin').trim().split(/\s+/);
        const firstName = userData.firstName || userData.FirstName || nameParts[0] || 'A';
        const lastName = userData.lastName || userData.LastName || nameParts[1] || '';
        const initials = (firstName.charAt(0) + (lastName.charAt(0) || '')).toUpperCase();
        return initials || 'A';
    }

    dispatchUserDataChanged() {
        const event = new CustomEvent('userDataChanged', {
            detail: this.getUserData()
        });
        document.dispatchEvent(event);
    }

    initializeUserDisplay() {
        this.updateHeaderAvatar();
        this.updateUserInfo();

        if (this.displayInitialized) return;
        this.displayInitialized = true;

        window.addEventListener('storage', (event) => {
            if (event.key === this.userDataKey || event.key === this.adminProfileKey) {
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

        headerAvatar.innerHTML = '';
        headerAvatar.textContent = '';
        headerAvatar.style.backgroundImage = '';
        headerAvatar.style.backgroundSize = '';
        headerAvatar.style.backgroundPosition = '';

        if (profilePicture) {
            const img = document.createElement('img');
            img.src = profilePicture;
            img.alt = 'Profile Picture';
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.borderRadius = '50%';
            img.style.objectFit = 'cover';
            headerAvatar.appendChild(img);
        } else {
            headerAvatar.textContent = initials;
        }
    }

    updateUserInfo() {
        const userData = this.getUserData();

        document.querySelectorAll('#userName, #userNameDisplay').forEach((element) => {
            element.textContent = userData.displayName || 'Admin';
        });

        document.querySelectorAll('#userEmail, #userEmailDisplay').forEach((element) => {
            element.textContent = userData.email || '';
            element.hidden = !userData.email;
        });
    }
}

window.userDataManager = new UserDataManager();

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
            localStorage.removeItem('userData');
            localStorage.removeItem('adminProfile');
            localStorage.removeItem('adminPreferences');
            localStorage.removeItem('preferredLanguage');
            window.location.href = '/';
        });
    }
});
