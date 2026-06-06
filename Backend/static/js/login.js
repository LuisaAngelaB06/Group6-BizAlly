console.log("login.js loaded");

const form = document.getElementById("modalLoginForm");
let isSubmitting = false;

if (form) {
  form.addEventListener(
    "submit",
    async function (e) {
      e.preventDefault();
      e.stopImmediatePropagation();

      if (isSubmitting) return;
      isSubmitting = true;

      const emailInput = document.getElementById("modalEmail");
      const passwordInput = document.getElementById("modalPassword");
      const loginBtn = document.getElementById("modalLoginBtn");
      const loadingText = document.getElementById("modalLoadingText");
      const loadingOverlay = document.getElementById("modalLoadingOverlay");
      const generalError = document.getElementById("loginGeneralError");

      if (generalError) generalError.textContent = "";

      const email = emailInput ? emailInput.value.trim() : "";
      const password = passwordInput ? passwordInput.value : "";

      if (!email || !password) {
        isSubmitting = false;
        if (generalError) generalError.textContent = "Please enter your email and password.";
        return;
      }

      try {
        if (loadingOverlay) loadingOverlay.style.display = "flex";
        if (loadingText) loadingText.textContent = "Authenticating...";
        if (loginBtn) loginBtn.disabled = true;

        const result = await loginUser(email, password);

        // 1. STANDARD LOGIN SUCCESS
        if (result.status === "success") {
          localStorage.setItem("userData", JSON.stringify(result.user));
          const role = (result.user.User_Type || result.user.user_type || result.user.role || "").toLowerCase();
          window.location.href = role === "technician" ? "/technician/all-tickets.html" : role === "admin" ? "/admin/dashboard" : "/user/dashboard";
          return;
        }

        // 2. 🌟 2FA CATCHER: This forces the OTP panel to open!
        if (result.status === "2fa_required") {
          if (loadingOverlay) loadingOverlay.style.display = "none";
          if (loginBtn) loginBtn.disabled = false;
          isSubmitting = false;

          // Tell the system we are logging in, not signing up
          window.isLogin2FA = true;
          window.pending2FAEmail = result.email || email;

          if (typeof window.showOtpPanel === 'function') {
             window.showOtpPanel(window.pending2FAEmail);
          }
          return;
        }

        // 3. FAILED LOGIN
        if (loadingOverlay) loadingOverlay.style.display = "none";
        if (loginBtn) loginBtn.disabled = false;
        isSubmitting = false;
        if (generalError) generalError.textContent = result.message || "Invalid email or password";
        
      } catch (error) {
        console.error("Login error:", error);
        if (loadingOverlay) loadingOverlay.style.display = "none";
        if (loginBtn) loginBtn.disabled = false;
        isSubmitting = false;
        if (generalError) generalError.textContent = "Server connection failed. Please try again.";
      }
    },
    true
  );
}