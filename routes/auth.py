from flask import Blueprint, request, jsonify
from supabase import create_client
from config import config

auth_bp = Blueprint("auth", __name__)

def get_supabase():
    return create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)

def get_supabase_admin():
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()

    if not email or not password or not name:
        return jsonify({"error": "email, password et name requis"}), 400
    if len(password) < 8:
        return jsonify({"error": "Mot de passe minimum 8 caracteres"}), 400

    try:
        supabase = get_supabase()
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": name}}
        })
        if res.user:
            # Creer profil dans table users
            try:
                admin = get_supabase_admin()
                admin.table("users").insert({
                    "id": res.user.id,
                    "email": email,
                    "full_name": name,
                    "subscription_active": False
                }).execute()
            except Exception:
                pass  # Table users peut ne pas exister encore

            token = res.session.access_token if res.session else None
            return jsonify({
                "message": "Inscription reussie ! Verifiez votre email.",
                "user_id": res.user.id,
                "token": token
            }), 201
        return jsonify({"error": "Inscription echouee"}), 400
    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower():
            return jsonify({"error": "Email deja utilise"}), 409
        return jsonify({"error": msg}), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email et password requis"}), 400

    try:
        supabase = get_supabase()
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if res.session:
            return jsonify({
                "message": "Connecte",
                "user_id": res.user.id,
                "email": res.user.email,
                "token": res.session.access_token,
                "refresh_token": res.session.refresh_token
            }), 200
        return jsonify({"error": "Identifiants incorrects"}), 401
    except Exception as e:
        return jsonify({"error": "Identifiants incorrects"}), 401


@auth_bp.route("/logout", methods=["POST"])
def logout():
    try:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            supabase = get_supabase()
            supabase.auth.sign_out()
    except Exception:
        pass
    return jsonify({"message": "Deconnecte"}), 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        return jsonify({"error": "refresh_token requis"}), 400
    try:
        supabase = get_supabase()
        res = supabase.auth.refresh_session(refresh_token)
        return jsonify({
            "token": res.session.access_token,
            "refresh_token": res.session.refresh_token
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401
