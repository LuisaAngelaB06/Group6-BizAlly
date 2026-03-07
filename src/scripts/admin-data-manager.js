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
        
        return {
            ...userData,
            ...userProfile,
            fullName: `${userProfile.firstName || userData.firstName || ''} ${userProfile.lastName || userData.lastName || ''}`.trim() || userData.name || 'User'
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
        const firstName = userData.firstName || userData.name?.split(' ')[0] || 'U';
        const lastName = userData.lastName || userData.name?.split(' ')[1] || '';
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
        const userNameElement = document.getElementById('userName');
        if (userNameElement) {
            userNameElement.textContent = userData.fullName;
        }

        // Update user email
        const userEmailElement = document.getElementById('userEmail');
        if (userEmailElement && userData.email) {
            userEmailElement.textContent = userData.email;
        }
    }
}

// Create global instance
window.userDataManager = new UserDataManager();