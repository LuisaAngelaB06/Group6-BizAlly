(function () {
    'use strict';

    const STORAGE_KEYS = {
        userData: 'userData',
        adminProfile: 'adminProfile',
        adminPreferences: 'adminPreferences',
        preferredLanguage: 'preferredLanguage'
    };

    const DEFAULT_ADMIN = {
        name: 'Admin',
        email: '',
        initials: 'AD'
    };

    function safeParseJSON(value, fallback = {}) {
        if (!value || value === 'undefined' || value === 'null') return fallback;
        try {
            return JSON.parse(value);
        } catch (error) {
            console.warn('Invalid JSON in sessionStorage:', error);
            return fallback;
        }
    }

    function redirectTo(path) {
        if (window.location.pathname !== path) {
            window.location.href = path;
        }
    }

    function enforceRouteAccess() {
        const currentPath = window.location.pathname.toLowerCase();
        const userData = safeParseJSON(sessionStorage.getItem(STORAGE_KEYS.userData), null);

        const isPublic =
            currentPath === '/' ||
            currentPath.endsWith('/index.html') ||
            currentPath.endsWith('index.html') ||
            currentPath.includes('landing');

        if (!userData && !isPublic) {
            redirectTo('/');
            return;
        }

        if (!userData) return;

        const role = String(
            userData.User_Type ||
            userData.user_type ||
            userData.role ||
            'client'
        ).toLowerCase();

        const isTryingAdmin = currentPath.includes('/admin');
        const isTryingTechnician = currentPath.includes('/technician');
        const isTryingUser = currentPath.includes('/user');

        if (isTryingAdmin && role === 'client') {
            redirectTo('/user/index-user.html');
            return;
        }

        if (isTryingAdmin && role === 'technician') {
            redirectTo('/technician/all-tickets.html');
            return;
        }

        if (isTryingTechnician && role !== 'technician') {
            redirectTo(role === 'admin' ? '/admin/dashboard' : '/user/index-user.html');
            return;
        }

        if (isTryingUser && role !== 'client') {
            redirectTo(role === 'technician' ? '/technician/all-tickets.html' : '/admin/index-admin.html');
        }
    }

    class UserDataManager {
        constructor() {
            this.userDataKey = STORAGE_KEYS.userData;
            this.adminProfileKey = STORAGE_KEYS.adminProfile;
            this.displayInitialized = false;
        }

        getUserData() {
            const userData = safeParseJSON(sessionStorage.getItem(this.userDataKey));
            const adminProfile = safeParseJSON(sessionStorage.getItem(this.adminProfileKey));

            const adminProfileName = [
                adminProfile.firstName,
                adminProfile.lastName
            ].filter(Boolean).join(' ').trim();

            const userDataName = [
                userData.first_name,
                userData.last_name
            ].filter(Boolean).join(' ').trim();

            const userDataNameAlt = [
                userData.firstName || userData.FirstName || userData.First_Name,
                userData.lastName || userData.LastName || userData.Last_Name
            ].filter(Boolean).join(' ').trim();

            const displayName =
                adminProfile.name ||
                adminProfile.fullName ||
                adminProfile.displayName ||
                adminProfileName ||
                userData.Name ||
                userData.name ||
                userData.displayName ||
                userData.fullName ||
                userDataName ||
                userDataNameAlt ||
                DEFAULT_ADMIN.name;

            const displayEmail =
                adminProfile.email ||
                adminProfile.Email ||
                userData.email ||
                userData.Email ||
                userData.userEmail ||
                userData.emailAddress ||
                DEFAULT_ADMIN.email;

            const profilePicture =
                adminProfile.photo ||
                adminProfile.profilePicture ||
                adminProfile.avatar ||
                userData.photo ||
                userData.profilePicture ||
                userData.avatar ||
                null;

            return {
                ...userData,
                ...adminProfile,
                displayName,
                fullName: displayName,
                name: displayName,
                email: displayEmail,
                Email: displayEmail,
                photo: profilePicture,
                profilePicture,
                avatar: profilePicture
            };
        }

        updateUserData(updates = {}) {
            const currentData = safeParseJSON(sessionStorage.getItem(this.userDataKey));
            const updatedData = { ...currentData, ...updates };

            sessionStorage.setItem(this.userDataKey, JSON.stringify(updatedData));
            this.dispatchUserDataChanged();

            return updatedData;
        }

        updateUserProfile(updates = {}) {
            const currentProfile = safeParseJSON(sessionStorage.getItem(this.adminProfileKey));
            const updatedProfile = { ...currentProfile, ...updates };

            sessionStorage.setItem(this.adminProfileKey, JSON.stringify(updatedProfile));
            this.dispatchUserDataChanged();

            return updatedProfile;
        }

        getProfilePicture() {
            const userData = this.getUserData();
            return userData.photo || userData.profilePicture || userData.avatar || null;
        }

        getUserInitials() {
            const userData = this.getUserData();
            const name = String(userData.displayName || DEFAULT_ADMIN.name).trim();

            if (!name) return DEFAULT_ADMIN.initials;

            const parts = name.split(/\s+/).filter(Boolean);
            const first = parts[0]?.charAt(0) || 'A';
            const last = parts.length > 1 ? parts[parts.length - 1].charAt(0) : '';

            return (first + last).toUpperCase() || DEFAULT_ADMIN.initials;
        }

        dispatchUserDataChanged() {
            document.dispatchEvent(new CustomEvent('userDataChanged', {
                detail: this.getUserData()
            }));
        }

        initializeUserDisplay() {
            this.refreshUserDisplay();

            if (this.displayInitialized) return;
            this.displayInitialized = true;

            window.addEventListener('storage', (event) => {
                if ([this.userDataKey, this.adminProfileKey].includes(event.key)) {
                    this.refreshUserDisplay();
                }
            });

            document.addEventListener('userDataChanged', () => {
                this.refreshUserDisplay();
            });
        }

        refreshUserDisplay() {
            this.updateHeaderAvatar();
            this.updateUserInfo();
            this.updateDropdownHeader();
            this.updateProfileFormIfPresent();
        }

        updateHeaderAvatar() {
            const avatarElements = document.querySelectorAll('#userAvatar, #profileInitials');
            if (!avatarElements.length) return;

            const profilePicture = this.getProfilePicture();
            const initials = this.getUserInitials();

            avatarElements.forEach((avatar) => {
                avatar.innerHTML = '';
                avatar.textContent = '';
                avatar.style.backgroundImage = '';
                avatar.style.backgroundSize = '';
                avatar.style.backgroundPosition = '';

                if (profilePicture && avatar.id === 'userAvatar') {
                    const img = document.createElement('img');
                    img.src = profilePicture;
                    img.alt = 'Profile Picture';
                    img.style.width = '100%';
                    img.style.height = '100%';
                    img.style.borderRadius = '50%';
                    img.style.objectFit = 'cover';
                    avatar.appendChild(img);
                } else {
                    avatar.textContent = initials;
                }
            });
        }

        updateUserInfo() {
            const userData = this.getUserData();

            this.setTextForSelectors(
                ['#userName', '#userNameDisplay', '[data-user-name]'],
                userData.displayName || DEFAULT_ADMIN.name
            );

            this.setTextForSelectors(
                ['#userEmail', '#userEmailDisplay', '[data-user-email]'],
                userData.email || DEFAULT_ADMIN.email
            );
        }

        updateDropdownHeader() {
            const userData = this.getUserData();

            this.setTextForSelectors(
                ['#menuUserName', '[data-menu-user-name]'],
                userData.displayName || DEFAULT_ADMIN.name
            );

            this.setTextForSelectors(
                ['#menuUserEmail', '[data-menu-user-email]'],
                userData.email || DEFAULT_ADMIN.email
            );
        }

        updateProfileFormIfPresent() {
            const userData = this.getUserData();

            const firstNameInput = document.getElementById('firstName');
            const lastNameInput = document.getElementById('lastName');
            const emailInput = document.getElementById('email');

            if (!firstNameInput && !lastNameInput && !emailInput) return;

            const nameParts = String(userData.displayName || '').trim().split(/\s+/);

            const firstName =
                userData.firstName ||
                userData.FirstName ||
                userData.First_Name ||
                userData.first_name ||
                nameParts[0] ||
                '';

            const lastName =
                userData.lastName ||
                userData.LastName ||
                userData.Last_Name ||
                userData.last_name ||
                nameParts.slice(1).join(' ') ||
                '';

            if (firstNameInput && !firstNameInput.value) firstNameInput.value = firstName;
            if (lastNameInput && !lastNameInput.value) lastNameInput.value = lastName;
            if (emailInput && !emailInput.value) emailInput.value = userData.email || DEFAULT_ADMIN.email;
        }

        setTextForSelectors(selectors, value) {
            selectors.forEach((selector) => {
                document.querySelectorAll(selector).forEach((element) => {
                    element.textContent = value;
                    element.hidden = !value;
                });
            });
        }
    }

    function setupLogout() {
        const logoutButtons = document.querySelectorAll('#logoutBtn, [data-logout]');
        if (!logoutButtons.length) return;

        logoutButtons.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();

                sessionStorage.removeItem(STORAGE_KEYS.userData);
                sessionStorage.removeItem(STORAGE_KEYS.adminProfile);
                sessionStorage.removeItem(STORAGE_KEYS.adminPreferences);
                sessionStorage.removeItem(STORAGE_KEYS.preferredLanguage);
                sessionStorage.removeItem('loginTime');

                window.location.href = '/';
            });
        });
    }

    function setupMultiTabSessionSync() {
        window.addEventListener('storage', (event) => {
            if (event.key !== STORAGE_KEYS.userData) return;

            if (!event.newValue) {
                window.location.href = '/';
                return;
            }

            window.location.reload();
        });
    }

    enforceRouteAccess();

    window.userDataManager = window.userDataManager || new UserDataManager();

    setupMultiTabSessionSync();

    document.addEventListener('DOMContentLoaded', () => {
        window.userDataManager.initializeUserDisplay();
        setupLogout();
    });
})();

/* =========================================================================
   🔔 ADMIN / TECHNICIAN RED DOT NOTIFICATION SYSTEM (UNIFIED FINAL)
   ========================================================================= */

window.adminRedDotState = {
    notificationCheckInProgress: false,
    notificationLastCheckTime: 0,
    notificationRetryCount: 0,
    notificationMaxRetries: 3
};

function extractAdminId() {
    const userData = JSON.parse(sessionStorage.getItem("userData") || "{}");
    const id = userData.user_id || userData.id || userData.User_ID || userData.system_user_id || userData.UserId;
    console.log("🔍 [X-RAY] Extracted ID:", id, "from userData:", userData);
    return id;
}

function buildAdminApiUrl(path) {
    const p = String(path || '');
    const apiPath = p.startsWith('/') ? p : `/${p}`;
    const base = (window.API_BASE_URL || '').replace(/\/$/, '');
    if (base.match(/\/api$/) && apiPath.startsWith('/api')) {
        return `${base}${apiPath.slice(4)}`;
    }
    return base ? `${base}${apiPath}` : apiPath;
}

async function checkAdminNotifications(isRetry = false) {
    const userId = extractAdminId();
    if (!userId) {
        console.warn("🛑 [X-RAY] STOPPED: No User ID found. Is the admin logged in?");
        return;
    }

    if (window.adminRedDotState && window.adminRedDotState.notificationCheckInProgress) return;
    
    // Ensure state object exists
    if (!window.adminRedDotState) window.adminRedDotState = { notificationCheckInProgress: false, notificationLastCheckTime: 0, notificationRetryCount: 0, notificationMaxRetries: 3 };

    const now = Date.now();
    if (!isRetry && now - window.adminRedDotState.notificationLastCheckTime < 3000) return;

    window.adminRedDotState.notificationCheckInProgress = true;
    window.adminRedDotState.notificationLastCheckTime = now;

    try {
        const url = window.API_BASE_URL ? `${window.API_BASE_URL}/api/notifications/user/${userId}` : `/api/notifications/user/${userId}`;
        console.log("🌐 [X-RAY] Fetching from API:", url);
        
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const notifications = await response.json();
        
        let hasUnread = false;
        if (Array.isArray(notifications)) {
            hasUnread = notifications.some(notif => 
                notif.unread === true || notif.unread === 1 || notif.unread === "true" ||
                notif.is_read === false || notif.is_read === 0 || notif.is_read === "false"
            );
        }

        console.log(`🎯 [X-RAY] hasUnread evaluated to: ${hasUnread}`);
        
        // 1. Save state globally
        window.allitrackHasUnread = hasUnread;

        // 2. 🌟 THE HEARTBEAT GUARDIAN: Runs twice a second, permanently invincible
        if (!window.redDotHeartbeatStarted) {
            window.redDotHeartbeatStarted = true;
            console.log("💓 [X-RAY] Red Dot Heartbeat is now pulsing...");

            setInterval(() => {
                // Find ANY and ALL notification links on the screen
                const notifLinks = document.querySelectorAll('a[data-section="notifications"], a[href*="notifications.html"], #notificationLink');
                
                notifLinks.forEach(link => {
                    let dot = link.querySelector('.red-dot') || link.querySelector('#notifRedDot');
                    
                    // If RBAC destroyed the dot, instantly recreate it
                    if (!dot) {
                        dot = document.createElement("span");
                        dot.className = "red-dot";
                        dot.id = "notifRedDot";
                        link.appendChild(dot);
                    }

                    // Force the paint with hardcoded fallback colors just in case CSS fails
                    if (window.allitrackHasUnread) {
                        dot.classList.remove("hidden");
                        dot.style.cssText = "display: inline-block !important; position: absolute; right: 75px; margin-top: 0.5px; background-color: #ff4757 !important; width: 8px !important; height: 8px !important; border-radius: 50% !important;";
                        link.style.position = "relative";
                    } else {
                        dot.classList.add("hidden");
                        dot.style.cssText = "display: none !important;";
                    }
                });
            }, 500); // 500ms timer
        }

        window.adminRedDotState.notificationRetryCount = 0;

    } catch (e) {
        console.error("❌ [X-RAY] Fetch Failed:", e.message);
        if (window.adminRedDotState.notificationRetryCount < window.adminRedDotState.notificationMaxRetries) {
            window.adminRedDotState.notificationRetryCount++;
            setTimeout(() => checkAdminNotifications(true), 2000);
        } else {
            window.adminRedDotState.notificationRetryCount = 0;
        }
    } finally {
        window.adminRedDotState.notificationCheckInProgress = false;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(checkAdminNotifications, 500); 
});

// HELPER: Show admin red dot 
function showAdminRedDot(dot) {
    if (!dot) return;
    dot.classList.remove("hidden");
    // 🌟 Wipes out custom shadows/colors, uses native CSS, and nudges it to the left
    dot.style.cssText = "display: inline-block !important; transform: translateX(-15px);"; 
}

// HELPER: Hide admin red dot
function hideAdminRedDot(dot) {
    if (!dot) return;
    dot.classList.add("hidden");
    dot.style.cssText = "display: none !important;";
}

/* =========================================================================
   🍞 NATIVE TOAST NOTIFICATION SYSTEM (MATCHES USER SIDE)
   ========================================================================= */

function ensureToastContainer() {
    let toast = document.getElementById('toast');
    if (toast) return toast;

    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
    return toast;
}

// Attach to window so it can be called from anywhere (like notifications.html)
window.showToast = function (message, type = 'success') {
    const toast = ensureToastContainer();
    
    // Sets the text (Your CSS ::before pseudo-element will handle the icon automatically!)
    toast.textContent = message;
    
    // Applies the base class, the dynamic type (success/error), and triggers the animation
    toast.className = `toast ${type} show`;

    // Removes the 'show' class after 3 seconds to slide it out gracefully
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
};

// ==========================================
// 🕒 UNIVERSAL IDLE SESSION MONITOR (TEST MODE)
// ==========================================
(function() {
    const sessionTimeoutMinutes = 60; 
    let lastActivityTime = Date.now();
    let activityInterval;

    function updateActivity() {
        const currentTime = Date.now();
        const elapsedMinutes = (currentTime - lastActivityTime) / 1000 / 60;
        if (elapsedMinutes >= sessionTimeoutMinutes) {
            executeAutoLogout();
            return;
        }
        lastActivityTime = currentTime;
    }

    function startActivityMonitor() {
        const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
        events.forEach(evt => {
            document.addEventListener(evt, updateActivity, { passive: true });
        });

        // Check the clock every 5 seconds for precise testing
        activityInterval = setInterval(() => {
            const currentTime = Date.now();
            const elapsedMinutes = (currentTime - lastActivityTime) / 1000 / 60;
            if (elapsedMinutes >= sessionTimeoutMinutes) {
                clearInterval(activityInterval);
                executeAutoLogout();
            }
        }, 30000); 
    }

    function executeAutoLogout() {
        sessionStorage.removeItem("userData");
        sessionStorage.removeItem("authToken");
        sessionStorage.removeItem("Technician_ID");
        
        // ✅ Correct key (Triggers the big modal on the landing page)
        sessionStorage.setItem("show_timeout_modal", "true"); 
        
        window.location.replace("/"); 
    }

    // Start monitor if logged in
    if (sessionStorage.getItem("userData")) {
        startActivityMonitor();
    }
})();
