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
            console.warn('Invalid JSON in localStorage:', error);
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
        const userData = safeParseJSON(localStorage.getItem(STORAGE_KEYS.userData), null);

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
        const isTryingUser = currentPath.includes('/user');

        if (isTryingAdmin && role === 'client') {
            redirectTo('/user/index-user.html');
            return;
        }

        if (isTryingUser && role !== 'client') {
            redirectTo('/admin/index-admin.html');
        }
    }

    class UserDataManager {
        constructor() {
            this.userDataKey = STORAGE_KEYS.userData;
            this.adminProfileKey = STORAGE_KEYS.adminProfile;
            this.displayInitialized = false;
        }

        getUserData() {
            const userData = safeParseJSON(localStorage.getItem(this.userDataKey));
            const adminProfile = safeParseJSON(localStorage.getItem(this.adminProfileKey));

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
            const currentData = safeParseJSON(localStorage.getItem(this.userDataKey));
            const updatedData = { ...currentData, ...updates };

            localStorage.setItem(this.userDataKey, JSON.stringify(updatedData));
            this.dispatchUserDataChanged();

            return updatedData;
        }

        updateUserProfile(updates = {}) {
            const currentProfile = safeParseJSON(localStorage.getItem(this.adminProfileKey));
            const updatedProfile = { ...currentProfile, ...updates };

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

                localStorage.removeItem(STORAGE_KEYS.userData);
                localStorage.removeItem(STORAGE_KEYS.adminProfile);
                localStorage.removeItem(STORAGE_KEYS.adminPreferences);
                localStorage.removeItem(STORAGE_KEYS.preferredLanguage);

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
