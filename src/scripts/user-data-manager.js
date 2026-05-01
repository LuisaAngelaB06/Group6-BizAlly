// user-data-manager.js
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

    // Update user profile
    updateUserProfile(updates) {
        const userProfile = JSON.parse(localStorage.getItem(this.userProfileKey) || '{}');
        const updatedProfile = { ...userProfile, ...updates };
        localStorage.setItem(this.userProfileKey, JSON.stringify(updatedProfile));
        
        // Dispatch event for other pages to update
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

document.addEventListener("DOMContentLoaded", function () {
    if (window.userDataManager) {
        window.userDataManager.initializeUserDisplay();
    }
});

async function checkNewAnnouncements() {
    const userData = JSON.parse(localStorage.getItem('userData') || '{}');
    const userId = userData.user_id || userData.user_id;
    const redDot = document.getElementById('navRedDot');

    if (!userId || !redDot) return;

    try {
        const response = await fetch(`http://127.0.0.1:5000/api/user/announcements/unread/${userId}`);
        const unread = await response.json();

        // If the array is empty (length is 0), the dot MUST be hidden
        if (Array.isArray(unread) && unread.length > 0) {
            redDot.style.display = 'inline-block';
        } else {
            redDot.style.display = 'none'; // This hides the dot!
        }
    } catch (e) {
        console.log("Dot check failed, hiding for safety.");
        redDot.style.display = 'none';
    }
}

// Run this on every page load
document.addEventListener('DOMContentLoaded', checkNewAnnouncements);