(function () {
  "use strict";

  const RULES = {
    admin: [
      "dashboard",
      "tickets",
      "users",
      "announcements",
      "system-settings",
      "analytics",
      "logs",
      "preferences",
      "profile-settings",
    ],
    technician: ["tickets", "announcements", "preferences", "profile-settings"],
  };

  const PATH_SECTIONS = {
    "index-admin.html": "dashboard",
    dashboard: "dashboard",
    "all-tickets.html": "tickets",
    "staff-management.html": "users",
    "announcements.html": "announcements",
    "system-settings.html": "system-settings",
    "system-analytics.html": "analytics",
    "system-logs.html": "logs",
    "preferences.html": "preferences",
    "profile-settings.html": "profile-settings",
  };

  // Safely parse JSON from localStorage, returning a fallback value if parsing fails or if the value is invalid
  function safeParseJSON(value, fallback = null) {
    if (!value || value === "undefined" || value === "null") return fallback;
    try {
      return JSON.parse(value);
    } catch (error) {
      console.warn("Invalid userData in localStorage:", error);
      return fallback;
    }
  }

  // Retrieve the current user's data from localStorage, returning null if not found or if the data is invalid
  function getUser() {
    return safeParseJSON(localStorage.getItem("userData"), null);
  }

  // Determine the user's role by checking common properties in the user object, defaulting to an empty string if not found
  function getRole() {
    const user = getUser();
    return String(user?.User_Type || user?.user_type || "").toLowerCase();
  }

  // Determine the technician ID from the user object, checking multiple possible property names and defaulting to an empty string if not found
  function getTechnicianId() {
    const user = getUser();
    return (
      user?.Technician_ID || user?.technician_id || user?.TechnicianId || ""
    );
  }

  // Get the allowed sections for a given role, defaulting to the current user's role if not provided
  function getRules(role = getRole()) {
    return RULES[role] || [];
  }

  // Generate authentication headers based on the current user's information
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

  // Determine the current section based on the URL path
  function getSectionFromPath() {
    const path = window.location.pathname.toLowerCase();
    const match = Object.keys(PATH_SECTIONS).find((key) => path.includes(key));
    return match ? PATH_SECTIONS[match] : null;
  }

  // Redirect to homepage if not logged in, or to default page if lacking permissions
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
      window.location.replace("/admin/all-tickets.html");
      return false;
    }

    return true;
  }

  // Hide group labels if all their items are hidden
  function hideEmptyGroups(nav) {
    const labels = Array.from(nav.querySelectorAll(".nav-group-label"));

    labels.forEach((label) => {
      let hasVisibleItem = false;
      let node = label.nextElementSibling;

      while (node && !node.classList.contains("nav-group-label")) {
        if (
          node.classList.contains("nav-item") &&
          node.style.display !== "none" &&
          !node.hidden
        ) {
          hasVisibleItem = true;
          break;
        }
        node = node.nextElementSibling;
      }

      label.hidden = !hasVisibleItem;
    });
  }

  // Show/hide sidebar links based on permissions, and hide group labels if all items are hidden
  function renderSidebar() {
    const rules = getRules();
    const nav = document.querySelector(".sidebar-nav");
    if (!nav) return;

    nav.querySelectorAll(".nav-item").forEach((link) => {
      let section = link.dataset.section;
      if (!section) {
        const href = String(link.getAttribute("href") || "").toLowerCase();
        const match = Object.keys(PATH_SECTIONS).find((key) =>
          href.includes(key),
        );
        section = match ? PATH_SECTIONS[match] : "";
        if (section) link.dataset.section = section;
      }

      if (section && !rules.includes(section)) {
        link.hidden = true;
        link.style.display = "none";
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
        el.textContent =
          "Technician console is optimized for larger screens. Please open on a desktop or tablet in landscape mode.";
      });

    if (document.title.toLowerCase().includes("admin")) {
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
        el.textContent = "Assigned Tickets";
      });

    document
      .querySelectorAll('.nav-item[data-section="tickets"]')
      .forEach((link) => {
        const span = link.querySelector("span");
        if (span) span.textContent = "Assigned Tickets";
        else {
          const icon = link.querySelector("i");
          link.innerHTML = "";
          if (icon) link.appendChild(icon);
          link.append(" Assigned Tickets");
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

  // Hide or disable ticket management features for technicians, and update descriptions accordingly
  function applyTicketPermissions() {
    if (getRole() !== "technician") return;

    relabelAssignedTickets();

    [
      "#deleteTicketsBtn",
      "#selectAllTickets",
      "#editAssignedTo",
      'label[for="editAssignedTo"]',
      "#editPriority",
      'label[for="editPriority"]',
    ].forEach((selector) => {
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

  // Hide or disable announcement management features for technicians, and update descriptions accordingly
  function applyAnnouncementPermissions() {
    if (getRole() !== "technician") return;

    applyConsoleLabels();

    [
      ".announcement-form-card",
      "#bulkActionBar",
      "#deleteConfirmationModal",
    ].forEach((selector) => {
      document.querySelectorAll(selector).forEach((el) => {
        el.hidden = true;
        el.style.display = "none";
      });
    });

    document
      .querySelectorAll(".item-actions, .btn-edit, .btn-delete")
      .forEach((el) => {
        el.hidden = true;
        el.style.display = "none";
      });

    const description = document.querySelector(
      '[data-translate="announcements_description"]',
    );
    if (description)
      description.textContent = "View support-related announcements";
  }

  // Determine if authentication headers should be attached based on the request URL, targeting API endpoints
  function shouldAttachHeaders(resource) {
    const url = typeof resource === "string" ? resource : resource?.url || "";
    return url.includes("/api/") || url.startsWith("/api/");
  }

  // Patch the global fetch function to automatically include authentication headers for API requests
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
    applyConsoleLabels,
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
  });

  document.addEventListener("languageReloaded", () => {
    setTimeout(applyConsoleLabels, 0);
  });
})();
