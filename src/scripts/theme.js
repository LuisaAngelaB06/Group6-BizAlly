const THEME_KEY = "preferredTheme";
const VALID_THEMES = ["light", "dark", "auto"];

(function initializeThemeController() {
    const root = document.documentElement;
    const systemPreference = window.matchMedia("(prefers-color-scheme: dark)");

    function getStoredTheme() {
        try {
            const storedTheme = localStorage.getItem(THEME_KEY);
            return VALID_THEMES.includes(storedTheme) ? storedTheme : "auto";
        } catch (error) {
            return "auto";
        }
    }

    function resolveTheme(theme) {
        if (theme === "auto") {
            return systemPreference.matches ? "dark" : "light";
        }

        return theme;
    }

    function applyTheme(theme) {
        const themeToApply = resolveTheme(theme);

        root.classList.remove("light-theme", "dark-theme");
        root.classList.add(`${themeToApply}-theme`);
        root.setAttribute("data-theme", themeToApply);
        root.setAttribute("data-preferred-theme", theme);

        return themeToApply;
    }

    applyTheme(getStoredTheme());

    window.ThemeManager = {
        setTheme(theme) {
            if (!VALID_THEMES.includes(theme)) return;

            try {
                localStorage.setItem(THEME_KEY, theme);
            } catch (error) {
                // Keep applying the requested theme even if storage is unavailable.
            }

            const activeTheme = applyTheme(theme);

            document.dispatchEvent(new CustomEvent("themeChanged", {
                detail: { preferredTheme: theme, theme: activeTheme }
            }));
        },

        getTheme() {
            return getStoredTheme();
        },

        getActiveTheme() {
            return resolveTheme(getStoredTheme());
        },

        applySavedTheme() {
            return applyTheme(getStoredTheme());
        }
    };

    const handleSystemPreferenceChange = () => {
        if (getStoredTheme() === "auto") {
            window.ThemeManager.applySavedTheme();
        }
    };

    if (systemPreference.addEventListener) {
        systemPreference.addEventListener("change", handleSystemPreferenceChange);
    } else if (systemPreference.addListener) {
        systemPreference.addListener(handleSystemPreferenceChange);
    }

    window.addEventListener("storage", (event) => {
        if (event.key === THEME_KEY) {
            window.ThemeManager.applySavedTheme();
        }
    });
})();
