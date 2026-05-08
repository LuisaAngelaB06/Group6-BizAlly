const API_BASE_URL = (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost')
    ? 'http://127.0.0.1:5000' 
    : 'https://group6-bizally.onrender.com';

// This ensures other functions can use it
window.API_BASE_URL = API_BASE_URL;

const userDataStr = localStorage.getItem("userData");
const currentPath = window.location.pathname.toLowerCase();

(function () {

    // If not logged in
    if (!userDataStr) {

        // allow login page only
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

    console.log("Current Role:", role);
    console.log("Current Path:", currentPath);

    // CLIENT cannot access ADMIN pages
    if (currentPath.includes("/admin/") && role === "client") {
        window.location.href = "/user/index-user.html";
    }

    // ADMIN cannot access USER pages
    if (currentPath.includes("/user/") && role === "admin") {
        window.location.href = "/admin/index-admin.html";
    }

})();

class UserDataManager {
    constructor() {
        this.userDataKey = 'userData';
        this.userProfileKey = 'userProfile';
    }

    // Get combined user data (from both userData and userProfile)
    getUserData() {
        const userData = JSON.parse(localStorage.getItem(this.userDataKey) || '{}');
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        const firstName = userProfile.firstName || userData.firstName || userData.FirstName || '';
        const lastName = userProfile.lastName || userData.lastName || userData.LastName || '';
        const profileName = `${firstName} ${lastName}`.trim();
        const displayName = userData.Name ||
            userData.name ||
            userData.Username ||
            userData.username ||
            userData.fullName ||
            profileName ||
            'User';
        const displayEmail = userData.Email ||
            userData.email ||
            userData.userEmail ||
            userData.emailAddress ||
            userProfile.Email ||
            userProfile.email ||
            '';
        
        return {
            ...userData,
            ...userProfile,
            fullName: displayName,
            displayName,
            email: displayEmail,
            Email: displayEmail
        };
    }

    // Update user data
    updateUserData(updates) {
        const userData = JSON.parse(localStorage.getItem(this.userDataKey) || '{}');
        const updatedData = { ...userData, ...updates };
        localStorage.setItem(this.userDataKey, JSON.stringify(updatedData));
        
        // Dispatch event for other pages to update
        this.dispatchUserDataChanged();
        return updatedData;
    }

    updateProfileDot() {
    const profileDot = document.getElementById('profileRedDot'); // Change 'profileDot' to 'profileRedDot'
    if (!profileDot) return;

    const userData = JSON.parse(localStorage.getItem(this.userDataKey) || '{}');
    
    if (userData.is_profile_complete === true || userData.is_profile_complete === "true") {
        profileDot.style.display = 'none';
    } else {
        profileDot.style.display = 'inline-block';
    }
}

    // Update user profile
    updateUserProfile(updates) {
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        const updatedProfile = { ...userProfile, ...updates };
        localStorage.setItem(this.userProfileKey, JSON.stringify(updatedProfile));
        
        // Dispatch event for other pages to update
        this.dispatchUserDataChanged();
        return updatedProfile;
    }

    getProfilePicture() {
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        const userData = JSON.parse(localStorage.getItem(this.userDataKey) || '{}');
        
        // Look inside userProfile first; if empty, look inside your session token object
        const photo = userProfile.photo || userData.profile_pic_url;

        // If the photo is null, empty, or our "default" string, return null
        if (!photo || photo === 'default-avatar.png' || photo === 'null') {
            return null;
        }
        return photo;
    }

    // Get user initials
    getUserInitials() {
        const userData = this.getUserData();
        const nameParts = (userData.displayName || userData.fullName || 'User').trim().split(/\s+/);
        const firstName = userData.firstName || nameParts[0] || 'U';
        const lastName = userData.lastName || nameParts[1] || '';
        return (firstName.charAt(0) + (lastName.charAt(0) || '')).toUpperCase();
    }

    // Dispatch event when user data changes
    dispatchUserDataChanged() {
        const event = new CustomEvent('userDataChanged', {
            detail: this.getUserData()
        });
        document.dispatchEvent(event);
    }

    // Initialize user data display on any page
    initializeUserDisplay() {
        this.updateHeaderAvatar();
        this.updateUserInfo();
        
        // Listen for changes from other tabs/pages
        window.addEventListener('storage', (event) => {
            if (event.key === this.userDataKey || event.key === this.userProfileKey) {
                this.updateHeaderAvatar();
                this.updateUserInfo();
            }
        });
        
        // Listen for custom events
        document.addEventListener('userDataChanged', () => {
            this.updateHeaderAvatar();
            this.updateUserInfo();
        });
    }

    // Update header avatar across all pages
    updateHeaderAvatar() {
        const headerAvatar = document.getElementById('userAvatar');
        if (!headerAvatar) return;

        const profilePicture = this.getProfilePicture();
        const initials = this.getUserInitials();
        
        if (profilePicture) {
            // Check if it's already an img element
            if (headerAvatar.querySelector('img')) {
                headerAvatar.querySelector('img').src = profilePicture;
            } else {
                headerAvatar.innerHTML = '';
                const img = document.createElement('img');
                img.src = profilePicture;
                img.alt = 'Profile Picture';
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.borderRadius = '50%';
                img.style.objectFit = 'cover';
                headerAvatar.appendChild(img);
            }
        } else {
            headerAvatar.innerHTML = '';
            headerAvatar.textContent = initials;
        }
    }

    // Update user info in header
    updateUserInfo() {
        const userData = this.getUserData();
        
        // Update user name
        const userNameElement = document.getElementById('userName') || document.getElementById('userNameDisplay');
        if (userNameElement) {
            userNameElement.textContent = userData.displayName || 'User';
        }

        // Update user email
        const userEmailElement = document.getElementById('userEmail') || document.getElementById('userEmailDisplay');
        if (userEmailElement) {
            userEmailElement.textContent = userData.email || '';
            userEmailElement.hidden = !userData.email;
        }
    }
}

// Create global instance
window.userDataManager = new UserDataManager();

// --- UNIFIED GLOBAL BACKGROUND TRACKERS (RUNS ONCE PER PAGE REFRESH) ---
if (typeof window.globalHeartbeatFired === 'undefined') {
    window.globalHeartbeatFired = true;

    // 1. Dedicated profile completeness heartbeat check
    // 1. Dedicated profile completeness heartbeat check
    async function checkProfileCompleteness(profileDot) {
        const userData = JSON.parse(localStorage.getItem('userData') || '{}');
        const userId = userData.user_id;

        if (!userId) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/user/profile/complete/${userId}`);
            const result = await response.json();

            if (response.ok && result.status === "success") {
                const isComplete = result.is_profile_complete;
                const normalized = (isComplete === true || isComplete === "true" || isComplete === 1);

                // Update core completion value
                userData.is_profile_complete = normalized;
                
                // 🌟 LIVE AVATAR SYNC: If backend has a photo, force it into current page session memory
                if (result.profile_pic_url) {
                    userData.profile_pic_url = result.profile_pic_url;
                }
                
                localStorage.setItem('userData', JSON.stringify(userData));

                // Toggle red alert dot visibility
                profileDot.style.display = normalized ? 'none' : 'inline-block';
                
                // Refresh avatar layout on the active page instantly
                if (window.userDataManager) {
                    window.userDataManager.updateHeaderAvatar();
                }
            }
        } catch (e) {
            console.error("Global profile background check failed:", e);
            profileDot.style.display = 'inline-block';
        }
    }

    function waitForProfileDot(callback) {
        const dot = document.getElementById('profileRedDot');

        if (dot) {
            callback(dot);
        } else {
            setTimeout(() => waitForProfileDot(callback), 100);
        }
    }

    const executeGlobalInitializations = () => {
        if (window.userDataManager) {
            window.userDataManager.initializeUserDisplay();
        }

        waitForProfileDot((profileDot) => {
            checkProfileCompleteness(profileDot);
        });

        checkNewAnnouncements();
        setupSubmitTicketGuard();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', executeGlobalInitializations);
    } else {
        executeGlobalInitializations();
    }

    // 2. Dedicated announcement check function
    async function checkNewAnnouncements() {
        const userData = JSON.parse(localStorage.getItem('userData') || '{}');
        const userId = userData.user_id;
        const announcementDot = document.getElementById('navRedDot');

        if (!userId || !announcementDot) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/user/announcements/unread/${userId}`);
            const unread = await response.json();

            if (Array.isArray(unread) && unread.length > 0) {
                announcementDot.style.display = 'inline-block';
            } else {
                announcementDot.style.display = 'none';
            }
        } catch (e) {
            console.log("Announcements check failed, hiding dot.");
            announcementDot.style.display = 'none';
        }
    }

    // 3. Sidebar link safety interceptor
    function setupSubmitTicketGuard() {
        const newTicketLink = document.querySelector('a[data-section="submit-ticket"]');
        if (!newTicketLink) return;

        newTicketLink.addEventListener('click', function (e) {
            const userData = JSON.parse(localStorage.getItem('userData') || '{}');
            
            const isComplete = userData.is_profile_complete === true;
            if (!isComplete) {
                e.preventDefault(); // Halt active sidebar link redirection execution

                if (typeof showToast === 'function') {
                    showToast("Please complete your profile before submitting a ticket.", "error");
                } else {
                    alert("Please complete your profile before submitting a ticket.");
                }

                setTimeout(() => {
                    window.location.href = "/user/profile-settings.html";
                }, 1200);
            }
        });
    }
}

// --- GLOBAL TOAST CONTROLLER ---
// --- GLOBAL TOAST SYSTEM ---
window.showToast = function(message, type = 'success') {
    // 1. Create the toast element if it doesn't exist on the current page
    let toast = document.getElementById('globalToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'globalToast';
        toast.className = 'toast';
        toast.innerHTML = `
            <i class="fas fa-info-circle"></i>
            <span id="globalToastMessage"></span>
        `;
        document.body.appendChild(toast);
    }

    const messageEl = document.getElementById('globalToastMessage');
    const iconEl = toast.querySelector('i');

    // 2. Set the icon based on the type
    if (type === 'success') iconEl.className = 'fas fa-check-circle';
    else if (type === 'error') iconEl.className = 'fas fa-exclamation-circle';
    else iconEl.className = 'fas fa-info-circle';

    // 3. Set content and show it
    messageEl.textContent = message;
    toast.className = `toast ${type} show`;

    // 4. Auto-hide after 4 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
};

