// preference-manager.js - Centralized system for language and theme synchronization
class PreferencesManager {
    constructor() {
        this.translations = {
            en: {
                // Page titles and headers
                pageTitle: "Preferences - AlliTrack",
                pageHeader: "Preferences",
                successMessage: "Preferences saved successfully!",
                
                // Navigation - EXACT keys that match data-section attributes
                dashboard: "Dashboard",
                myTickets: "My Tickets",
                notifications: "Notifications",
                submitTicket: "Submit a Ticket",  // Matches data-section="submit-ticket"
                preferences: "Preferences",
                profileSettings: "Profile Settings",  // Matches data-section="profile-settings"
                announcements: "Announcements",
                accountSecurity: "Account Security",  // Matches data-section="account-security"
                systemInformation: "System Information",  // Matches data-section="system-information"
                support: "Support",
                management: "Management",
                system: "System",
                
                // Header
                searchPlaceholder: "Search tickets, users, IDs...",
                
                // Account Menu
                profile: "Profile",
                settings: "Settings",
                logout: "Logout",
                
                // Sections (for preferences page)
                notificationSettings: "Notification Settings",
                notificationDescription: "Manage how and when you receive notifications",
                languageSettings: "Language Settings",
                languageDescription: "Set your preferred language for the entire dashboard",
                themeSettings: "Theme Settings",
                themeDescription: "Customize your dashboard appearance",
                
                // Setting items (for preferences page)
                emailNotifications: "Email Notifications",
                emailDescription: "Receive email alerts for ticket updates and system announcements",
                pushNotifications: "Push Notifications",
                pushDescription: "Show browser notifications for urgent updates",
                ticketUpdates: "Ticket Updates",
                ticketDescription: "Notify me when my tickets are updated or resolved",
                announcementNotifications: "New Announcements",
                announcementDescription: "Notify me about new system announcements and features",
                weeklyDigest: "Weekly Digest",
                weeklyDescription: "Send weekly summary of all ticket activities",
                dashboardLanguage: "Dashboard Language",
                languageDropdown: "This will change the language across all pages of your dashboard",
                themeMode: "Theme Mode",
                themeModeDescription: "Switch between light and dark theme",
                
                // Theme options
                auto: "Auto",
                light: "Light",
                dark: "Dark",
                
                // Buttons
                resetDefaults: "Reset to Defaults",
                savePreferences: "Save Preferences",
                
                // Footer
                footerText: "Dashboard Template"
            },
            fil: {
                // Page titles and headers
                pageTitle: "Mga Kagustuhan - AlliTrack",
                pageHeader: "Mga Kagustuhan",
                successMessage: "Matagumpay na na-save ang mga kagustuhan!",
                
                // Navigation - EXACT keys that match data-section attributes
                dashboard: "Dashboard",
                myTickets: "Aking Ticket",
                notifications: "Notipikasyon",
                submitTicket: "Sumite Ticket",  // Matches data-section="submit-ticket"
                preferences: "Kagustuhan",
                profileSettings: "Settings ng Profile",  // Matches data-section="profile-settings"
                announcements: "Anunsyo",
                accountSecurity: "Seguridad",  // Matches data-section="account-security"
                systemInformation: "Impormasyon ng Sistema",  // Matches data-section="system-information"
                support: "Suporta",
                management: "Pamahalaan",
                system: "Sistema",
                
                // Header
                searchPlaceholder: "Maghanap ng ticket, user, ID...",
                
                // Account Menu
                profile: "Profile",
                settings: "Settings",
                logout: "Logout",
                
                // Sections (for preferences page)
                notificationSettings: "Mga Setting ng Notipikasyon",
                notificationDescription: "Pamahalaan kung paano at kailan ka makakatanggap ng mga notipikasyon",
                languageSettings: "Mga Setting ng Wika",
                languageDescription: "Itakda ang iyong gustong wika para sa buong dashboard",
                themeSettings: "Mga Setting ng Tema",
                themeDescription: "Ipasadya ang hitsura ng iyong dashboard",
                
                // Setting items (for preferences page)
                emailNotifications: "Notipikasyon sa Email",
                emailDescription: "Tumanggap ng email alerts para sa mga update ng ticket at mga anunsyo sa sistema",
                pushNotifications: "Notipikasyon sa Browser",
                pushDescription: "Magpakita ng browser notifications para sa mga urgent na update",
                ticketUpdates: "Update ng Ticket",
                ticketDescription: "Ipaalam sa akin kapag ang aking mga ticket ay na-update o na-resolve",
                announcementNotifications: "Mga Bagong Anunsyo",
                announcementDescription: "Ipaalam sa akin ang tungkol sa mga bagong anunsyo at feature ng sistema",
                weeklyDigest: "Weekly Digest",
                weeklyDescription: "Magpadala ng lingguhang buod ng lahat ng aktibidad sa ticket",
                dashboardLanguage: "Wika ng Dashboard",
                languageDropdown: "Ibabago nito ang wika sa lahat ng pahina ng iyong dashboard",
                themeMode: "Mode ng Tema",
                themeModeDescription: "Pagpalit-palitin sa pagitan ng light at dark theme",
                
                // Theme options
                auto: "Awtomatiko",
                light: "Maliwanag",
                dark: "Madilim",
                
                // Buttons
                resetDefaults: "I-reset sa Default",
                savePreferences: "I-save ang Kagustuhan",
                
                // Footer
                footerText: "Dashboard"
            }
        };
        
        this.initialized = false;
        
        // Force language refresh when storage changes
        window.addEventListener('storage', (event) => {
            if (event.key === 'dashboardLanguage') {
                console.log('Language changed in storage, forcing refresh...');
                setTimeout(() => this.applyLanguage(), 100);
            }
        });
    }

    async initialize() {
        if (this.initialized) return;
        
        console.log('=== INITIALIZING PREFERENCES MANAGER ===');
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            await new Promise(resolve => {
                document.addEventListener('DOMContentLoaded', resolve);
            });
        }
        
        console.log('DOM ready, applying preferences...');
        
        // Apply saved preferences
        this.applyTheme();
        this.applyLanguage();
        
        // Setup preferences page if needed
        if (document.querySelector('.preferences-content')) {
            this.setupPreferencesPage();
        } else {
            // For other pages, just set up account dropdown
            this.setupAccountDropdown();
            this.setupLogout();
        }
        
        // Listen for preference changes from other tabs/windows
        this.setupStorageListener();
        
        this.initialized = true;
        console.log('Preferences Manager initialized successfully');
    }

    setupPreferencesPage() {
        console.log('Setting up preferences page...');
        
        // Load user data using userDataManager if available
        if (window.userDataManager) {
            console.log('Using userDataManager for user display');
            window.userDataManager.initializeUserDisplay();
        }
        
        // Setup preferences form
        this.setupPreferencesForm();
        
        // Setup logout
        this.setupLogout();
        
        // Setup account dropdown
        this.setupAccountDropdown();
    }

    setupPreferencesForm() {
        console.log('Setting up preferences form...');
        
        const preferencesForm = document.getElementById('preferencesForm');
        if (preferencesForm) {
            preferencesForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.savePreferences();
            });
        }
        
        // Load saved preferences
        this.loadPreferencesIntoForm();
        
        // Setup theme options
        this.setupThemeOptions();
        
        // Setup language selector
        this.setupLanguageSelector();
        
        // Setup reset button
        const resetBtn = document.querySelector('.btn-secondary');
        if (resetBtn) {
            resetBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.resetPreferences();
            });
        }
    }

    loadPreferencesIntoForm() {
        const savedLanguage = this.getCurrentLanguage();
        const languageSelect = document.getElementById('language');
        if (languageSelect) {
            languageSelect.value = savedLanguage;
        }
        
        // Load notification settings
        const savedNotifications = JSON.parse(localStorage.getItem('notificationSettings') || '{}');
        const emailNotifications = document.getElementById('emailNotifications');
        const pushNotifications = document.getElementById('pushNotifications');
        const ticketUpdates = document.getElementById('ticketUpdates');
        const announcementNotifications = document.getElementById('announcementNotifications');
        const weeklyDigest = document.getElementById('weeklyDigest');
        
        if (emailNotifications) emailNotifications.checked = savedNotifications.email !== false;
        if (pushNotifications) pushNotifications.checked = savedNotifications.push !== false;
        if (ticketUpdates) ticketUpdates.checked = savedNotifications.ticketUpdates !== false;
        if (announcementNotifications) announcementNotifications.checked = savedNotifications.announcements !== false;
        if (weeklyDigest) weeklyDigest.checked = savedNotifications.weeklyDigest || false;
        
        // Load theme preference
        const savedTheme = this.getCurrentTheme();
        this.updateThemeOptions(savedTheme);
    }

    setupLanguageSelector() {
        const languageSelect = document.getElementById('language');
        if (languageSelect) {
            languageSelect.addEventListener('change', (e) => {
                const language = e.target.value;
                console.log('Language changed to:', language);
                this.setLanguage(language);
                
                // Auto-save when language is changed
                if (document.querySelector('.preferences-content')) {
                    this.savePreferences();
                }
            });
        }
    }

    setupThemeOptions() {
        const themeOptions = document.querySelectorAll('.theme-option');
        themeOptions.forEach(option => {
            option.addEventListener('click', () => {
                // Remove active class from all options
                themeOptions.forEach(opt => opt.classList.remove('active'));
                
                // Add active class to clicked option
                option.classList.add('active');
                
                // Get selected theme
                const theme = option.getAttribute('data-theme');
                
                // Set theme
                this.setTheme(theme);
                
                // Auto-save preferences
                if (document.querySelector('.preferences-content')) {
                    this.savePreferences();
                }
            });
        });
    }

    updateThemeOptions(selectedTheme) {
        const themeOptions = document.querySelectorAll('.theme-option');
        themeOptions.forEach(option => {
            const theme = option.getAttribute('data-theme');
            if (theme === selectedTheme) {
                option.classList.add('active');
            } else {
                option.classList.remove('active');
            }
        });
    }

    // Theme Management
    getCurrentTheme() {
        return localStorage.getItem('preferredTheme') || 'auto';
    }

    setTheme(theme) {
        if (!['light', 'dark', 'auto'].includes(theme)) {
            console.error('Invalid theme:', theme);
            return;
        }
        
        localStorage.setItem('preferredTheme', theme);
        this.applyTheme();
        
        // Broadcast theme change to all pages
        this.broadcastPreferenceChange('theme', theme);
    }

    applyTheme() {
        const theme = this.getCurrentTheme();
        let themeToApply = theme;
        
        // If theme is 'auto', detect system preference
        if (theme === 'auto') {
            themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        
        // Remove existing theme classes
        document.documentElement.classList.remove('light-theme', 'dark-theme');
        document.body.classList.remove('light-theme', 'dark-theme');
        
        // Add the selected theme class
        document.documentElement.classList.add(themeToApply + '-theme');
        document.body.classList.add(themeToApply + '-theme');
        
        // Apply CSS variables
        this.applyThemeVariables(themeToApply);
        
        console.log('Theme applied:', themeToApply);
    }

    applyThemeVariables(theme) {
        const root = document.documentElement;
        
        if (theme === 'dark') {
            // Dark theme variables
            root.style.setProperty('--surface', '#1e293b');
            root.style.setProperty('--text-primary', '#f1f5f9');
            root.style.setProperty('--text-secondary', '#94a3b8');
            root.style.setProperty('--border', '#334155');
            root.style.setProperty('--hover-bg', 'rgba(59, 130, 246, 0.1)');
            root.style.setProperty('--glass', 'rgba(30, 41, 59, 0.85)');
            root.style.setProperty('--sidebar-border', '#334155');
            root.style.setProperty('--bg', 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)');
            
            // Preferences.css specific variables
            root.style.setProperty('--toggle-bg', '#475569');
            root.style.setProperty('--toggle-handle', '#f8fafc');
            root.style.setProperty('--theme-options-bg', '#334155');
            root.style.setProperty('--accent-border', 'rgba(59, 130, 246, 0.3)');
            
            // Force background color
            document.body.style.background = 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)';
        } else {
            // Light theme variables
            root.style.setProperty('--surface', '#ffffff');
            root.style.setProperty('--text-primary', '#0f172a');
            root.style.setProperty('--text-secondary', '#64748b');
            root.style.setProperty('--border', 'rgba(15, 23, 42, 0.1)');
            root.style.setProperty('--hover-bg', 'rgba(59, 130, 246, 0.06)');
            root.style.setProperty('--glass', 'rgba(255, 255, 255, 0.85)');
            root.style.setProperty('--sidebar-border', '#eef2ff');
            root.style.setProperty('--bg', 'linear-gradient(180deg, #f6f9ff 0%, #ffffff 100%)');
            
            // Preferences.css specific variables
            root.style.setProperty('--toggle-bg', '#e2e8f0');
            root.style.setProperty('--toggle-handle', '#ffffff');
            root.style.setProperty('--theme-options-bg', '#f8fafc');
            root.style.setProperty('--accent-border', 'rgba(59, 130, 246, 0.1)');
            
            // Force background color
            document.body.style.background = 'linear-gradient(180deg, #f6f9ff 0%, #ffffff 100%)';
        }
    }

    // Language Management
    getCurrentLanguage() {
        const lang = localStorage.getItem('dashboardLanguage') || 'en';
        console.log('Getting current language:', lang);
        return lang;
    }

    setLanguage(language) {
        if (!['en', 'fil'].includes(language)) {
            console.error('Invalid language:', language);
            return;
        }
        
        console.log('Setting language to:', language);
        localStorage.setItem('dashboardLanguage', language);
        this.applyLanguage();
        
        // Broadcast language change to all pages
        this.broadcastPreferenceChange('language', language);
    }

    applyLanguage() {
        const language = this.getCurrentLanguage();
        console.log('=== APPLYING LANGUAGE ===');
        console.log('Language:', language);
        console.log('Available languages:', Object.keys(this.translations));
        
        const lang = this.translations[language] || this.translations.en;
        console.log('Translation object found:', lang ? 'YES' : 'NO');
        
        try {
            this.applyCommonTranslations(lang, language);
            
            // Apply preferences page specific translations
            if (document.querySelector('.preferences-content')) {
                console.log('Applying preferences page translations...');
                this.applyPreferencesTranslations(lang, language);
            }
            
            // Dispatch language changed event for other pages to listen to
            document.dispatchEvent(new CustomEvent('languageChanged', {
                detail: { language: language }
            }));
            console.log('Dispatched languageChanged event for:', language);
            
            console.log('Language applied successfully!');
        } catch (error) {
            console.error('Error applying language:', error);
        }
    }

    applyCommonTranslations(lang, language) {
        console.log('=== APPLYING COMMON TRANSLATIONS ===');
        
        const translationMap = {
            'dashboard': 'dashboard',
            'tickets': 'myTickets',
            'notifications': 'notifications',
            'submit-ticket': 'submitTicket',  // Map dash to camelCase
            'preferences': 'preferences',
            'profile-settings': 'profileSettings',  // Map dash to camelCase
            'announcements': 'announcements',
            'account-security': 'accountSecurity',  // Map dash to camelCase
            'system-information': 'systemInformation'  // Map dash to camelCase
        };

        // Update ALL navigation links
        const navLinks = document.querySelectorAll('.nav a[data-section]');
        console.log(`Found ${navLinks.length} navigation links`);
        
        navLinks.forEach(element => {
            const section = element.getAttribute('data-section');
            const translationKey = translationMap[section];
            
            console.log(`Processing: ${section} -> key: ${translationKey}`);
            
            if (translationKey && lang[translationKey]) {
                const icon = element.querySelector('i')?.outerHTML || '';
                element.innerHTML = `${icon} ${lang[translationKey]}`;
                console.log(`✓ Updated ${section} to: ${lang[translationKey]}`);
            } else {
                console.log(`✗ No translation for ${section} (key: ${translationKey})`);
            }
        });

        // Update section headers
        const navSections = document.querySelectorAll('.nav-section');
        console.log(`Found ${navSections.length} section headers`);
        
        if (navSections[0] && lang.support) {
            navSections[0].textContent = lang.support;
            console.log(`✓ Updated Support to: ${lang.support}`);
        }
        if (navSections[1] && lang.management) {
            navSections[1].textContent = lang.management;
            console.log(`✓ Updated Management to: ${lang.management}`);
        }
        if (navSections[2] && lang.system) {
            navSections[2].textContent = lang.system;
            console.log(`✓ Updated System to: ${lang.system}`);
        }

        // Update header search placeholder
        const searchInput = document.getElementById('q');
        if (searchInput && lang.searchPlaceholder) {
            searchInput.placeholder = lang.searchPlaceholder;
            console.log(`✓ Updated search placeholder to: ${lang.searchPlaceholder}`);
        }

        // Update footer
        const footerText = document.querySelector('.site-footer div:last-child');
        if (footerText && lang.footerText) {
            footerText.textContent = lang.footerText;
            console.log(`✓ Updated footer to: ${lang.footerText}`);
        }

        // Update account menu
        const accountMenuLinks = document.querySelectorAll('.account-menu a');
        console.log(`Found ${accountMenuLinks.length} account menu links`);
        
        if (accountMenuLinks[0] && lang.profile) {
            accountMenuLinks[0].textContent = lang.profile;
            console.log(`✓ Updated Profile to: ${lang.profile}`);
        }
        if (accountMenuLinks[1] && lang.settings) {
            accountMenuLinks[1].textContent = lang.settings;
            console.log(`✓ Updated Settings to: ${lang.settings}`);
        }
        if (accountMenuLinks[2] && lang.logout) {
            accountMenuLinks[2].textContent = lang.logout;
            console.log(`✓ Updated Logout to: ${lang.logout}`);
        }

        // Update accessibility labels
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.setAttribute('aria-label', language === 'fil' ? 'Pangunahing Sidebar' : 'Main Sidebar');
        }

        const search = document.querySelector('.search');
        if (search) {
            search.setAttribute('aria-label', language === 'fil' ? 'Maghanap ng Ticket' : 'Search Tickets');
        }

        console.log('=== COMMON TRANSLATIONS COMPLETE ===');
    }

    applyPreferencesTranslations(lang, language) {
        console.log('=== APPLYING PREFERENCES TRANSLATIONS ===');
        
        // Update page title
        document.title = lang.pageTitle || "Preferences - AlliTrack";
        console.log(`✓ Updated page title to: ${document.title}`);
        
        // Update preferences page header
        const preferencesHeader = document.querySelector('.preferences-header h1');
        if (preferencesHeader && lang.pageHeader) {
            preferencesHeader.innerHTML = `<i class="fas fa-sliders-h"></i> ${lang.pageHeader}`;
            console.log(`✓ Updated header to: ${lang.pageHeader}`);
        }
        
        // Update success message
        const successText = document.querySelector('.success-text');
        if (successText && lang.successMessage) {
            successText.textContent = lang.successMessage;
            console.log(`✓ Updated success message to: ${lang.successMessage}`);
        }
        
        // Update section titles and descriptions
        const sectionTitles = document.querySelectorAll('.section-title');
        const sectionDescriptions = document.querySelectorAll('.section-description');
        
        if (sectionTitles[0] && lang.notificationSettings) {
            sectionTitles[0].textContent = lang.notificationSettings;
            console.log(`✓ Updated notification settings title to: ${lang.notificationSettings}`);
        }
        if (sectionDescriptions[0] && lang.notificationDescription) {
            sectionDescriptions[0].textContent = lang.notificationDescription;
            console.log(`✓ Updated notification description`);
        }
        
        if (sectionTitles[1] && lang.languageSettings) {
            sectionTitles[1].textContent = lang.languageSettings;
            console.log(`✓ Updated language settings title to: ${lang.languageSettings}`);
        }
        if (sectionDescriptions[1] && lang.languageDescription) {
            sectionDescriptions[1].textContent = lang.languageDescription;
            console.log(`✓ Updated language description`);
        }
        
        if (sectionTitles[2] && lang.themeSettings) {
            sectionTitles[2].textContent = lang.themeSettings;
            console.log(`✓ Updated theme settings title to: ${lang.themeSettings}`);
        }
        if (sectionDescriptions[2] && lang.themeDescription) {
            sectionDescriptions[2].textContent = lang.themeDescription;
            console.log(`✓ Updated theme description`);
        }
        
        // Update setting titles and descriptions
        const settingTitles = document.querySelectorAll('.setting-title');
        const settingDescriptions = document.querySelectorAll('.setting-description');
        
        console.log(`Found ${settingTitles.length} setting titles and ${settingDescriptions.length} descriptions`);
        
        // Update each setting based on index
        const settingKeys = [
            'emailNotifications', 'pushNotifications', 'ticketUpdates', 
            'announcementNotifications', 'weeklyDigest', 'dashboardLanguage', 'themeMode'
        ];
        
        const descKeys = [
            'emailDescription', 'pushDescription', 'ticketDescription',
            'announcementDescription', 'weeklyDescription', 'languageDropdown', 'themeModeDescription'
        ];
        
        for (let i = 0; i < settingTitles.length; i++) {
            if (settingTitles[i] && lang[settingKeys[i]]) {
                settingTitles[i].textContent = lang[settingKeys[i]];
                console.log(`✓ Updated setting ${i} title to: ${lang[settingKeys[i]]}`);
            }
            if (settingDescriptions[i] && lang[descKeys[i]]) {
                settingDescriptions[i].textContent = lang[descKeys[i]];
                console.log(`✓ Updated setting ${i} description`);
            }
        }
        
        // Update theme options
        const themeOptions = document.querySelectorAll('.theme-option');
        if (themeOptions[0] && lang.auto) {
            themeOptions[0].innerHTML = `<i class="fas fa-desktop"></i> ${lang.auto}`;
            console.log(`✓ Updated auto theme to: ${lang.auto}`);
        }
        if (themeOptions[1] && lang.light) {
            themeOptions[1].innerHTML = `<i class="fas fa-sun"></i> ${lang.light}`;
            console.log(`✓ Updated light theme to: ${lang.light}`);
        }
        if (themeOptions[2] && lang.dark) {
            themeOptions[2].innerHTML = `<i class="fas fa-moon"></i> ${lang.dark}`;
            console.log(`✓ Updated dark theme to: ${lang.dark}`);
        }
        
        // Update button texts
        const resetButton = document.querySelector('.btn-secondary');
        const saveButton = document.querySelector('.btn-primary');
        if (resetButton && lang.resetDefaults) {
            resetButton.innerHTML = `<i class="fas fa-undo"></i> ${lang.resetDefaults}`;
            console.log(`✓ Updated reset button to: ${lang.resetDefaults}`);
        }
        if (saveButton && lang.savePreferences) {
            saveButton.innerHTML = `<i class="fas fa-save"></i> ${lang.savePreferences}`;
            console.log(`✓ Updated save button to: ${lang.savePreferences}`);
        }
        
        console.log('=== PREFERENCES TRANSLATIONS COMPLETE ===');
    }

    // Cross-tab synchronization
    setupStorageListener() {
        window.addEventListener('storage', (event) => {
            console.log('Storage event:', event.key, '=', event.newValue);
            
            if (event.key === 'dashboardLanguage') {
                console.log('Language changed in another tab:', event.newValue);
                this.applyLanguage();
            }
            
            if (event.key === 'preferredTheme') {
                console.log('Theme changed in another tab:', event.newValue);
                this.applyTheme();
            }
        });
    }

    broadcastPreferenceChange(type, value) {
        // This ensures changes are reflected across tabs
        localStorage.setItem(`pref_${type}_timestamp`, Date.now().toString());
    }

    // Save preferences
    savePreferences() {
        try {
            console.log('Saving preferences...');
            
            // Collect all preference values
            const preferences = {
                notifications: {
                    email: document.getElementById('emailNotifications')?.checked || true,
                    push: document.getElementById('pushNotifications')?.checked || true,
                    ticketUpdates: document.getElementById('ticketUpdates')?.checked || true,
                    announcements: document.getElementById('announcementNotifications')?.checked || true,
                    weeklyDigest: document.getElementById('weeklyDigest')?.checked || false
                },
                language: document.getElementById('language')?.value || 'en',
                theme: document.querySelector('.theme-option.active')?.getAttribute('data-theme') || 'auto'
            };
            
            console.log('Preferences to save:', preferences);
            
            // Save to localStorage
            localStorage.setItem('dashboardLanguage', preferences.language);
            localStorage.setItem('notificationSettings', JSON.stringify(preferences.notifications));
            localStorage.setItem('preferredTheme', preferences.theme);
            
            // Show success message
            const successMessage = document.getElementById('successMessage');
            if (successMessage) {
                successMessage.classList.add('show');
                
                // Hide success message after 3 seconds
                setTimeout(() => {
                    successMessage.classList.remove('show');
                }, 3000);
            }
            
            console.log('Preferences saved successfully!');
        } catch (error) {
            console.error('Error saving preferences:', error);
        }
    }

    // Reset preferences
    resetPreferences() {
        try {
            console.log('Resetting preferences to defaults...');
            
            // Reset toggles to default
            const emailNotifications = document.getElementById('emailNotifications');
            const pushNotifications = document.getElementById('pushNotifications');
            const ticketUpdates = document.getElementById('ticketUpdates');
            const announcementNotifications = document.getElementById('announcementNotifications');
            const weeklyDigest = document.getElementById('weeklyDigest');
            const languageSelect = document.getElementById('language');
            
            if (emailNotifications) emailNotifications.checked = true;
            if (pushNotifications) pushNotifications.checked = true;
            if (ticketUpdates) ticketUpdates.checked = true;
            if (announcementNotifications) announcementNotifications.checked = true;
            if (weeklyDigest) weeklyDigest.checked = false;
            if (languageSelect) languageSelect.value = 'en';
            
            // Reset theme to auto
            const themeOptions = document.querySelectorAll('.theme-option');
            themeOptions.forEach(option => {
                option.classList.remove('active');
                if (option.getAttribute('data-theme') === 'auto') {
                    option.classList.add('active');
                }
            });
            
            // Save and apply defaults
            this.savePreferences();
            
            console.log('Preferences reset to defaults');
        } catch (error) {
            console.error('Error resetting preferences:', error);
        }
    }

    setupLogout() {
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Logout clicked');
                
                // Clear user data from localStorage
                localStorage.removeItem('userData');
                localStorage.removeItem('dashboardLanguage');
                localStorage.removeItem('preferredTheme');
                localStorage.removeItem('notificationSettings');
                
                // Redirect to login page
                window.location.href = '../../landing page/pages/index.html';
            });
        }
    }

    setupAccountDropdown() {
        const accountBtn = document.getElementById("accountBtn");
        const accountMenu = document.getElementById("accountMenu");

        if (accountBtn && accountMenu) {
            accountBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                const isExpanded = accountMenu.classList.contains("show");
                accountMenu.classList.toggle("show");
                accountBtn.setAttribute("aria-expanded", !isExpanded);
            });

            // Close dropdown when clicking outside
            document.addEventListener("click", (e) => {
                if (!accountBtn.contains(e.target) && !accountMenu.contains(e.target)) {
                    accountMenu.classList.remove("show");
                    accountBtn.setAttribute("aria-expanded", false);
                }
            });

            // Close dropdown when pressing Escape key
            document.addEventListener("keydown", (e) => {
                if (e.key === "Escape" && accountMenu.classList.contains("show")) {
                    accountMenu.classList.remove("show");
                    accountBtn.setAttribute("aria-expanded", false);
                }
            });
        }
    }
}

// Initialize globally
window.preferencesManager = new PreferencesManager();