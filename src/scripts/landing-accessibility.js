(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {

        // ---------- MOBILE NAVIGATION FIX ----------
        const mobileToggle = document.getElementById('mobileToggle');
        const nav = document.querySelector('.primary-nav');

        if (mobileToggle && nav) {
            // Enhanced mobile toggle handler with body scroll prevention
            const enhancedToggleHandler = function (e) {
                e.stopPropagation();
                const visible = nav.getAttribute('data-visible') === 'true' ? false : true;
                nav.setAttribute('data-visible', visible);
                const icon = this.querySelector('i');
                if (icon) icon.className = visible ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';

                // Update aria-expanded
                this.setAttribute('aria-expanded', visible);

                // Enhanced body scroll prevention
                if (visible) {
                    document.body.style.overflow = 'hidden';
                    document.body.style.position = 'fixed';
                    document.body.style.width = '100%';
                    document.body.style.height = '100%';
                    document.body.style.top = '0';
                    document.body.style.left = '0';
                    document.body.classList.add('menu-open');
                } else {
                    document.body.style.overflow = '';
                    document.body.style.position = '';
                    document.body.style.width = '';
                    document.body.style.height = '';
                    document.body.style.top = '';
                    document.body.style.left = '';
                    document.body.classList.remove('menu-open');
                }
            };

            // Remove existing listener and add enhanced one
            mobileToggle.removeEventListener('click', mobileToggle._listener);
            mobileToggle.addEventListener('click', enhancedToggleHandler);
            mobileToggle._listener = enhancedToggleHandler;

            // Close menu when clicking on links
            nav.querySelectorAll('.nav-link, .btn-login').forEach(link => {
                link.addEventListener('click', () => {
                    nav.setAttribute('data-visible', 'false');
                    const icon = mobileToggle.querySelector('i');
                    if (icon) icon.className = 'fa-solid fa-bars';
                    mobileToggle.setAttribute('aria-expanded', 'false');
                    document.body.style.overflow = '';
                    document.body.style.position = '';
                    document.body.style.width = '';
                    document.body.style.height = '';
                    document.body.style.top = '';
                    document.body.style.left = '';
                    document.body.classList.remove('menu-open');
                });
            });

            // Close menu when clicking outside
            document.removeEventListener('click', document._navCloseHandler);

            document._navCloseHandler = function (e) {
                if (nav.getAttribute('data-visible') === 'true' &&
                    !nav.contains(e.target) &&
                    !mobileToggle.contains(e.target)) {
                    nav.setAttribute('data-visible', 'false');
                    const icon = mobileToggle.querySelector('i');
                    if (icon) icon.className = 'fa-solid fa-bars';
                    mobileToggle.setAttribute('aria-expanded', 'false');
                    document.body.style.overflow = '';
                    document.body.style.position = '';
                    document.body.style.width = '';
                    document.body.style.height = '';
                    document.body.style.top = '';
                    document.body.style.left = '';
                    document.body.classList.remove('menu-open');
                }
            };

            document.addEventListener('click', document._navCloseHandler);
        }

        // ---------- ACTIVE NAV LINK ON SCROLL ----------
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-link');
        const headerOffset = 100;

        function updateActiveLink() {
            let scrollY = window.scrollY + headerOffset + 20;
            sections.forEach(section => {
                const top = section.offsetTop;
                const height = section.offsetHeight;
                const id = section.getAttribute('id');
                if (scrollY >= top && scrollY < top + height) {
                    navLinks.forEach(link => {
                        link.classList.remove('active');
                        if (link.getAttribute('href') === `#${id}`) link.classList.add('active');
                    });
                }
            });
        }

        window.addEventListener('scroll', updateActiveLink);
        window.addEventListener('load', updateActiveLink);

        // ---------- ACCESSIBILITY SETTINGS WITH LOCALSTORAGE ----------
        const STORAGE_PREFIX = 'alliTrack_';
        let fontSizeLevel = 1;
        let highContrast = false;
        let focusHighlight = false;
        let theme = 'light';

        // Load saved preferences
        try {
            fontSizeLevel = JSON.parse(localStorage.getItem(STORAGE_PREFIX + 'fontSize') || '1');
            highContrast = JSON.parse(localStorage.getItem(STORAGE_PREFIX + 'highContrast') || 'false');
            focusHighlight = JSON.parse(localStorage.getItem(STORAGE_PREFIX + 'focusHighlight') || 'false');
            theme = localStorage.getItem(STORAGE_PREFIX + 'theme') || 'light';
        } catch (e) { }

        const FONT_VALUES = ['80%', '100%', '120%', '140%'];
        const FONT_NAMES = ['Small', 'Medium', 'Large', 'X-Large'];
        const body = document.body;

        function applyFontSize() {
            document.documentElement.style.fontSize = FONT_VALUES[fontSizeLevel];
            const lbl = document.getElementById('currentFontSize');
            if (lbl) lbl.textContent = FONT_NAMES[fontSizeLevel];
            localStorage.setItem(STORAGE_PREFIX + 'fontSize', JSON.stringify(fontSizeLevel));
        }

        function applyTheme() {
            body.classList.remove('dark-theme', 'light-theme');
            body.classList.add(theme === 'dark' ? 'dark-theme' : 'light-theme');
            localStorage.setItem(STORAGE_PREFIX + 'theme', theme);
            document.querySelectorAll('.theme-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.theme === theme);
            });
        }

        function applyContrast() {
            body.classList.toggle('high-contrast', highContrast);
            localStorage.setItem(STORAGE_PREFIX + 'highContrast', JSON.stringify(highContrast));
            const btn = document.getElementById('toggleContrast');
            if (btn) btn.classList.toggle('active', highContrast);
        }

        function applyFocus() {
            body.classList.toggle('focus-highlight', focusHighlight);
            localStorage.setItem(STORAGE_PREFIX + 'focusHighlight', JSON.stringify(focusHighlight));
            const btn = document.getElementById('toggleFocus');
            if (btn) btn.classList.toggle('active', focusHighlight);
        }

        function setFontSize(level) {
            if (level >= 0 && level < 4) {
                fontSizeLevel = level;
                applyFontSize();
            }
        }

        function setTheme(t) {
            theme = t;
            applyTheme();
        }

        function setHighContrast(v) {
            highContrast = v;
            applyContrast();
        }

        function setFocus(v) {
            focusHighlight = v;
            applyFocus();
        }

        function resetAll() {
            setFontSize(1);
            setTheme('light');
            setHighContrast(false);
            setFocus(false);
        }

        applyFontSize();
        applyTheme();
        applyContrast();
        applyFocus();

        // ---------- ACCESSIBILITY PANEL CONTROLS ----------
        const toggleBtn = document.getElementById('accessibilityToggle');
        const panel = document.getElementById('accessibilityPanel');
        const closeBtn = document.getElementById('closeAccessibility');

        if (toggleBtn && panel) {
            toggleBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                panel.classList.toggle('open');
                toggleBtn.setAttribute('aria-expanded', panel.classList.contains('open'));
            });

            if (closeBtn) {
                closeBtn.addEventListener('click', function () {
                    panel.classList.remove('open');
                    toggleBtn.setAttribute('aria-expanded', 'false');
                });
            }

            document.addEventListener('click', function (e) {
                if (!panel.contains(e.target) && !toggleBtn.contains(e.target)) {
                    panel.classList.remove('open');
                    toggleBtn.setAttribute('aria-expanded', 'false');
                }
            });
        }

        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                setTheme(this.dataset.theme);
            });
        });

        document.getElementById('decreaseFont')?.addEventListener('click', function () {
            setFontSize(fontSizeLevel - 1);
        });

        document.getElementById('increaseFont')?.addEventListener('click', function () {
            setFontSize(fontSizeLevel + 1);
        });

        document.getElementById('toggleContrast')?.addEventListener('click', function () {
            setHighContrast(!highContrast);
        });

        document.getElementById('toggleFocus')?.addEventListener('click', function () {
            setFocus(!focusHighlight);
        });

        document.getElementById('resetAccessibility')?.addEventListener('click', resetAll);

    });

    // ---------- ESCAPE KEY HANDLER ----------
    document.removeEventListener('keydown', document._escapeHandler);

    document._escapeHandler = function (e) {
        if (e.key === 'Escape') {
            const panel = document.getElementById('accessibilityPanel');
            const toggleBtn = document.getElementById('accessibilityToggle');

            if (panel?.classList.contains('open')) {
                panel.classList.remove('open');
                if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
            }

            const nav = document.querySelector('.primary-nav');
            const mobileToggle = document.getElementById('mobileToggle');

            if (nav?.getAttribute('data-visible') === 'true') {
                nav.setAttribute('data-visible', 'false');
                const icon = mobileToggle?.querySelector('i');
                if (icon) icon.className = 'fa-solid fa-bars';
                if (mobileToggle) mobileToggle.setAttribute('aria-expanded', 'false');
                document.body.style.overflow = '';
                document.body.style.position = '';
                document.body.style.width = '';
                document.body.style.height = '';
                document.body.style.top = '';
                document.body.style.left = '';
                document.body.classList.remove('menu-open');
            }
        }
    };

    document.addEventListener('keydown', document._escapeHandler);

})();