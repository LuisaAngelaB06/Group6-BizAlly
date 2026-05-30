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
      console.warn("Invalid userData in localStorage:", error);
      return fallback;
    }
  }

  function getUser() {
    return safeParseJSON(localStorage.getItem("userData"), null);
  }

  function getRole() {
    const user = getUser();
    return String(user?.User_Type || user?.user_type || "").toLowerCase();
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

  // 🌟 PRESERVED: Preserves your active technician subdirectory page guard routing rule options exactly
  function protectPage() {
    const user = getUser();
    if (!user) {
      window.location.replace("/");
      return false;
    }

    const role = getRole();
    const rules = getRules(role);
    const section = getSectionFromPath();

    if (!rules.length || (section && !rules.includes(section))) {
      window.location.replace(
        role === "technician"
          ? "/technician/all-tickets.html"
          : "/admin/all-tickets.html",
      );
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

  document.addEventListener("DOMContentLoaded", () => {
    if (!protectPage()) return;
    renderSidebar();
    applyConsoleLabels();
    relabelAssignedTickets();
    applyTicketPermissions();
    applyAnnouncementPermissions();
    setTimeout(applyConsoleLabels, 0);
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