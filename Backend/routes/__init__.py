from .auth_routes import auth_bp
from .analytics_routes import analytics_bp
from .ticket_routes import ticket_bp
from .contact_routes import contact_bp

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(ticket_bp, url_prefix="/api")
    app.register_blueprint(analytics_bp, url_prefix="/api")
    app.register_blueprint(contact_bp, url_prefix="/api")
