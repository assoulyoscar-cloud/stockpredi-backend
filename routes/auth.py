from flask import Blueprint, request, jsonify, current_app
from supabase import create_client
from config import Config

auth_bp = Blueprint("auth", __name__)


def get_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)


def get_admin_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    # Rate limit: 3 signups par heure par IP
    limiter = current_app.limiter
    limiter.limit("3 per hour")(lambda: None)()

    body = request.get_json(silent=True) or {}
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400
    if len(password) < 8:
        return jsonify({"error": "Mot de passe minimum 8 caracteres"}), 400

    try:
        supabase = get_client()
        res = supabase.auth.sign_up({"email": email, "password": password})
        if not res.user:
            return jsonify({"error": "Inscription impossible"}), 400
        return jsonify({
            "message": "Verifiez votre email pour confirmer",
            "user_id": res.user.id
        }), 201
    except Exception as e:
        return jsonify({"error": "Inscription impossible", "detail": str(e)}), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    # Rate limit: 5 tentatives par minute par IP
    limiter = current_app.limiter
    limiter.limit("5 per minute")(lambda: None)()

    body = request.get_json(silent=True) or {}
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    try:
        supabase = get_client()
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if not res.session:
            return jsonify({"error": "Identifiants invalides"}), 401
        return jsonify({
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "user_id": res.user.id,
            "email": res.user.email
        }), 200
    except Exception as e:
        return jsonify({"error": "Identifiants invalides"}), 401


@auth_bp.route("/logout", methods=["POST"])
def logout():
    try:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            supabase = get_client()
            supabase.auth.sign_out()
    except Exception:
        pass
    return jsonify({"message": "Deconnecte"}), 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    body = request.get_json(silent=True) or {}
    refresh_token = body.get("refresh_token", "")
    if not refresh_token:
        return jsonify({"error": "Refresh token manquant"}), 400
    try:
        supabase = get_client()
        res = supabase.auth.refresh_session(refresh_token)
        return jsonify({
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token
        }), 200
    except Exception as e:
        return jsonify({"error": "Token invalide", "detail": str(e)}), 401
