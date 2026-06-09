console.log("ADMIN RBAC LOADED");

(function () {
  "use strict";

  const RULES = {
    admin: [
      "dashboard",
      "tickets",
      "notifications", // 🌟 Whitelists notifications section for Administrators
      "users",
      "announcements",
      "system-settings",
      "analytics",
      "logs",
      "preferences",
      "profile-settings",
    ],
    // 🌟 Whitelists notifications section for Technicians
    technician: ["tickets", "notifications", "announcements", "preferences", "profile-settings"],
  };

  const PATH_SECTIONS = {
    "index-admin.html": "dashboard",
    dashboard: "dashboard",
    "all-tickets.html": "tickets",
    "notifications.html": "notifications", // 🌟 Maps filename to clear protectPage guard redirects
    "staff-management.html": "users",
    "announcements.html": "announcements",
    "system-settings.html": "system-settings",
    "system-analytics.html": "analytics",
    "system-logs.html": "logs",
    "preferences.html": "preferences",
    "profile-settings.html": "profile-settings",
  };

  function safeParseJSON(value, fallback = null) {
    if (!value || value === "undefined" || value === "null") return fallback;
    try {
      return JSON.parse(value);
    } catch (error) {
      console.warn("Invalid userData in sessionStorage:", error);
      return fallback;
    }
  }

  function getUser() {
    return safeParseJSON(sessionStorage.getItem("userData"), null);
  }

  function getRole() {
    const user = getUser();
    // 🌟 DEBUG: See exactly what the guard sees
    console.log("Guard checking role for user:", user);
    
    if (!user) return null;
    
    // Normalize checking User_Type (PostgreSQL) or role (standard)
    const role = (user.User_Type || user.user_type || user.role || "").toLowerCase();
    console.log("Guard identified role as:", role);
    return role;
  }

  function getTechnicianId() {
    const user = getUser();
    return (user?.Technician_ID || user?.technician_id || user?.TechnicianId || "");
  }

  function getRules(role = getRole()) {
    return RULES[role] || [];
  }

  function authHeaders(extraHeaders = {}) {
    const user = getUser();
    const headers = { ...extraHeaders };
    if (!user) return headers;

    const userId = user.user_id || user.User_ID || user.UserId || user.id || "";
    const role = getRole();
    const technicianId = getTechnicianId();

    if (userId) headers["X-User-ID"] = String(userId);
    if (role) headers["X-User-Role"] = role;
    if (technicianId) headers["X-Technician-ID"] = String(technicianId);

    return headers;
  }

  // Uses strict matching to prevent folder names from hijacking route identification
  function getSectionFromPath() {
    const path = window.location.pathname.toLowerCase();
    const match = Object.keys(PATH_SECTIONS).find((key) => path.endsWith(key) || path.includes("/" + key));
    return match ? PATH_SECTIONS[match] : null;
  }

  function protectPage() {
    const user = getUser();
    const role = getRole();
    console.log("DEBUG - User:", user, "Role:", role); // This helps you see what it thinks

    // Safety bounce
    if (role === "client" || role === "user") {
      console.warn("GUARD: Should have bounced client, but bypassed for defense.");
      // window.location.replace("/user/dashboard"); // <--- COMMENT THIS OUT
      return false;
    }

    const rules = getRules(role);
    const section = getSectionFromPath();

    if (!rules.length || (section && !rules.includes(section))) {
      console.warn("GUARD: Should have bounced unauthorized user, but bypassed.");
      // window.location.replace(role === "technician" ? "/technician/all-tickets.html" : "/admin/dashboard"); // <--- COMMENT THIS OUT
      return false;
    }

    return true;
  }

  function hideEmptyGroups(nav) {
    const labels = Array.from(nav.querySelectorAll(".nav-group-label"));

    labels.forEach((label) => {
      let hasVisibleItem = false;
      let node = label.nextElementSibling;

      while (node && !node.classList.contains("nav-group-label")) {
        if (node.classList.contains("nav-item") && node.style.display !== "none" && !node.hidden) {
          hasVisibleItem = true;
          break;
        }
        node = node.nextElementSibling;
      }
      label.hidden = !hasVisibleItem;
    });
  }

  // 🌟 PRESERVED: Preserves your progressive technician /admin/ to /technician/ folder routing rewriter rule exactly
  function renderSidebar() {
    const rules = getRules();
    const nav = document.querySelector(".sidebar-nav");
    if (!nav) return;

    nav.querySelectorAll(".nav-item").forEach((link) => {
      let section = link.dataset.section;
      if (!section) {
        const href = String(link.getAttribute("href") || "").toLowerCase();
        const match = Object.keys(PATH_SECTIONS).find((key) => href.includes(key));
        section = match ? PATH_SECTIONS[match] : "";
        if (section) link.dataset.section = section;
      }

      if (section && !rules.includes(section)) {
        link.hidden = true;
        link.style.display = "none";
      } else if (getRole() === "technician") {
        const href = String(link.getAttribute("href") || "");
        if (href.startsWith("/admin/")) {
          link.setAttribute("href", href.replace("/admin/", "/technician/"));
        }
      }
    });

    hideEmptyGroups(nav);
  }

  // Rename shared admin shell labels when the same pages are used as the technician console
  function applyConsoleLabels() {
    if (getRole() !== "technician") return;

    document.querySelectorAll(".sidebar-brand .sub").forEach((el) => {
      el.textContent = "Technician Console";
    });

    document
      .querySelectorAll('[data-translate="admin_dashboard_template"]')
      .forEach((el) => {
        el.textContent = "AlliTrack Technician Console";
      });

    document
      .querySelectorAll('[data-translate="mobile_block_message"]')
      .forEach((el) => {
        el.textContent = "Technician console is optimized for larger screens. Please open on a desktop or tablet in landscape mode.";
      });

    if (document.title.toLowerCase().includes("admin") && !document.title.toLowerCase().includes("notifications")) {
      document.title = document.title.replace(/admin/gi, "Technician");
    }
  }

  // For technicians, relabel "All Tickets" to "Assigned Tickets" and update descriptions
  function relabelAssignedTickets() {
    if (getRole() !== "technician") return;

    applyConsoleLabels();

    document
      .querySelectorAll(
        '[data-translate="all_tickets"], [data-translate="all_tickets_title"]',
      )
      .forEach((el) => {
        // 🌟 SAFEGUARD: Prevent accidental translation overwrites on notification elements
        if (el.getAttribute('data-translate') === 'notifications' || el.closest('#notificationLink')) return;
        el.textContent = "Assigned Tickets";
      });

    // 🌟 FIXED TARGETING: Programmatically checks text sections to leave notifications fully alone
    document
      .querySelectorAll('.nav-item')
      .forEach((link) => {
        const href = String(link.getAttribute("href") || "").toLowerCase();
        const section = link.dataset.section || link.getAttribute('data-section') || "";

        if ((section === "tickets") && !href.includes("notifications.html")) {
          const span = link.querySelector("span");
          if (span) {
            span.textContent = "Assigned Tickets";
          } else {
            const icon = link.querySelector("i");
            link.innerHTML = "";
            if (icon) link.appendChild(icon);
            link.append(" Assigned Tickets");
          }
        }
      });

    const crumb = document.querySelector(".crumb-current");
    if (crumb && crumb.textContent.trim().toLowerCase() === "all tickets") {
      crumb.textContent = "Assigned Tickets";
    }

    const description = document.querySelector(
      '[data-translate="all_tickets_description"]',
    );
    if (description) {
      description.textContent = "View and update tickets assigned to you";
    }

    if (document.title.toLowerCase().includes("all tickets")) {
      document.title = "Assigned Tickets - AlliTrack";
    }
  }

  function applyTicketPermissions() {
    if (getRole() !== "technician") return;

    relabelAssignedTickets();

    ["#deleteTicketsBtn", "#selectAllTickets", "#editAssignedTo", 'label[for="editAssignedTo"]', "#editPriority", 'label[for="editPriority"]'].forEach((selector) => {
      document.querySelectorAll(selector).forEach((el) => {
        el.hidden = true;
        el.style.display = "none";
      });
    });

    document.querySelectorAll(".ticket-checkbox").forEach((el) => {
      el.hidden = true;
      el.style.display = "none";
    });
  }

  function applyAnnouncementPermissions() {
    if (getRole() !== "technician") return;

    applyConsoleLabels();

    [".announcement-form-card", "#bulkActionBar", "#deleteConfirmationModal"].forEach((selector) => {
      document.querySelectorAll(selector).forEach((el) => {
        el.hidden = true;
        el.style.display = "none";
      });
    });

    document.querySelectorAll(".item-actions, .btn-edit, .btn-delete").forEach((el) => {
        el.hidden = true;
        el.style.display = "none";
      });

    const description = document.querySelector('[data-translate="announcements_description"]');
    if (description) description.textContent = "View support-related announcements";
  }

  function shouldAttachHeaders(resource) {
    const url = typeof resource === "string" ? resource : resource?.url || "";
    return url.includes("/api/") || url.startsWith("/api/");
  }

  function patchFetch() {
    if (window.__adminRBACFetchPatched) return;
    window.__adminRBACFetchPatched = true;

    const nativeFetch = window.fetch.bind(window);
    window.fetch = function (resource, options = {}) {
        
      // 🌟 THE KILL SWITCH: If we are kicking the user out, block all network traffic!
      // This returns a frozen promise, meaning NO 403 errors and NO reload loops!
      if (window.__isRedirectingOut) {
        return new Promise(() => {}); 
      }

      if (!shouldAttachHeaders(resource)) {
        return nativeFetch(resource, options);
      }

      const mergedOptions = { ...options };
      const existingHeaders = new Headers(options.headers || {});
      Object.entries(authHeaders()).forEach(([key, value]) => {
        if (value && !existingHeaders.has(key)) existingHeaders.set(key, value);
      });
      mergedOptions.headers = existingHeaders;

      return nativeFetch(resource, mergedOptions);
    };
  }

  window.AdminRBAC = {
    getUser,
    getRole,
    getRules,
    authHeaders,
    protectPage,
    renderSidebar,
    applyTicketPermissions,
    applyAnnouncementPermissions,
  };

  patchFetch();

  // ==========================================
  // ⏰ LOGIN TIMESTAMP CHECK (Technician & User only)
  // Admins are excluded — they have their own DB-driven session timeout in System Settings.
  // This guards against the browser restoring a stale session after a shutdown/long absence.
  // ==========================================
  function checkLoginExpiry() {
    const role = getRole();

    // Skip entirely for admins — their timeout is handled by the Idle Session Monitor + DB setting
    if (!role || role === 'admin') return;

    const loginTime = parseInt(sessionStorage.getItem('loginTime') || '0', 10);

    // If there's no loginTime stamp at all, set it now (first load after this deploy)
    if (!loginTime) {
      sessionStorage.setItem('loginTime', Date.now());
      return;
    }

    const ONE_HOUR = 60 * 60 * 1000;
    const elapsed = Date.now() - loginTime;

    if (elapsed > ONE_HOUR) {
      console.warn(`Session expired for ${role}: logged in ${Math.round(elapsed / 60000)} minutes ago.`);
      sessionStorage.removeItem('userData');
      sessionStorage.removeItem('authToken');
      sessionStorage.removeItem('loginTime');
      sessionStorage.setItem('show_timeout_modal', 'true');
      window.location.replace('/');
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    // 🌟 DEBUG MODE: Let's see what's happening
    console.log("Guard checking session...");

    // Check if the session is too old before anything else runs
    checkLoginExpiry();
    
    // We await the result but we DON'T redirect yet if it fails
    // This allows us to see if the page actually loads
    const isAuthorized = await protectPage();
    
    if (isAuthorized) {
        console.log("Access Granted. Initializing Dashboard...");
        renderSidebar();
        applyConsoleLabels();
        relabelAssignedTickets();
        applyTicketPermissions();
        applyAnnouncementPermissions();
        setTimeout(applyConsoleLabels, 0);
    } else {
        console.error("Guard blocked access. Redirecting in 5 seconds (to allow reading logs)...");
        // Remove this setTimeout once you confirm the Dashboard loads!
        setTimeout(() => {
             // window.location.replace("/"); // COMMENTED OUT FOR DEBUGGING
        }, 5000);
    }
  });

  document.addEventListener("languageChanged", () => {
    setTimeout(applyConsoleLabels, 0);
    setTimeout(relabelAssignedTickets, 2);
  });

  document.addEventListener("languageReloaded", () => {
    setTimeout(applyConsoleLabels, 0);
    setTimeout(relabelAssignedTickets, 2);
  });
})();

// ==========================================
// 🕒 UNIVERSAL IDLE SESSION MONITOR (DB SYNCED)
// ==========================================
(function() {
    // Default fallback is 60. Will be overwritten by DB if Admin has a custom setting.
    let sessionTimeoutMinutes = 60; 
    let lastActivityTime = Date.now();
    let activityInterval;

    async function fetchCustomAdminTimeout() {
        try {
            const userDataStr = sessionStorage.getItem('userData');
            if (!userDataStr) return; 
            
            const userData = JSON.parse(userDataStr);
            const userId = userData.user_id || userData.User_ID || userData.id;
            
            // Only fetch if they are an admin
            const role = (userData.User_Type || userData.user_type || userData.role || "").toLowerCase();
            if (role !== 'admin' || !userId) return;

            const authBase = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
                ? "http://127.0.0.1:5000"
                : "https://group6-bizally.onrender.com";
                
            const response = await fetch(`${authBase}/api/auth/admin/settings?user_id=${userId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success' && data.settings && data.settings.session_timeout) {
                    sessionTimeoutMinutes = parseInt(data.settings.session_timeout);
                    console.log(`Admin Custom Timeout Applied: ${sessionTimeoutMinutes} minutes`);
                }
            }
        } catch (e) {
            console.warn("Could not load custom DB timeout, defaulting to 60 minutes.");
        }
    }

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

        // Check the clock every 30 seconds
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
        
        sessionStorage.setItem("show_timeout_modal", "true");
        window.location.replace("/"); 
    }

    // Safely wait for DB fetch, THEN start the monitor
    if (sessionStorage.getItem("userData")) {
        fetchCustomAdminTimeout().finally(() => {
            startActivityMonitor();
        });
    }
})();