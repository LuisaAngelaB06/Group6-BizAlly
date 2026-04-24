from .auth_routes import auth_bp
from .ticket_routes import ticket_bp

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(ticket_bp, url_prefix="/api")