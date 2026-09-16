from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from routes.auth import auth_bp
from routes.predictions import predictions_bp
from routes.user import user_bp
from routes.stripe_routes import stripe_bp
from routes.rgpd import rgpd_bp
from routes.export_routes import export_bp
from routes.occupations_routes import occupations_bp
from routes.archive import archive_bp

def create_app():
    app = Flask(__name__)

    # CORS — frontend uniquement
    CORS(app, origins=[Config.FRONTEND_URL, "http://localhost:3000"],
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
         automatic_options=True)

    # Rate limiting global
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://",
        headers_enabled=True
    )

    # Expose limiter pour les blueprints
    app.limiter = limiter

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(predictions_bp, url_prefix="/api/predictions")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(stripe_bp, url_prefix="/api/stripe")
    app.register_blueprint(export_bp)
    app.register_blueprint(occupations_bp)
    app.register_blueprint(rgpd_bp, url_prefix="/api/rgpd")
    app.register_blueprint(archive_bp)

    # Global preflight handler for all routes
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = make_response()
            response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.status_code = 200
            return response

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "stockpredi-backend"}), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Route introuvable"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Methode non autorisee"}), 405

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Trop de requetes", "detail": str(e.description)}), 429

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Erreur serveur interne"}), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=(Config.FLASK_ENV == "development"), host="0.0.0.0", port=5000)
# Build trigger: Wed Sep 16 17:14:37 UTC 2026
