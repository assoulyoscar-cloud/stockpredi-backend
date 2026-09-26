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
        print(f"routes/auth.py: Inscription impossible: {type(e).__name__}: {e}")
        return jsonify({"error": "Inscription impossible"}), 400


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
        print(f"routes/auth.py: Token invalide: {type(e).__name__}: {e}")
        return jsonify({"error": "Token invalide"}), 401


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Sends a password reset email to the user.
    
    Request body:
    {
        "email": "user@example.com"
    }
    
    Response:
    {
        "message": "Email de reinitialisation envoye",
        "email": "user@example.com"
    }
    """
    # Rate limit: 2 reset attempts par 15 minutes par IP
    limiter = current_app.limiter
    limiter.limit("2 per 15 minutes")(lambda: None)()

    body = request.get_json(silent=True) or {}
    email = body.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Email requis"}), 400

    try:
        supabase = get_client()
        # admin_reset_password_email n'existe pas dans supabase-py : l'AttributeError
        # etait avalee par le except -> 200 "lien envoye" sans aucun email.
        supabase.auth.reset_password_email(
            email, {"redirect_to": f"{Config.FRONTEND_URL}/reset-password"}
        )
        
        return jsonify({
            "message": "Email de reinitialisation envoye",
            "email": email
        }), 200
    except Exception as e:
        # Don't reveal if email exists or not (security) -- mais loguer pour Render
        print(f"forgot-password: envoi Supabase echoue: {type(e).__name__}: {e}")
        return jsonify({
            "message": "Si cet email existe, vous recevrez un lien de reinitialisation"
        }), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    Resets the user's password using the reset token from email.
    
    The flow:
    1. User receives reset email with token in URL
    2. Frontend captures token from URL parameter
    3. Frontend calls this endpoint with new password
    
    Request body:
    {
        "access_token": "token_from_email_link",
        "new_password": "newpassword123"
    }
    
    Response:
    {
        "message": "Mot de passe reinitialise avec succes"
    }
    """
    body = request.get_json(silent=True) or {}
    access_token = body.get("access_token", "").strip()
    new_password = body.get("new_password", "")

    if not access_token or not new_password:
        return jsonify({"error": "Token et nouveau mot de passe requis"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "Mot de passe minimum 8 caracteres"}), 400

    try:
        supabase = get_client()
        
        # Set the session with the reset token
        # This makes the user "logged in" for the password update
        response = supabase.auth.set_session(access_token, None)
        
        # Update password
        updated_user = supabase.auth.update_user(
            {"password": new_password}
        )
        
        return jsonify({
            "message": "Mot de passe reinitialise avec succes"
        }), 200
    except Exception as e:
        print(f"reset-password: {type(e).__name__}: {e}")
        return jsonify({
            "error": "Impossible de reinitialiser le mot de passe"
        }), 400
