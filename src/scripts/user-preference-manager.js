// preference-manager.js - Centralized system for language and theme synchronization
class PreferencesManager {
    constructor() {
        this.translations = {
            en: {
                // Page titles and headers
                pageTitle: "Preferences - AlliTrack",
                pageHeader: "Preferences",
                successMessage: "Preferences saved successfully!",

                // Sidebar nav group labels (data-translate on .nav-group-label)
                overview: "OVERVIEW",
                support: "SUPPORT",
                management: "MANAGEMENT",
                system: "SYSTEM",

                // Sidebar nav item labels (data-section on .nav-item)
                dashboard: "Dashboard",
                myTickets: "My Tickets",
                notifications: "Notifications",
                submitTicket: "Submit a Ticket",
                preferences: "Preferences",
                profileSettings: "Profile Settings",
                announcements: "Announcements",
                accountSecurity: "Account Security",
                systemInformation: "Legal Center",

                // Sidebar brand sub-label
                userConsole: "User Console",

                // Topbar breadcrumb
                userLabel: "User",

                // Accessibility labels
                sidebarAriaLabel: "Main Sidebar",
                searchAriaLabel: "Search Tickets",

                // Header
                searchPlaceholder: "Search tickets, users, IDs...",

                // Account Menu
                profile: "Profile",
                settings: "Settings",
                logout: "Logout",

                // Sections (for preferences page)
                notificationSettings: "Notification Settings",
                notificationDescription:
                    "Manage how and when you receive notifications",
                languageSettings: "Language Settings",
                languageDescription:
                    "Set your preferred language for the entire dashboard",
                themeSettings: "Theme Settings",
                themeDescription: "Customize your dashboard appearance",

                // Setting items (for preferences page)
                emailNotifications: "Email Notifications",
                emailDescription:
                    "Receive email alerts for ticket updates and system announcements",
                pushNotifications: "Push Notifications",
                pushDescription: "Show browser notifications for urgent updates",
                ticketUpdates: "Ticket Updates",
                ticketDescription: "Notify me when my tickets are updated or resolved",
                announcementNotifications: "New Announcements",
                announcementDescription:
                    "Notify me about new system announcements and features",
                weeklyDigest: "Weekly Digest",
                weeklyDescription: "Send weekly summary of all ticket activities",
                dashboardLanguage: "Dashboard Language",
                languageDropdown:
                    "This will change the language across all pages of your dashboard",
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
                footerText: "AlliTrack User Dashboard",
            },
            fil: {
                // Page titles and headers
                pageTitle: "Mga Kagustuhan - AlliTrack",
                pageHeader: "Mga Kagustuhan",
                successMessage: "Matagumpay na na-save ang mga kagustuhan!",

                // Sidebar nav group labels (data-translate on .nav-group-label)
                overview: "PANGKALAHATANG-IDEYA",
                support: "SUPORTA",
                management: "PAMAMAHALA",
                system: "SISTEMA",

                // Sidebar nav item labels (data-section on .nav-item)
                dashboard: "Dashboard",
                myTickets: "Aking Ticket",
                notifications: "Notipikasyon",
                submitTicket: "Sumite ng Ticket",
                preferences: "Kagustuhan",
                profileSettings: "Settings ng Profile",
                announcements: "Anunsyo",
                accountSecurity: "Seguridad ng Account",
                systemInformation: "Sentrong Legal",

                // Sidebar brand sub-label
                userConsole: "Console ng User",

                // Topbar breadcrumb
                userLabel: "User",

                // Accessibility labels
                sidebarAriaLabel: "Pangunahing Sidebar",
                searchAriaLabel: "Maghanap ng Ticket",

                // Header
                searchPlaceholder: "Maghanap ng ticket, user, ID...",

                // Account Menu
                profile: "Profile",
                settings: "Settings",
                logout: "Logout",

                // Sections (for preferences page)
                notificationSettings: "Mga Setting ng Notipikasyon",
                notificationDescription:
                    "Pamahalaan kung paano at kailan ka makakatanggap ng mga notipikasyon",
                languageSettings: "Mga Setting ng Wika",
                languageDescription:
                    "Itakda ang iyong gustong wika para sa buong dashboard",
                themeSettings: "Mga Setting ng Tema",
                themeDescription: "Ipasadya ang hitsura ng iyong dashboard",

                // Setting items (for preferences page)
                emailNotifications: "Notipikasyon sa Email",
                emailDescription:
                    "Tumanggap ng email alerts para sa mga update ng ticket at mga anunsyo sa sistema",
                pushNotifications: "Notipikasyon sa Browser",
                pushDescription:
                    "Magpakita ng browser notifications para sa mga urgent na update",
                ticketUpdates: "Update ng Ticket",
                ticketDescription:
                    "Ipaalam sa akin kapag ang aking mga ticket ay na-update o na-resolve",
                announcementNotifications: "Mga Bagong Anunsyo",
                announcementDescription:
                    "Ipaalam sa akin ang tungkol sa mga bagong anunsyo at feature ng sistema",
                weeklyDigest: "Weekly Digest",
                weeklyDescription:
                    "Magpadala ng lingguhang buod ng lahat ng aktibidad sa ticket",
                dashboardLanguage: "Wika ng Dashboard",
                languageDropdown:
                    "Ibabago nito ang wika sa lahat ng pahina ng iyong dashboard",
                themeMode: "Mode ng Tema",
                themeModeDescription:
                    "Pagpalit-palitin sa pagitan ng light at dark theme",

                // Theme options
                auto: "Awtomatiko",
                light: "Maliwanag",
                dark: "Madilim",

                // Buttons
                resetDefaults: "I-reset sa Default",
                savePreferences: "I-save ang Kagustuhan",

                // Footer
                footerText: "Dashboard ng User ng AlliTrack",
            },
        };

        this.initialized = false;

        // Force language refresh when storage changes
        window.addEventListener("storage", (event) => {
            if (event.key === "dashboardLanguage") {
                console.log("Language changed in storage, forcing refresh...");
                setTimeout(() => this.applyLanguage(), 100);
            }
        });
    }

    async initialize() {
        if (this.initialized) return;

        console.log("=== INITIALIZING PREFERENCES MANAGER ===");

        // Wait for DOM to be ready
        if (document.readyState === "loading") {
            await new Promise((resolve) => {
                document.addEventListener("DOMContentLoaded", resolve);
            });
        }

        console.log("DOM ready, applying preferences...");
        // Apply saved preferences
        this.applyLanguage();

        // Setup preferences page if needed
        if (document.querySelector(".preferences-content")) {
            this.setupPreferencesPage();
        } else {
            // For other pages, just set up account dropdown
            this.setupAccountDropdown();
            this.setupLogout();
        }

        // Listen for preference changes from other tabs/windows
        this.setupStorageListener();

        this.initialized = true;
        console.log("Preferences Manager initialized successfully");
    }

    setupPreferencesPage() {
        console.log("Setting up preferences page...");

        // Load user data using userDataManager if available
        if (window.userDataManager) {
            console.log("Using userDataManager for user display");
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
        console.log("Setting up preferences form...");

        const preferencesForm = document.getElementById("preferencesForm");
        if (preferencesForm) {
            preferencesForm.addEventListener("submit", (e) => {
                e.preventDefault();
                this.savePreferences();
            });
        }

        // Load saved preferences
        this.loadPreferencesIntoForm();
        // Setup language selector
        this.setupLanguageSelector();

        // Setup reset button
        const resetBtn = document.querySelector(".btn-secondary");
        if (resetBtn) {
            resetBtn.addEventListener("click", (e) => {
                e.preventDefault();
                this.resetPreferences();
            });
        }
    }

    loadPreferencesIntoForm() {
        const savedLanguage = this.getCurrentLanguage();
        const languageSelect = document.getElementById("language");
        if (languageSelect) {
            languageSelect.value = savedLanguage;
        }

        // Load notification settings
        const savedNotifications = JSON.parse(
            localStorage.getItem("notificationSettings") || "{}",
        );
        const emailNotifications = document.getElementById("emailNotifications");
        const pushNotifications = document.getElementById("pushNotifications");
        const ticketUpdates = document.getElementById("ticketUpdates");
        const announcementNotifications = document.getElementById(
            "announcementNotifications",
        );
        const weeklyDigest = document.getElementById("weeklyDigest");

        if (emailNotifications)
            emailNotifications.checked = savedNotifications.email !== false;
        if (pushNotifications)
            pushNotifications.checked = savedNotifications.push !== false;
        if (ticketUpdates)
            ticketUpdates.checked = savedNotifications.ticketUpdates !== false;
        if (announcementNotifications)
            announcementNotifications.checked =
                savedNotifications.announcements !== false;
        if (weeklyDigest)
            weeklyDigest.checked = savedNotifications.weeklyDigest || false;
    }

    setupLanguageSelector() {
        const languageSelect = document.getElementById("language");
        if (languageSelect) {
            languageSelect.addEventListener("change", (e) => {
                const language = e.target.value;
                console.log("Language changed to:", language);
                this.setLanguage(language);

                // Auto-save when language is changed
                if (document.querySelector(".preferences-content")) {
                    this.savePreferences();
                }
            });
        }
    }

    // Language Management
    getCurrentLanguage() {
        const lang = localStorage.getItem("dashboardLanguage") || "en";
        console.log("Getting current language:", lang);
        return lang;
    }

    setLanguage(language) {
        if (!["en", "fil"].includes(language)) {
            console.error("Invalid language:", language);
            return;
        }

        console.log("Setting language to:", language);
        localStorage.setItem("dashboardLanguage", language);
        this.applyLanguage();

        // Broadcast language change to all pages
        this.broadcastPreferenceChange("language", language);
    }

    applyLanguage() {
        const language = this.getCurrentLanguage();
        console.log("=== APPLYING LANGUAGE ===");
        console.log("Language:", language);
        console.log("Available languages:", Object.keys(this.translations));

        const lang = this.translations[language] || this.translations.en;
        console.log("Translation object found:", lang ? "YES" : "NO");

        try {
            this.applyCommonTranslations(lang, language);

            // Apply preferences page specific translations
            if (document.querySelector(".preferences-content")) {
                console.log("Applying preferences page translations...");
                this.applyPreferencesTranslations(lang, language);
            }

            // Dispatch language changed event for other pages to listen to
            document.dispatchEvent(
                new CustomEvent("languageChanged", {
                    detail: { language: language },
                }),
            );
            console.log("Dispatched languageChanged event for:", language);

            console.log("Language applied successfully!");
        } catch (error) {
            console.error("Error applying language:", error);
        }
    }

    applyCommonTranslations(lang, language) {
        console.log("=== APPLYING COMMON TRANSLATIONS ===");

        // ── Sidebar nav item labels ──────────────────────────────────────────
        // Maps data-section attribute values → translation keys
        const navItemMap = {
            dashboard: "dashboard",
            tickets: "myTickets",
            notifications: "notifications",
            "submit-ticket": "submitTicket",
            preferences: "preferences",
            "profile-settings": "profileSettings",
            announcements: "announcements",
            "account-security": "accountSecurity",
            "system-information": "systemInformation",
        };

        // Target .nav-item elements (the actual sidebar links used across all pages)
        const navItems = document.querySelectorAll(".nav-item[data-section]");
        console.log(`Found ${navItems.length} sidebar nav items`);

        navItems.forEach((element) => {
            const section = element.getAttribute("data-section");
            const translationKey = navItemMap[section];

            console.log(`Processing nav-item: ${section} -> key: ${translationKey}`);

            if (translationKey && lang[translationKey]) {
                // Preserve the <i> icon and any badge/dot spans; only replace the text span
                const icon = element.querySelector("i")?.outerHTML || "";
                const badges = Array.from(element.querySelectorAll(".red-dot, .badge"))
                    .map((el) => el.outerHTML)
                    .join("");
                element.innerHTML = `${icon} <span>${lang[translationKey]}</span>${badges}`;
                console.log(
                    `✓ Updated nav-item "${section}" to: ${lang[translationKey]}`,
                );
            } else {
                console.log(
                    `✗ No translation for nav-item "${section}" (key: ${translationKey})`,
                );
            }
        });

        // ── Sidebar group labels (OVERVIEW / SUPPORT / MANAGEMENT / SYSTEM) ─
        // Maps data-translate attribute values → translation keys
        const groupLabelMap = {
            overview: "overview",
            support: "support",
            management: "management",
            system: "system",
        };

        const groupLabels = document.querySelectorAll(
            ".nav-group-label[data-translate]",
        );
        console.log(`Found ${groupLabels.length} sidebar group labels`);

        groupLabels.forEach((element) => {
            const key = element.getAttribute("data-translate");
            const translationKey = groupLabelMap[key];

            if (translationKey && lang[translationKey]) {
                element.textContent = lang[translationKey];
                console.log(
                    `✓ Updated group label "${key}" to: ${lang[translationKey]}`,
                );
            } else {
                console.log(`✗ No translation for group label "${key}"`);
            }
        });

        // ── Sidebar brand sub-label ("User Console") ─────────────────────────
        const brandSub = document.querySelector(
            '.sidebar-brand .sub[data-translate="user_console"]',
        );
        if (brandSub && lang.userConsole) {
            brandSub.textContent = lang.userConsole;
            console.log(`✓ Updated brand sub to: ${lang.userConsole}`);
        }

        // ── Topbar breadcrumb ─────────────────────────────────────────────────
        const breadcrumbUser = document.querySelector(
            '.topbar-left span[data-translate="user"]',
        );
        if (breadcrumbUser && lang.userLabel) {
            breadcrumbUser.textContent = lang.userLabel;
            console.log(`✓ Updated breadcrumb "User" to: ${lang.userLabel}`);
        }

        // ── Header search placeholder ─────────────────────────────────────────
        const searchInput =
            document.getElementById("q") ||
            document.querySelector(
                '.topbar input[type="search"], .topbar input[type="text"]',
            );
        if (searchInput && lang.searchPlaceholder) {
            searchInput.placeholder = lang.searchPlaceholder;
            console.log(`✓ Updated search placeholder to: ${lang.searchPlaceholder}`);
        }

        // ── Account dropdown menu ─────────────────────────────────────────────
        const accountMenuLinks = document.querySelectorAll(".account-menu a");
        console.log(`Found ${accountMenuLinks.length} account menu links`);

        if (accountMenuLinks[0] && lang.profile) {
            this.setTranslatedText(accountMenuLinks[0], lang.profile, "fas fa-user");
            console.log(`✓ Updated Profile to: ${lang.profile}`);
        }
        if (accountMenuLinks[1] && lang.settings) {
            this.setTranslatedText(accountMenuLinks[1], lang.settings, "fas fa-cog");
            console.log(`✓ Updated Settings to: ${lang.settings}`);
        }
        if (accountMenuLinks[2] && lang.logout) {
            this.setTranslatedText(accountMenuLinks[2], lang.logout, "fas fa-sign-out-alt");
            console.log(`✓ Updated Logout to: ${lang.logout}`);
        }

        // ── Footer ────────────────────────────────────────────────────────────
        const footerText = document.querySelector(".site-footer div:last-child");
        if (footerText && lang.footerText) {
            footerText.textContent = lang.footerText;
            console.log(`✓ Updated footer to: ${lang.footerText}`);
        }

        // ── Accessibility labels ──────────────────────────────────────────────
        const sidebar = document.querySelector(".sidebar");
        if (sidebar) {
            sidebar.setAttribute(
                "aria-label",
                lang.sidebarAriaLabel || "Main Sidebar",
            );
        }

        const search = document.querySelector(".search");
        if (search) {
            search.setAttribute(
                "aria-label",
                lang.searchAriaLabel || "Search Tickets",
            );
        }

        console.log("=== COMMON TRANSLATIONS COMPLETE ===");
    }

    setTranslatedText(element, text, fallbackIconClass = "") {
        if (!element) return;

        if (element.tagName === "INPUT" || element.tagName === "TEXTAREA") {
            element.placeholder = text;
            return;
        }

        if (element.tagName === "OPTION") {
            element.textContent = text;
            return;
        }

        let icon = element.querySelector(":scope > i");
        if (!icon && fallbackIconClass) {
            icon = document.createElement("i");
            icon.className = fallbackIconClass;
            element.prepend(icon);
        }

        if (!icon) {
            element.textContent = text;
            return;
        }

        let label = element.querySelector(":scope > span");
        if (!label) {
            label = document.createElement("span");
            Array.from(element.childNodes).forEach((node) => {
                if (node !== icon) node.remove();
            });
            element.appendChild(document.createTextNode(" "));
            element.appendChild(label);
        }

        label.textContent = text;
    }

    applyPreferencesTranslations(lang, language) {
        console.log("=== APPLYING PREFERENCES TRANSLATIONS ===");

        // Update page title
        document.title = lang.pageTitle || "Preferences - AlliTrack";
        console.log(`✓ Updated page title to: ${document.title}`);

        // Update preferences page header
        const preferencesHeader = document.querySelector(".preferences-header h1");
        if (preferencesHeader && lang.pageHeader) {
            preferencesHeader.innerHTML = `<i class="fas fa-sliders-h"></i> ${lang.pageHeader}`;
            console.log(`✓ Updated header to: ${lang.pageHeader}`);
        }

        // Update success message
        const successText = document.querySelector(".success-text");
        if (successText && lang.successMessage) {
            successText.textContent = lang.successMessage;
            console.log(`✓ Updated success message to: ${lang.successMessage}`);
        }

        // Update section titles and descriptions
        const sectionTitles = document.querySelectorAll(".section-title");
        const sectionDescriptions = document.querySelectorAll(
            ".section-description",
        );

        if (sectionTitles[0] && lang.notificationSettings) {
            sectionTitles[0].textContent = lang.notificationSettings;
            console.log(
                `✓ Updated notification settings title to: ${lang.notificationSettings}`,
            );
        }
        if (sectionDescriptions[0] && lang.notificationDescription) {
            sectionDescriptions[0].textContent = lang.notificationDescription;
            console.log(`✓ Updated notification description`);
        }

        if (sectionTitles[1] && lang.languageSettings) {
            sectionTitles[1].textContent = lang.languageSettings;
            console.log(
                `✓ Updated language settings title to: ${lang.languageSettings}`,
            );
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
        const settingTitles = document.querySelectorAll(".setting-title");
        const settingDescriptions = document.querySelectorAll(
            ".setting-description",
        );

        console.log(
            `Found ${settingTitles.length} setting titles and ${settingDescriptions.length} descriptions`,
        );

        // Update each setting based on index
        const settingKeys = [
            "emailNotifications",
            "pushNotifications",
            "ticketUpdates",
            "announcementNotifications",
            "weeklyDigest",
            "dashboardLanguage",
            "themeMode",
        ];

        const descKeys = [
            "emailDescription",
            "pushDescription",
            "ticketDescription",
            "announcementDescription",
            "weeklyDescription",
            "languageDropdown",
            "themeModeDescription",
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
        const themeOptions = document.querySelectorAll(".theme-option");
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
        const resetButton = document.querySelector(".btn-secondary");
        const saveButton = document.querySelector(".btn-primary");
        if (resetButton && lang.resetDefaults) {
            resetButton.innerHTML = `<i class="fas fa-undo"></i> ${lang.resetDefaults}`;
            console.log(`✓ Updated reset button to: ${lang.resetDefaults}`);
        }
        if (saveButton && lang.savePreferences) {
            saveButton.innerHTML = `<i class="fas fa-save"></i> ${lang.savePreferences}`;
            console.log(`✓ Updated save button to: ${lang.savePreferences}`);
        }

        console.log("=== PREFERENCES TRANSLATIONS COMPLETE ===");
    }

    // Cross-tab synchronization
    setupStorageListener() {
        window.addEventListener("storage", (event) => {
            console.log("Storage event:", event.key, "=", event.newValue);

            if (event.key === "dashboardLanguage") {
                console.log("Language changed in another tab:", event.newValue);
                this.applyLanguage();
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
            console.log("Saving preferences...");

            // Collect all preference values
            const preferences = {
                notifications: {
                    email: document.getElementById("emailNotifications")?.checked || true,
                    push: document.getElementById("pushNotifications")?.checked || true,
                    ticketUpdates:
                        document.getElementById("ticketUpdates")?.checked || true,
                    announcements:
                        document.getElementById("announcementNotifications")?.checked ||
                        true,
                    weeklyDigest:
                        document.getElementById("weeklyDigest")?.checked || false,
                },
                language: document.getElementById("language")?.value || "en",
            };

            console.log("Preferences to save:", preferences);

            // Save to localStorage
            localStorage.setItem("dashboardLanguage", preferences.language);
            localStorage.setItem(
                "notificationSettings",
                JSON.stringify(preferences.notifications),
            );
            // Show success message
            const successMessage = document.getElementById("successMessage");
            if (successMessage) {
                successMessage.classList.add("show");

                // Hide success message after 3 seconds
                setTimeout(() => {
                    successMessage.classList.remove("show");
                }, 3000);
            }

            console.log("Preferences saved successfully!");
        } catch (error) {
            console.error("Error saving preferences:", error);
        }
    }

    // Reset preferences
    resetPreferences() {
        try {
            console.log("Resetting preferences to defaults...");

            // Reset toggles to default
            const emailNotifications = document.getElementById("emailNotifications");
            const pushNotifications = document.getElementById("pushNotifications");
            const ticketUpdates = document.getElementById("ticketUpdates");
            const announcementNotifications = document.getElementById(
                "announcementNotifications",
            );
            const weeklyDigest = document.getElementById("weeklyDigest");
            const languageSelect = document.getElementById("language");

            if (emailNotifications) emailNotifications.checked = true;
            if (pushNotifications) pushNotifications.checked = true;
            if (ticketUpdates) ticketUpdates.checked = true;
            if (announcementNotifications) announcementNotifications.checked = true;
            if (weeklyDigest) weeklyDigest.checked = false;
            if (languageSelect) languageSelect.value = "en";

            // Save and apply defaults
            this.savePreferences();

            console.log("Preferences reset to defaults");
        } catch (error) {
            console.error("Error resetting preferences:", error);
        }
    }

    setupLogout() {
        const logoutBtn = document.getElementById("logoutBtn");
        if (logoutBtn) {
            logoutBtn.addEventListener("click", function (e) {
                e.preventDefault();
                console.log("Logout clicked");

                // Clear user data from localStorage
                localStorage.removeItem("userData");
                localStorage.removeItem("dashboardLanguage");
                localStorage.removeItem("notificationSettings");

                // Redirect to login page
                window.location.href = "../../landing page/pages/index.html";
            });
        }
    }

    setupAccountDropdown() {
        const accountBtn = document.getElementById("accountBtn");
        const accountMenu = document.getElementById("accountMenu");

        if (accountBtn && accountMenu) {
            this.ensureAccountMenuIcons();
            this.watchAccountMenuIcons(accountMenu);

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

    ensureAccountMenuIcons() {
        const iconMap = [
            "fas fa-user",
            "fas fa-cog",
            "fas fa-sign-out-alt"
        ];

        document.querySelectorAll(".account-menu a").forEach((link, index) => {
            if (!iconMap[index] || link.querySelector(":scope > i")) return;

            const icon = document.createElement("i");
            icon.className = iconMap[index];
            const label = link.textContent.trim();
            link.textContent = "";
            link.appendChild(icon);
            link.appendChild(document.createTextNode(" "));
            const span = document.createElement("span");
            span.textContent = label;
            link.appendChild(span);
        });
    }

    watchAccountMenuIcons(accountMenu) {
        if (this.accountMenuIconObserver || !accountMenu || !window.MutationObserver) return;

        this.accountMenuIconObserver = new MutationObserver(() => {
            this.ensureAccountMenuIcons();
        });
        this.accountMenuIconObserver.observe(accountMenu, {
            childList: true,
            subtree: true
        });
    }
}

// Initialize globally
window.preferencesManager = new PreferencesManager();
