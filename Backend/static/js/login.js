console.log("login.js loaded");

const form = document.getElementById("modalLoginForm");

let isSubmitting = false;

if (form) {
  form.addEventListener(
    "submit",
    async function (e) {
      e.preventDefault();
      e.stopImmediatePropagation();

      if (isSubmitting) {
        console.log("Login already in progress...");
        return;
      }

      isSubmitting = true;

      const emailInput = document.getElementById("modalEmail");
      const passwordInput = document.getElementById("modalPassword");
      const loginBtn = document.getElementById("modalLoginBtn");
      const loadingText = document.getElementById("modalLoadingText");
      const loadingOverlay = document.getElementById("modalLoadingOverlay");

      const email = emailInput ? emailInput.value.trim() : "";
      const password = passwordInput ? passwordInput.value : "";

      if (!email || !password) {
        isSubmitting = false;
        alert("Please enter your email and password.");
        return;
      }

      try {
        if (loadingOverlay) loadingOverlay.style.display = "flex";
        if (loadingText) loadingText.textContent = "Authenticating...";
        if (loginBtn) loginBtn.disabled = true;

        const result = await loginUser(email, password);

        if (result.status === "success") {
          localStorage.setItem("userData", JSON.stringify(result.user));
          console.log("Login success:", result.user);

          const role = (
            result.user.User_Type ||
            result.user.user_type ||
            result.user.role ||
            ""
          ).toLowerCase();

          window.location.href =
            role === "admin" || role === "technician"
              ? "/admin/dashboard"
              : "/user/dashboard";

          return;
        }

        if (loadingOverlay) loadingOverlay.style.display = "none";
        if (loginBtn) loginBtn.disabled = false;
        isSubmitting = false;

        alert(result.message || "Invalid email or password");
      } catch (error) {
        console.error("Login error:", error);

        if (loadingOverlay) loadingOverlay.style.display = "none";
        if (loginBtn) loginBtn.disabled = false;
        isSubmitting = false;

        alert("Server connection failed. Please try again.");
      }
    },
    true,
  );
}
