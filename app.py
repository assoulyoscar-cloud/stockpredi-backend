from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from routes.auth import auth_bp
from routes.rgpd import rgpd_bp
from routes.predictions import predictions_bp
from routes.user import user_bp
from routes.stripe_routes import stripe_bp
from routes.contact import contact_bp
from routes.stats import stats_bp
from routes.admin import admin_bp

def create_app():
    app = Flask(__name__)

    # CORS — frontend prod + previews Vercel du projet + dev local.
    # Regex ancree (Flask-CORS fait re.match) : stockpredi-<hash>-<scope>.vercel.app
    # et stockpredi-git-<branche>-<scope>.vercel.app, pas n'importe quel *.vercel.app.
    CORS(app, origins=[Config.FRONTEND_URL, "https://stockpredi.vercel.app",
                       r"^https://stockpredi-[a-z0-9-]+\.vercel\.app$",
                       "http://localhost:3000"],
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])

    # Preflight CORS : repondre 200 avant toute vue / auth_required.
    # Les routes declarent methods=[..., "OPTIONS"], donc sans ce hook la vue
    # s'executait sur le preflight -> 401 "Token manquant" -> "Failed to fetch".
    # Flask-CORS ajoute les en-tetes Access-Control-* dans after_request.
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            return app.make_default_options_response()

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
    app.register_blueprint(rgpd_bp, url_prefix="/api/rgpd")
    app.register_blueprint(contact_bp, url_prefix="/api/contact")
    app.register_blueprint(stats_bp, url_prefix="/api/stats")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    
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

    # Security Headers
    @app.after_request
    def set_security_headers(response):
        """Set security headers on all responses."""
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        return response

    # Scheduler pour exporter stats vers Google Drive
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from tasks.export_to_drive import export_stats_to_drive
        import atexit
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=export_stats_to_drive,
            trigger="cron",
            day_of_week="6",
            hour=22,
            minute=0,
            id='export_stats_weekly',
            name='Export stats to Google Drive weekly',
            replace_existing=True
        )
        scheduler.start()
        print("✅ APScheduler started successfully")
        atexit.register(lambda: scheduler.shutdown())
    except Exception as e:
        print(f"❌ Scheduler error: {e}")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=(Config.FLASK_ENV == "development"), host="0.0.0.0", port=5000)