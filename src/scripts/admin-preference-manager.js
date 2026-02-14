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
                allTickets: "All Tickets",
                users: "Staff Management",
                announcements: "Announcements",
                preferences: "Preferences",
                profileSettings: "Profile Settings",
                accountSecurity: "Account Security",
                systemSettings: "System Settings",
                analytics: "Analytics",
                logs: "System Logs",
                ticketManagement: "Ticket Management",
                systemManagement: "System Management",
                adminTools: "Admin Tools",
                admin_dashboard: "Admin Dashboard",
                all_tickets: "All Tickets",
                users_management: "Users Management",
                system_settings: "System Settings",
                system_logs: "System Logs",
                profile_settings: "Profile Settings",
                
                // Header
                searchPlaceholder: "Search tickets, users, IDs...",
                
                // Account Menu
                profile: "Profile",
                settings: "Settings",
                logout: "Logout",
                
                // Tabs
                appearance: "Appearance",
                language: "Language",
                notifications: "Notifications",
                accessibility: "Accessibility",
                
                // Theme section
                theme_settings: "Theme Settings",
                choose_appearance: "Choose how AlliTrack looks and feels",
                auto_theme: "Auto (System)",
                auto_theme_desc: "Automatically switches between light and dark based on your system settings",
                light_theme: "Light Mode",
                light_theme_desc: "Clean and bright interface for daytime use",
                dark_theme: "Dark Mode",
                dark_theme_desc: "Easier on the eyes in low-light environments",
                
                // Font section
                font_settings: "Font Settings",
                font_desc: "Adjust text size and font family",
                font_size: "Font Size",
                font_family: "Font Family",
                font_inter: "Inter (Default)",
                font_roboto: "Roboto",
                font_opensans: "Open Sans",
                font_system: "System Font",
                
                // Language section
                language_settings: "Language Settings",
                choose_language: "Select your preferred language for the entire dashboard",
                english: "English",
                english_desc: "United States English - Default language",
                filipino: "Filipino",
                filipino_desc: "Tagalog (Philippines) - Wikang Filipino",
                language_help: "Language changes will apply immediately to the entire dashboard interface.",
                
                // Notification section
                notification_settings: "Notification Settings",
                notification_desc: "Control how you receive updates and alerts",
                email_notifications: "Email Notifications",
                email_desc: "Receive email alerts for important updates",
                browser_notifications: "Browser Notifications",
                browser_desc: "Show push notifications in your browser",
                ticket_updates: "Ticket Updates",
                ticket_desc: "Notify me when tickets are updated or resolved",
                
                // Accessibility section
                accessibility_settings: "Accessibility Settings",
                accessibility_desc: "Make AlliTrack more accessible",
                high_contrast: "High Contrast Mode",
                contrast_desc: "Increase color contrast for better visibility",
                reduce_motion: "Reduce Motion",
                motion_desc: "Minimize animations and transitions",
                
                // Buttons
                reset_defaults: "Reset to Defaults",
                save_changes: "Save Changes",
                customize_experience: "Customize your experience with AlliTrack",
                
                // Footer
                footerText: "Admin Dashboard",
                admin_dashboard_template: "AlliTrack Admin Dashboard"
            },
            fil: {
                // Page titles and headers
                pageTitle: "Mga Kagustuhan - AlliTrack",
                pageHeader: "Mga Kagustuhan",
                successMessage: "Matagumpay na na-save ang mga kagustuhan!",
                
                // Navigation - EXACT keys that match data-section attributes
                dashboard: "Dashboard",
                allTickets: "Lahat ng Ticket",
                users: "Pamamahala ng Staff",
                announcements: "Mga Anunsyo",
                preferences: "Kagustuhan",
                profileSettings: "Settings ng Profile",
                accountSecurity: "Seguridad",
                systemSettings: "Setting ng Sistema",
                analytics: "Analitika",
                logs: "Log ng Sistema",
                ticketManagement: "Pamamahala ng Ticket",
                systemManagement: "Pamamahala ng Sistema",
                adminTools: "Mga Tool ng Admin",
                admin_dashboard: "Admin Dashboard",
                all_tickets: "Lahat ng Ticket",
                users_management: "Pamamahala ng User",
                system_settings: "Mga Setting ng Sistema",
                system_logs: "Log ng Sistema",
                profile_settings: "Settings ng Profile",
                
                // Header
                searchPlaceholder: "Maghanap ng ticket, user, ID...",
                
                // Account Menu
                profile: "Profile",
                settings: "Settings",
                logout: "Logout",
                
                // Tabs
                appearance: "Itsura",
                language: "Wika",
                notifications: "Mga Notipikasyon",
                accessibility: "Accessibilidad",
                
                // Theme section
                theme_settings: "Mga Setting ng Tema",
                choose_appearance: "Piliin kung paano magmumukha at mararamdaman ang AlliTrack",
                auto_theme: "Awtomatiko (Sistema)",
                auto_theme_desc: "Awtomatikong nagpapalit sa pagitan ng light at dark base sa iyong system settings",
                light_theme: "Light Mode",
                light_theme_desc: "Malinis at maliwanag na interface para sa araw-araw na gamit",
                dark_theme: "Dark Mode",
                dark_theme_desc: "Mas madali sa mata sa mga low-light na kapaligiran",
                
                // Font section
                font_settings: "Mga Setting ng Font",
                font_desc: "Ayusin ang laki ng teksto at pamilya ng font",
                font_size: "Laki ng Font",
                font_family: "Pamilya ng Font",
                font_inter: "Inter (Default)",
                font_roboto: "Roboto",
                font_opensans: "Open Sans",
                font_system: "System Font",
                
                // Language section
                language_settings: "Mga Setting ng Wika",
                choose_language: "Piliin ang iyong gustong wika para sa buong dashboard",
                english: "Ingles",
                english_desc: "United States English - Default na wika",
                filipino: "Filipino",
                filipino_desc: "Tagalog (Pilipinas) - Wikang Filipino",
                language_help: "Ang mga pagbabago sa wika ay agad na maa-apply sa buong dashboard interface.",
                
                // Notification section
                notification_settings: "Mga Setting ng Notipikasyon",
                notification_desc: "Kontrolin kung paano ka makakatanggap ng mga update at alerto",
                email_notifications: "Notipikasyon sa Email",
                email_desc: "Tumanggap ng email alerts para sa mga importanteng update",
                browser_notifications: "Notipikasyon sa Browser",
                browser_desc: "Magpakita ng push notifications sa iyong browser",
                ticket_updates: "Update ng Ticket",
                ticket_desc: "Ipaalam sa akin kapag ang mga ticket ay na-update o na-resolve",
                
                // Accessibility section
                accessibility_settings: "Mga Setting ng Accessibilidad",
                accessibility_desc: "Gawing mas accessible ang AlliTrack",
                high_contrast: "High Contrast Mode",
                contrast_desc: "Dagdagan ang color contrast para sa mas magandang visibility",
                reduce_motion: "Bawasan ang Motion",
                motion_desc: "Minimahin ang mga animation at transition",
                
                // Buttons
                reset_defaults: "I-reset sa Default",
                save_changes: "I-save ang mga Pagbabago",
                customize_experience: "Ipasadya ang iyong karanasan sa AlliTrack",
                
                // Footer
                footerText: "Admin Dashboard",
                admin_dashboard_template: "AlliTrack Admin Dashboard"
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
        
        // Setup tabs
        this.setupTabs();
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
        
        // Setup font controls
        this.setupFontControls();
        
        // Setup notification toggles
        this.setupNotificationToggles();
        
        // Setup accessibility toggles
        this.setupAccessibilityToggles();
        
        // Setup reset button
        const resetBtn = document.getElementById('resetBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.resetPreferences();
            });
        }
        
        // Setup save button
        const saveBtn = document.getElementById('saveBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.savePreferences();
            });
        }
    }

    setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.preferences-tab');
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                
                // Update active tab button
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Show selected tab content
                tabContents.forEach(content => content.classList.remove('active'));
                const activeTab = document.getElementById(`${tabId}-tab`);
                if (activeTab) {
                    activeTab.classList.add('active');
                }
            });
        });
    }

    loadPreferencesIntoForm() {
        const savedLanguage = this.getCurrentLanguage();
        const savedTheme = this.getCurrentTheme();
        
        console.log('Loading saved preferences:', { language: savedLanguage, theme: savedTheme });
        
        // Set language radio button
        const languageRadio = document.querySelector(`input[name="language"][value="${savedLanguage}"]`);
        if (languageRadio) {
            languageRadio.checked = true;
            languageRadio.closest('.language-card')?.classList.add('selected');
        }
        
        // Set theme radio button
        const themeRadio = document.querySelector(`input[name="theme"][value="${savedTheme}"]`);
        if (themeRadio) {
            themeRadio.checked = true;
            themeRadio.closest('.theme-card')?.classList.add('selected');
        }
        
        // Load font preferences
        const savedFontSize = localStorage.getItem('fontSize') || 'medium';
        const savedFontFamily = localStorage.getItem('fontFamily') || 'inter';
        
        // Set font size buttons
        const fontSizeBtns = document.querySelectorAll('.font-size-btn');
        fontSizeBtns.forEach(btn => {
            if (btn.dataset.size === savedFontSize) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        // Set font family select
        const fontSelect = document.getElementById('font-family');
        if (fontSelect) {
            fontSelect.value = savedFontFamily;
        }
        
        // Load notification settings
        const savedNotifications = JSON.parse(localStorage.getItem('notificationSettings') || '{}');
        const emailNotifications = document.getElementById('email-notifications');
        const browserNotifications = document.getElementById('browser-notifications');
        const ticketUpdates = document.getElementById('ticket-updates');
        
        if (emailNotifications) emailNotifications.checked = savedNotifications.email !== false;
        if (browserNotifications) browserNotifications.checked = savedNotifications.browser !== false;
        if (ticketUpdates) ticketUpdates.checked = savedNotifications.ticketUpdates !== false;
        
        // Load accessibility settings
        const savedAccessibility = JSON.parse(localStorage.getItem('accessibilitySettings') || '{}');
        const highContrast = document.getElementById('high-contrast');
        const reduceMotion = document.getElementById('reduce-motion');
        
        if (highContrast) highContrast.checked = savedAccessibility.highContrast || false;
        if (reduceMotion) reduceMotion.checked = savedAccessibility.reduceMotion || false;
    }

    setupLanguageSelector() {
        const languageCards = document.querySelectorAll('.language-card');
        
        languageCards.forEach(card => {
            card.addEventListener('click', () => {
                const language = card.dataset.language;
                
                // Update radio button
                const radio = card.querySelector('input[type="radio"]');
                if (radio) {
                    radio.checked = true;
                    
                    // Update card selection
                    languageCards.forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    
                    // Apply language immediately
                    this.setLanguage(language);
                    
                    // Show toast notification
                    this.showToast('Language updated', 'success');
                }
            });
        });
    }

    setupThemeOptions() {
        const themeCards = document.querySelectorAll('.theme-card');
        
        themeCards.forEach(card => {
            card.addEventListener('click', () => {
                const theme = card.dataset.theme;
                
                // Update radio button
                const radio = card.querySelector('input[type="radio"]');
                if (radio) {
                    radio.checked = true;
                    
                    // Update card selection
                    themeCards.forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    
                    // Apply theme immediately
                    this.setTheme(theme);
                    
                    // Show toast notification
                    this.showToast('Theme updated', 'success');
                }
            });
        });
    }

    setupFontControls() {
        // Font size buttons
        const fontSizeBtns = document.querySelectorAll('.font-size-btn');
        fontSizeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const size = btn.dataset.size;
                
                // Update active button
                fontSizeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Save preference
                localStorage.setItem('fontSize', size);
                
                // Apply font size
                this.applyFontSize(size);
            });
        });
        
        // Font family select
        const fontSelect = document.getElementById('font-family');
        if (fontSelect) {
            fontSelect.addEventListener('change', (e) => {
                const fontFamily = e.target.value;
                
                // Save preference
                localStorage.setItem('fontFamily', fontFamily);
                
                // Apply font family
                this.applyFontFamily(fontFamily);
            });
        }
    }

    setupNotificationToggles() {
        const notificationToggles = [
            'email-notifications',
            'browser-notifications',
            'ticket-updates'
        ];
        
        notificationToggles.forEach(id => {
            const toggle = document.getElementById(id);
            if (toggle) {
                toggle.addEventListener('change', () => {
                    this.saveNotificationSettings();
                });
            }
        });
    }

    setupAccessibilityToggles() {
        const accessibilityToggles = [
            'high-contrast',
            'reduce-motion'
        ];
        
        accessibilityToggles.forEach(id => {
            const toggle = document.getElementById(id);
            if (toggle) {
                toggle.addEventListener('change', () => {
                    this.saveAccessibilitySettings();
                });
            }
        });
    }

    saveNotificationSettings() {
        const notifications = {
            email: document.getElementById('email-notifications')?.checked || true,
            browser: document.getElementById('browser-notifications')?.checked || true,
            ticketUpdates: document.getElementById('ticket-updates')?.checked || true
        };
        
        localStorage.setItem('notificationSettings', JSON.stringify(notifications));
        console.log('Notification settings saved:', notifications);
    }

    saveAccessibilitySettings() {
        const accessibility = {
            highContrast: document.getElementById('high-contrast')?.checked || false,
            reduceMotion: document.getElementById('reduce-motion')?.checked || false
        };
        
        localStorage.setItem('accessibilitySettings', JSON.stringify(accessibility));
        console.log('Accessibility settings saved:', accessibility);
    }

    applyFontSize(size) {
        const sizes = {
            'small': '0.875rem',
            'medium': '1rem',
            'large': '1.125rem',
            'xlarge': '1.25rem'
        };
        
        document.documentElement.style.setProperty('--base-font-size', sizes[size] || '1rem');
        console.log('Font size applied:', size);
    }

    applyFontFamily(fontFamily) {
        const fonts = {
            'inter': "'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial",
            'roboto': "'Roboto', sans-serif",
            'open-sans': "'Open Sans', sans-serif",
            'system': "system-ui, -apple-system, sans-serif"
        };
        
        document.body.style.fontFamily = fonts[fontFamily] || fonts.inter;
        console.log('Font family applied:', fontFamily);
    }

    updateThemeOptions(selectedTheme) {
        const themeCards = document.querySelectorAll('.theme-card');
        themeCards.forEach(card => {
            const theme = card.dataset.theme;
            if (theme === selectedTheme) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
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
            
            // Apply dashboard page translations if needed
            if (document.querySelector('.dashboard-content')) {
                console.log('Applying dashboard page translations...');
                this.applyDashboardTranslations(lang, language);
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
            'tickets': 'allTickets',
            'users': 'users',
            'announcements': 'announcements',
            'preferences': 'preferences',
            'profile-settings': 'profileSettings',
            'account-security': 'accountSecurity',
            'system-settings': 'systemSettings',
            'analytics': 'analytics',
            'logs': 'logs'
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
        
        if (navSections[0] && lang.ticketManagement) {
            navSections[0].textContent = lang.ticketManagement;
            console.log(`✓ Updated Ticket Management to: ${lang.ticketManagement}`);
        }
        if (navSections[1] && lang.systemManagement) {
            navSections[1].textContent = lang.systemManagement;
            console.log(`✓ Updated System Management to: ${lang.systemManagement}`);
        }
        if (navSections[2] && lang.adminTools) {
            navSections[2].textContent = lang.adminTools;
            console.log(`✓ Updated Admin Tools to: ${lang.adminTools}`);
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
        const pageTitle = document.querySelector('.page-title h1');
        const pageSubtitle = document.querySelector('.page-title .subtitle');
        
        if (pageTitle && lang.preferences) {
            pageTitle.textContent = lang.preferences;
            console.log(`✓ Updated header to: ${lang.preferences}`);
        }
        if (pageSubtitle && lang.customize_experience) {
            pageSubtitle.textContent = lang.customize_experience;
            console.log(`✓ Updated subtitle to: ${lang.customize_experience}`);
        }
        
        // Update tab buttons
        const tabBtns = document.querySelectorAll('.tab-btn span[data-translate]');
        tabBtns.forEach(btn => {
            const key = btn.getAttribute('data-translate');
            if (lang[key]) {
                btn.textContent = lang[key];
                console.log(`✓ Updated tab ${key} to: ${lang[key]}`);
            }
        });
        
        // Update section headers and descriptions
        document.querySelectorAll('[data-translate]').forEach(element => {
            const key = element.getAttribute('data-translate');
            if (lang[key]) {
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    element.placeholder = lang[key];
                } else {
                    element.textContent = lang[key];
                }
                console.log(`✓ Updated ${key} to: ${lang[key]}`);
            }
        });
        
        // Update footer
        const footerDiv = document.querySelector('.site-footer div:last-child');
        if (footerDiv && lang.admin_dashboard_template) {
            footerDiv.textContent = lang.admin_dashboard_template;
        }
        
        console.log('=== PREFERENCES TRANSLATIONS COMPLETE ===');
    }

    // NEW: Apply dashboard translations
    applyDashboardTranslations(lang, language) {
        console.log('=== APPLYING DASHBOARD TRANSLATIONS ===');
        
        // Update dashboard-specific elements
        document.querySelectorAll('[data-translate]').forEach(element => {
            const key = element.getAttribute('data-translate');
            if (lang[key]) {
                element.textContent = lang[key];
                console.log(`✓ Updated ${key} to: ${lang[key]}`);
            }
        });
        
        console.log('=== DASHBOARD TRANSLATIONS COMPLETE ===');
    }

    // NEW: Reload all translations
    reloadAllTranslations() {
        console.log('=== RELOADING ALL TRANSLATIONS ===');
        this.applyLanguage();
        
        // Dispatch event to update other components
        const currentLanguage = this.getCurrentLanguage();
        document.dispatchEvent(new CustomEvent('languageReloaded', {
            detail: { language: currentLanguage }
        }));
        
        // Force storage event for other tabs
        localStorage.setItem('dashboardLanguage', currentLanguage);
        localStorage.setItem('langReloadTimestamp', Date.now().toString());
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
                theme: document.querySelector('input[name="theme"]:checked')?.value || 'auto',
                language: document.querySelector('input[name="language"]:checked')?.value || 'en',
                fontSize: localStorage.getItem('fontSize') || 'medium',
                fontFamily: localStorage.getItem('fontFamily') || 'inter',
                notifications: JSON.parse(localStorage.getItem('notificationSettings') || '{}'),
                accessibility: JSON.parse(localStorage.getItem('accessibilitySettings') || '{}')
            };
            
            console.log('Preferences to save:', preferences);
            
            // Save to localStorage
            localStorage.setItem('preferredTheme', preferences.theme);
            localStorage.setItem('dashboardLanguage', preferences.language);
            localStorage.setItem('fontSize', preferences.fontSize);
            localStorage.setItem('fontFamily', preferences.fontFamily);
            
            // Apply preferences
            this.applyTheme();
            this.applyLanguage();
            this.applyFontSize(preferences.fontSize);
            this.applyFontFamily(preferences.fontFamily);
            
            // Show success message
            this.showToast('Preferences saved successfully', 'success');
            
            console.log('Preferences saved successfully!');
        } catch (error) {
            console.error('Error saving preferences:', error);
            this.showToast('Error saving preferences', 'error');
        }
    }

    // Reset preferences
    resetPreferences() {
        try {
            console.log('Resetting preferences to defaults...');
            
            // Reset theme to auto
            const themeAuto = document.querySelector('input[name="theme"][value="auto"]');
            if (themeAuto) {
                themeAuto.checked = true;
                themeAuto.closest('.theme-card')?.classList.add('selected');
            }
            
            // Reset language to English
            const languageEn = document.querySelector('input[name="language"][value="en"]');
            if (languageEn) {
                languageEn.checked = true;
                languageEn.closest('.language-card')?.classList.add('selected');
            }
            
            // Reset font size to medium
            const fontSizeBtns = document.querySelectorAll('.font-size-btn');
            fontSizeBtns.forEach(btn => {
                if (btn.dataset.size === 'medium') {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
            
            // Reset font family to inter
            const fontSelect = document.getElementById('font-family');
            if (fontSelect) {
                fontSelect.value = 'inter';
            }
            
            // Reset notification toggles
            const emailNotifications = document.getElementById('email-notifications');
            const browserNotifications = document.getElementById('browser-notifications');
            const ticketUpdates = document.getElementById('ticket-updates');
            
            if (emailNotifications) emailNotifications.checked = true;
            if (browserNotifications) browserNotifications.checked = true;
            if (ticketUpdates) ticketUpdates.checked = true;
            
            // Reset accessibility toggles
            const highContrast = document.getElementById('high-contrast');
            const reduceMotion = document.getElementById('reduce-motion');
            
            if (highContrast) highContrast.checked = false;
            if (reduceMotion) reduceMotion.checked = false;
            
            // Save reset preferences
            this.savePreferences();
            
            console.log('Preferences reset to defaults');
        } catch (error) {
            console.error('Error resetting preferences:', error);
        }
    }

    showToast(message, type = 'success') {
        // Create toast element if it doesn't exist
        let toast = document.getElementById('preference-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'preference-toast';
            toast.className = 'toast';
            document.body.appendChild(toast);
        }
        
        toast.textContent = message;
        toast.className = `toast ${type}`;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
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
                localStorage.removeItem('accessibilitySettings');
                localStorage.removeItem('fontSize');
                localStorage.removeItem('fontFamily');
                
                // Redirect to login page
                window.location.href = '../../../index.html';
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

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.preferencesManager.initialize();
    });
} else {
    window.preferencesManager.initialize();
}