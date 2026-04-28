from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import os
from routes import register_routes

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

register_routes(app)

# Base project directory (parent of Backend)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# =========================
# MAIN PAGES (templates)
# =========================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "unified-auth-modal.html"
    )

@app.route("/admin/dashboard")
def admin_dash():
    return send_from_directory(os.path.join(BASE_DIR, "src/pages/admin page"), "index-admin.html")

@app.route("/user/dashboard")
def user_dash():
    return send_from_directory(os.path.join(BASE_DIR, "src/pages/user page"), "index-user.html")

@app.route("/quickfix-one")
def quickfix_one():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "quickfix-one.html"
    )

@app.route("/quickfix-two")
def quickfix_two():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "quickfix-two.html"
        )

@app.route("/quickfix-three")
def quickfix_three():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "quickfix-three.html"
    )

@app.route("/quickfix-four")
def quickfix_four():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "quickfix-four.html"
    )

@app.route("/privacy")
def privacy():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "privacy.html"
    )

@app.route("/cookies")
def cookies():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "cookies.html"
    )

@app.route("/terms")
def terms():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "terms.html"
    )

@app.route("/contact-us")
def contact_us():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "contact-us.html"
    )

@app.route("/about-us")
def about_us():
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/landing page"),
        "about-us.html"
    )



# =========================
# ADMIN PAGES
# =========================
@app.route("/admin/<path:filename>")
def admin_pages(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/admin page"),
        filename
    )

@app.route("/admin/dashboard")
def admin_dashboard():
    return send_from_directory(os.path.join(BASE_DIR, "src/pages/admin page"), "index-admin.html")

@app.route("/user/dashboard")
def user_dashboard():
    return send_from_directory(os.path.join(BASE_DIR, "src/pages/user page"), "index-user.html")
# =========================
# USER PAGES
# =========================
@app.route("/user/<path:filename>")
def user_pages(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/user page"),
        filename
    )

# =========================
# FRONTEND STYLES
# =========================
@app.route("/src/styles/<path:filename>")
def styles(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "Group6-BizAlly/src/styles"),
        filename
    )

# =========================
# FRONTEND SCRIPTS
# =========================
@app.route("/src/scripts/<path:filename>")
def scripts(filename):
    return send_from_directory(os.path.join(BASE_DIR, "src/scripts"), filename)

# =========================
# FRONTEND ASSETS (images)
# =========================
@app.route("/src/assets/<path:filename>")
def assets(filename):
    return send_from_directory(os.path.join(BASE_DIR, "src/assets"), filename)

# =========================
# LOGIN CSS
# =========================
@app.route("/css/<path:filename>")
def serve_login_css(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "src/styles"),
        filename
    )

# =========================
# GLOBAL STYLES
# =========================
@app.route("/styles/<path:filename>")
def serve_styles(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "src/styles"),
        filename
    )

# =========================
# GLOBAL SCRIPTS
# =========================
@app.route("/scripts/<path:filename>")
def serve_scripts(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "src/scripts"),
        filename
    )

# =========================
# ASSETS (images)
# =========================
@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "src/assets"),
        filename
    )

# =========================
# TECHNICIAN PAGES
# =========================
@app.route("/technician/<path:filename>")
def technician_pages(filename):
    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/technician page"),
        filename
    )



print("Routes loaded!")

if __name__ == "__main__":
    app.run(debug=True)