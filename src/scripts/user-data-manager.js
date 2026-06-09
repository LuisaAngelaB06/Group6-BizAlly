// --- UNIFIED GLOBAL BACKGROUND TRACKERS (RUNS ONCE PER PAGE REFRESH) ---
if (typeof window.globalHeartbeatFired === "undefined") {
  window.globalHeartbeatFired = true;

  // ==========================================
  // GLOBAL STATE FOR RED-DOT SYSTEM
  // ==========================================
  window.redDotSystemState = {
    // Announcement system state
    announcementSocketListenersAttached: false,
    announcementLastCheckTime: 0,
    announcementCheckInProgress: false,
    announcementRetryCount: 0,
    announcementMaxRetries: 3,
    
    // Profile completeness state
    profileCheckInProgress: false,
    profileLastCheckTime: 0,
    profileRetryCount: 0,
    profileMaxRetries: 3,

    // 🌟 Notification system state added cleanly
    notificationCheckInProgress: false,
    notificationLastCheckTime: 0,
    notificationRetryCount: 0,
    notificationMaxRetries: 3,
  };

  // ==========================================
  // HELPER: Extract user ID from multiple possible fields
  // ==========================================
  function extractUserId() {
    const userData = JSON.parse(sessionStorage.getItem("userData") || "{}");
    return userData.user_id || userData.id || userData.User_ID || userData.Customer_ID;
  }

  // ==========================================
  // HELPER: build API URL safely (avoids duplicate /api segments)
  // ==========================================
  function buildApiUrl(path) {
    // path should start with '/'
    const p = String(path || '');
    const apiPath = p.startsWith('/') ? p : `/${p}`;
    const base = (window.API_BASE_URL || '').replace(/\/$/, '');

    // If base already ends with '/api' and apiPath starts with '/api', avoid duplication
    if (base.match(/\/api$/) && apiPath.startsWith('/api')) {
      return `${base}${apiPath.slice(4)}`; // remove leading /api from path
    }

    // If base empty, return apiPath
    if (!base) return apiPath;

    return `${base}${apiPath}`;
  }

  // ==========================================
  // HELPER: Show red dot
  // ==========================================
  function showRedDot(dot) {
    if (dot) {
      dot.classList.remove("hidden");
      dot.style.display = "inline-block";
    }
  }

  // ==========================================
  // HELPER: Hide red dot
  // ==========================================
  function hideRedDot(dot) {
    if (dot) {
      dot.classList.add("hidden");
      dot.style.display = "none";
    }
  }

  // ==========================================
  // PROFILE COMPLETENESS CHECK (GLOBAL)
  // ==========================================
  async function checkProfileCompleteness() {
    const userData = JSON.parse(sessionStorage.getItem("userData") || "{}");
    const userId = extractUserId();

    if (!userId) {
      console.warn("[RedDot] No user ID found for profile check");
      return;
    }

    // Prevent duplicate simultaneous checks
    if (window.redDotSystemState.profileCheckInProgress) {
      console.debug("[RedDot] Profile check already in progress, skipping");
      return;
    }

    // Rate limit: don't check more than once per 3 seconds
    const now = Date.now();
    if (now - window.redDotSystemState.profileLastCheckTime < 3000) {
      console.debug("[RedDot] Profile check rate limited, skipping");
      return;
    }

    window.redDotSystemState.profileCheckInProgress = true;
    window.redDotSystemState.profileLastCheckTime = now;

    try {
      const response = await fetch(buildApiUrl(`/api/auth/user/profile/complete/${userId}`));
      const result = await response.json();

      if (response.ok && result.status === "success") {
        const isComplete = result.is_profile_complete;
        const normalized = isComplete === true || isComplete === "true" || isComplete === 1;

        // Update localStorage
        userData.is_profile_complete = normalized;
        if (result.profile_pic_url) {
          userData.profile_pic_url = result.profile_pic_url;
        }
        localStorage.setItem("userData", JSON.stringify(userData));

        // Update all profileRedDot instances on the page
        const profileDots = document.querySelectorAll("#profileRedDot");
        profileDots.forEach(dot => {
          if (normalized) {
            hideRedDot(dot);
          } else {
            showRedDot(dot);
          }
        });

        console.log(`[RedDot] Profile completeness: ${normalized}, updated ${profileDots.length} dots`);

        // Refresh avatar if available
        if (window.userDataManager && typeof window.userDataManager.updateHeaderAvatar === "function") {
          window.userDataManager.updateHeaderAvatar();
        }

        // Reset retry count on success
        window.redDotSystemState.profileRetryCount = 0;
      } else {
        throw new Error(`API returned status: ${result.status}`);
      }
    } catch (e) {
      console.error("[RedDot] Profile check failed:", e.message);

      // Show profile dot on error (safer assumption)
      const profileDots = document.querySelectorAll("#profileRedDot");
      profileDots.forEach(dot => showRedDot(dot));

      // Retry logic
      if (window.redDotSystemState.profileRetryCount < window.redDotSystemState.profileMaxRetries) {
        window.redDotSystemState.profileRetryCount++;
        const backoffMs = Math.min(1000 * Math.pow(2, window.redDotSystemState.profileRetryCount), 10000);
        console.log(`[RedDot] Retrying profile check in ${backoffMs}ms`);
        setTimeout(checkProfileCompleteness, backoffMs);
      }
    } finally {
      window.redDotSystemState.profileCheckInProgress = false;
    }
  }

  // ==========================================
  // WAIT FOR ELEMENT WITH RETRY
  // ==========================================
  function waitForElement(selector, callback, maxAttempts = 50) {
    let attempts = 0;

    function attempt() {
      const element = document.querySelector(selector);

      if (element) {
        callback(element);
      } else if (attempts < maxAttempts) {
        attempts++;
        setTimeout(attempt, 100);
      }
    }

    attempt();
  }

  // ==========================================
  // ROBUST ANNOUNCEMENT RED DOT CHECKER (GLOBAL)
  // ==========================================
  async function checkNewAnnouncements(isRetry = false) {
    const userId = extractUserId();

    if (!userId) {
      console.warn("[RedDot] No user ID found for announcement check");
      return;
    }

    // Prevent duplicate simultaneous checks
    if (window.redDotSystemState.announcementCheckInProgress) {
      console.debug("[RedDot] Announcement check already in progress, skipping");
      return;
    }

    // Rate limit: don't check more than once per 3 seconds (unless retry)
    const now = Date.now();
    if (!isRetry && now - window.redDotSystemState.announcementLastCheckTime < 3000) {
      console.debug("[RedDot] Announcement check rate limited, skipping");
      return;
    }

    window.redDotSystemState.announcementCheckInProgress = true;
    window.redDotSystemState.announcementLastCheckTime = now;

    try {
      const response = await fetch(buildApiUrl(`/api/user/announcements/unread/${userId}`));

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const unread = await response.json();

      // Update all navRedDot instances on the page
      const announcementDots = document.querySelectorAll("#navRedDot");
      const hasUnread = Array.isArray(unread) && unread.length > 0;

      announcementDots.forEach(dot => {
        if (hasUnread) {
          showRedDot(dot);
        } else {
          hideRedDot(dot);
        }
      });

      console.log(`[RedDot] Announcements check: ${hasUnread ? unread.length + " unread" : "none"}, updated ${announcementDots.length} dots`);

      // Reset retry count on success
      window.redDotSystemState.announcementRetryCount = 0;
    } catch (e) {
      console.error("[RedDot] Announcement check failed:", e.message);

      // Retry logic
      if (window.redDotSystemState.announcementRetryCount < window.redDotSystemState.announcementMaxRetries) {
        window.redDotSystemState.announcementRetryCount++;
        const backoffMs = Math.min(1000 * Math.pow(2, window.redDotSystemState.announcementRetryCount), 10000);
        console.log(`[RedDot] Retrying announcement check in ${backoffMs}ms (attempt ${window.redDotSystemState.announcementRetryCount})`);
        setTimeout(() => checkNewAnnouncements(true), backoffMs);
      } else {
        console.warn("[RedDot] Max retries exceeded for announcement check");
        window.redDotSystemState.announcementRetryCount = 0;
      }
    } finally {
      window.redDotSystemState.announcementCheckInProgress = false;
    }
  }

  // ==========================================
  // 🌟 ROBUST NOTIFICATION RED DOT CHECKER (GLOBAL)
  // ==========================================
  async function checkNewNotifications(isRetry = false) {
    const userId = extractUserId();

    if (!userId) {
      console.warn("[RedDot] No user ID found for notification check");
      return;
    }

    // Prevent duplicate simultaneous checks
    if (window.redDotSystemState.notificationCheckInProgress) {
      console.debug("[RedDot] Notification check already in progress, skipping");
      return;
    }

    // Rate limit: don't check more than once per 3 seconds (unless retry)
    const now = Date.now();
    if (!isRetry && now - window.redDotSystemState.notificationLastCheckTime < 3000) {
      console.debug("[RedDot] Notification check rate limited, skipping");
      return;
    }

    window.redDotSystemState.notificationCheckInProgress = true;
    window.redDotSystemState.notificationLastCheckTime = now;

    try {
      const response = await fetch(buildApiUrl(`/api/notifications/user/${userId}`));

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const notifications = await response.json();

      // Find all matching notification dot instances across your layout sidebar view
      const notificationDots = document.querySelectorAll("#notifRedDot");
      
      // Safe validation supports multiple boolean combinations from database fields cleanly
      const hasUnread = Array.isArray(notifications) && notifications.some(notif => 
        notif.unread == true || 
        notif.unread === 1 || 
        notif.unread === "true" ||
        notif.is_read == false ||
        notif.is_read === 0 ||
        notif.is_read === "false"
      );

      notificationDots.forEach(dot => {
        if (hasUnread) {
          showRedDot(dot);
        } else {
          hideRedDot(dot);
        }
      });

      console.log(`[RedDot] Notifications check: ${hasUnread ? "unread items found" : "none"}, updated ${notificationDots.length} dots`);

      // Reset retry count on success
      window.redDotSystemState.notificationRetryCount = 0;
    } catch (e) {
      console.error("[RedDot] Notification check failed:", e.message);

      // Retry backoff logic cascades safely if server experiences downtime
      if (window.redDotSystemState.notificationRetryCount < window.redDotSystemState.notificationMaxRetries) {
        window.redDotSystemState.notificationRetryCount++;
        const backoffMs = Math.min(1000 * Math.pow(2, window.redDotSystemState.notificationRetryCount), 10000);
        console.log(`[RedDot] Retrying notification check in ${backoffMs}ms (attempt ${window.redDotSystemState.notificationRetryCount})`);
        setTimeout(() => checkNewNotifications(true), backoffMs);
      } else {
        console.warn("[RedDot] Max retries exceeded for notification check");
        window.redDotSystemState.notificationRetryCount = 0;
      }
    } finally {
      window.redDotSystemState.notificationCheckInProgress = false;
    }
  }

  // ==========================================
  // SETUP SOCKET.IO LISTENERS (ROBUST)
  // ==========================================
  function setupAnnouncementSocketListeners() {
    // Prevent duplicate listener attachment
    if (window.redDotSystemState.announcementSocketListenersAttached) {
      console.debug("[RedDot] Socket listeners already attached");
      return;
    }

    if (!window.socket) {
      console.warn("[RedDot] Socket.IO not available yet");
      return;
    }

    console.log("[RedDot] Attaching Socket.IO listeners for announcements...");

    // Remove any old listeners first (safety)
    window.socket.off("new_announcement");
    window.socket.off("announcement_updated");
    window.socket.off("announcement_deleted");
    window.socket.off("ticket_updated");
    window.socket.off("ticket_assigned");
    window.socket.off("connect");
    window.socket.off("disconnect");

    // NEW ANNOUNCEMENT
    window.socket.on("new_announcement", () => {
      console.log("[RedDot] Socket event: new_announcement");
      checkNewAnnouncements();
      if (typeof showToast === "function") {
        showToast("New announcement received.", "success");
      }
    });

    // ANNOUNCEMENT UPDATED
    window.socket.on("announcement_updated", () => {
      console.log("[RedDot] Socket event: announcement_updated");
      checkNewAnnouncements();
    });

    // ANNOUNCEMENT DELETED
    window.socket.on("announcement_deleted", () => {
      console.log("[RedDot] Socket event: announcement_deleted");
      checkNewAnnouncements();
    });

    // 🌟 REALTIME TICKET STATUS MODIFICATION UPDATES DETECTION CHANNELS
    window.socket.on("ticket_updated", () => {
      console.log("[RedDot] Socket event: ticket_updated. Refreshing alerts...");
      checkNewNotifications();
    });

    window.socket.on("ticket_assigned", () => {
      console.log("[RedDot] Socket event: ticket_assigned. Refreshing alerts...");
      checkNewNotifications();
    });

    // RECONNECTION HANDLER
    window.socket.on("connect", () => {
      console.log("[RedDot] Socket reconnected, re-checking databases...");
      window.redDotSystemState.announcementRetryCount = 0;
      window.redDotSystemState.notificationRetryCount = 0;
      checkNewAnnouncements();
      checkNewNotifications();
    });

    window.socket.on("disconnect", () => {
      console.log("[RedDot] Socket disconnected");
    });

    window.redDotSystemState.announcementSocketListenersAttached = true;
    console.log("[RedDot] Socket listeners attached successfully");
  }

  // ==========================================
  // MONITOR SOCKET.IO AVAILABILITY
  // ==========================================
  function monitorSocketIO() {
    if (window.socket && !window.redDotSystemState.announcementSocketListenersAttached) {
      console.log("[RedDot] Socket.IO detected, setting up listeners");
      setupAnnouncementSocketListeners();
    } else if (!window.socket) {
      // Check again in 500ms
      setTimeout(monitorSocketIO, 500);
    }
  }

  // ==========================================
  // TOAST CONTAINER + SHARED SHOWTOAST UTILITY
  // ==========================================
  function ensureToastContainer() {
    let toast = document.getElementById('toast');
    if (toast) return toast;

    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
    return toast;
  }

  function ensureSharedToast() {
    ensureToastContainer();

    if (typeof window.showToast === 'function') {
      return;
    }

    window.showToast = function (message, type = 'success') {
      const toast = ensureToastContainer();
      toast.textContent = message;
      toast.className = `toast ${type}`;
      toast.classList.add('show');

      setTimeout(() => {
        toast.classList.remove('show');
      }, 3000);
    };
  }

  // ==========================================
  // SUBMIT TICKET GUARD (BLOCK IF PROFILE INCOMPLETE)
  // ==========================================
  function setupSubmitTicketGuard() {
    const submitTicketLink = document.querySelector('a[data-section="submit-ticket"]');

    if (!submitTicketLink) {
      console.debug("[RedDot] Submit Ticket link not found on this page");
      return;
    }

    submitTicketLink.addEventListener("click", function (e) {
      const userData = JSON.parse(sessionStorage.getItem("userData") || "{}");
      const isComplete = userData.is_profile_complete === true;

      if (!isComplete) {
        e.preventDefault();

        if (typeof showToast === "function") {
          showToast("Please complete your profile before submitting a ticket.", "error");
        } else {
          alert("Please complete your profile before submitting a ticket.");
        }

        setTimeout(() => {
          window.location.href = "/user/profile-settings.html";
        }, 1200);
      }
    });
  }

  // ==========================================
  // MOBILE SIDEBAR TOGGLE (SHARED GLOBAL NAV)
  // ==========================================
  function setupMobileSidebarToggle() {
    const menuToggle = document.getElementById("menuToggle");
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    if (!menuToggle || !sidebar || !overlay) {
      console.debug("[Sidebar] Mobile sidebar elements not found on this page");
      return;
    }

    const freshToggle = menuToggle.cloneNode(true);
    const freshOverlay = overlay.cloneNode(true);
    menuToggle.parentNode.replaceChild(freshToggle, menuToggle);
    overlay.parentNode.replaceChild(freshOverlay, overlay);

    const openSidebar = () => {
      sidebar.classList.add("open");
      freshOverlay.classList.add("active");
      freshToggle.setAttribute("aria-expanded", "true");
      freshToggle.setAttribute("aria-label", "Close sidebar");
      freshToggle.innerHTML = '<i class="fas fa-times" aria-hidden="true"></i>';
      document.body.classList.add("sidebar-open");
    };

    const closeSidebar = () => {
      sidebar.classList.remove("open");
      freshOverlay.classList.remove("active");
      freshToggle.setAttribute("aria-expanded", "false");
      freshToggle.setAttribute("aria-label", "Open sidebar");
      freshToggle.innerHTML = '<i class="fas fa-bars" aria-hidden="true"></i>';
      document.body.classList.remove("sidebar-open");
    };

    const toggleSidebar = () => {
      if (sidebar.classList.contains("open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    };

    freshToggle.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      toggleSidebar();
    });

    freshOverlay.addEventListener("click", closeSidebar);

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && sidebar.classList.contains("open")) {
        closeSidebar();
      }
    });

    sidebar.querySelectorAll(".sidebar-nav a").forEach(link => {
      link.addEventListener("click", function () {
        if (sidebar.classList.contains("open")) {
          closeSidebar();
        }
      });
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth > 900 || document.body.classList.contains("mobile-block-active")) {
        closeSidebar();
      }
    });

    console.log("[Sidebar] Mobile sidebar toggle initialized");
  }

  // ==========================================
  // GLOBAL INITIALIZATION - RUNS ON EVERY PAGE LOAD
  // ==========================================
  const executeGlobalInitializations = () => {
    console.log("[RedDot] Executing global red-dot initializations");

    // Initialize user display
    if (window.userDataManager && typeof window.userDataManager.initializeUserDisplay === "function") {
      window.userDataManager.initializeUserDisplay();
    }

    // Run profile completeness check immediately (works on all pages)
    console.log("[RedDot] Starting profile completeness check");
    checkProfileCompleteness();

    // Run announcement checker immediately (works on all pages)
    console.log("[RedDot] Starting announcement check");
    checkNewAnnouncements();

    // 🌟 Run background alert checker immediately on load across all system dashboards
    console.log("[RedDot] Starting notification check");
    checkNewNotifications();

    // Start monitoring for Socket.IO availability
    monitorSocketIO();

    // Try to setup listeners if Socket.IO is already available
    setupAnnouncementSocketListeners();

    // Ensure user toast system is available
    ensureSharedToast();

    // Setup submit ticket guard on every page
    setupSubmitTicketGuard();

    // Setup mobile sidebar toggle for user navigation
    setupMobileSidebarToggle();

    console.log("[RedDot] Global initializations complete");
  };

  // ==========================================
  // DOM READY
  // ==========================================
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", executeGlobalInitializations);
  } else {
    executeGlobalInitializations();
  }

  // ==========================================
  // GLOBAL CLEANUP ON PAGE UNLOAD
  // ==========================================
  window.addEventListener("beforeunload", () => {
    // Reset state for next page load
    window.redDotSystemState.announcementCheckInProgress = false;
    window.redDotSystemState.profileCheckInProgress = false;
    window.redDotSystemState.notificationCheckInProgress = false;
  });
}

// Expose helpers for debugging / test harness
/* istanbul ignore next */
if (typeof window !== 'undefined') {
  window.__redDot_checkProfile = window.__redDot_checkProfile || function () {
    try { return checkProfileCompleteness(); } catch (e) { console.warn('profile check unavailable', e); }
  };

  window.__redDot_checkAnnouncements = window.__redDot_checkAnnouncements || function () {
    try { return checkNewAnnouncements(); } catch (e) { console.warn('announcement check unavailable', e); }
  };

  window.__redDot_checkNotifications = window.__redDot_checkNotifications || function () {
    try { return checkNewNotifications(); } catch (e) { console.warn('notification check unavailable', e); }
  };

  window.__redDot_setupSocket = window.__redDot_setupSocket || function () {
    try { return setupAnnouncementSocketListeners(); } catch (e) { console.warn('setup socket unavailable', e); }
  };

  window.__redDot_state = window.__redDot_state || window.redDotSystemState;
  
  window.__redDot_extractUserId = window.__redDot_extractUserId || function () {
    try { return extractUserId(); } catch (e) { console.warn('extractUserId unavailable', e); }
  };
}

// ==========================================
// 🕒 UNIVERSAL IDLE SESSION MONITOR (TEST MODE)
// ==========================================
(function() {
    const sessionTimeoutMinutes = 60; 
    let lastActivityTime = Date.now();
    let activityInterval;

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

        // Check the clock every 5 seconds for precise testing
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
        
        // 🌟 Trigger the red text on the login page!
        sessionStorage.setItem("show_timeout_modal", "true");
        
        window.location.replace("/"); 
    }

    // Start monitor if logged in
    if (sessionStorage.getItem("userData")) {
        startActivityMonitor();
    }
})();