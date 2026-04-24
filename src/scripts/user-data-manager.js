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

// ==========================================
// GLOBAL PROFILE SYNC: Runs on every page load
// ==========================================
document.addEventListener("DOMContentLoaded", function () {
    
    // 1. Check if they are logged in
    const userDataStr = localStorage.getItem("userData");
    if (!userDataStr) return; 
    
    const userData = JSON.parse(userDataStr);
    
    // 🔍 DEBUG: This will print your data to the console so we can see it!
    console.log("DEBUG - User Data from Local Storage:", userData);

    // 2. Find the header profile elements
    const nameDisplay = document.getElementById("userName");
    const emailDisplay = document.getElementById("userEmail");
    const avatarDisplay = document.getElementById("userAvatar");

    // 3. Cast a wider net! Check every possible variation of "Name" or "Username"
    const fullName = userData.Name || userData.name || userData.Username || userData.username || userData.first_name || "User";
    const email = userData.Email || userData.email || "No Email";

    // 4. Inject the real data into the HTML header
    if (nameDisplay) nameDisplay.textContent = fullName;
    if (emailDisplay) emailDisplay.textContent = email;
    if (avatarDisplay && fullName !== "User") {
        avatarDisplay.textContent = fullName.charAt(0).toUpperCase();
    }
});

async function checkNewAnnouncements() {
    const userData = JSON.parse(localStorage.getItem('userData') || '{}');
    const userId = userData.User_ID || userData.user_id;
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