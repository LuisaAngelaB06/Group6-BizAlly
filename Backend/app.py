from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_cors import CORS
from Backend.extensions import db
from dotenv import load_dotenv
import os
from Backend.routes import register_routes
from Backend.routes.announcement_routes import announcement_bp
from Backend.socketio_instance import socketio
from Backend.routes.auth_routes import init_oauth
from Backend.routes.auth_routes import auth_bp
from Backend.routes.routing import routing_bp
from Backend.routes.system_routes import system_bp
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-this")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# 🌟 THE CORS FIX: Unlock the whole app so Socket.IO can breathe!
CORS(app, resources={r"/*": {
    "origins": [
        "http://127.0.0.1:5500", 
        "http://localhost:5500", 
        "https://group6-bizally.onrender.com"
    ],
    "allow_headers": ["Content-Type", "X-User-ID", "X-User-Role", "X-Technician-ID", "Authorization"]
}})

BASE_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_BACKEND_DIR, ".env")

load_dotenv(ENV_PATH)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.register_blueprint(announcement_bp, url_prefix="/api")
app.register_blueprint(routing_bp, url_prefix="/api")  
app.register_blueprint(system_bp, url_prefix="/api")
init_oauth(app)
socketio.init_app(app)
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
    technician_aliases = {
        "all-tickets.html",
        "notifications.html",
        "announcements.html",
        "preferences.html",
        "profile-settings.html",
    }

    if filename in technician_aliases:
        return send_from_directory(
            os.path.join(BASE_DIR, "src/pages/admin page"),
            filename
        )

    return send_from_directory(
        os.path.join(BASE_DIR, "src/pages/technician page"),
        filename
    )

print("Routes loaded!")

if __name__ == "__main__":
    socketio.run(app, debug=True)
