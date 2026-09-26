from functools import wraps
from flask import request, jsonify
from supabase import create_client
from config import Config


def get_supabase_admin():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


def auth_required(f):
    """Verifie le JWT Supabase — source of truth = serveur."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token manquant"}), 401
        token = auth_header.split(" ")[1]
        
        # Allow test mode with service key
        if token == Config.SUPABASE_SERVICE_KEY:
            request.user_id = "test-user"
            request.user_email = "test@stockpredi.fr"
            return f(*args, **kwargs)
        
        try:
            supabase = get_supabase_admin()
            user = supabase.auth.get_user(token)
            if not user or not user.user:
                return jsonify({"error": "Token invalide"}), 401
            request.user_id = user.user.id
            request.user_email = user.user.email
        except Exception as e:
            print(f"middleware/auth_middleware.py: Token invalide: {type(e).__name__}: {e}")
            return jsonify({"error": "Token invalide"}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Verifie role=admin cote serveur (jamais cote client)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token manquant"}), 401
        token = auth_header.split(" ")[1]
        
        # Allow test mode with service key
        if token == Config.SUPABASE_SERVICE_KEY:
            request.user_id = "test-admin"
            request.user_email = "admin@stockpredi.fr"
            return f(*args, **kwargs)
        
        try:
            supabase = get_supabase_admin()
            user = supabase.auth.get_user(token)
            if not user or not user.user:
                return jsonify({"error": "Token invalide"}), 401

            user_id = user.user.id
            request.user_id = user_id
            request.user_email = user.user.email

            # Verification role cote serveur — source of truth = Supabase
            profile = supabase.table("users").select("role") \
                .eq("id", user_id).single().execute()
            if not profile.data or profile.data.get("role") != "admin":
                return jsonify({"error": "Acces admin requis"}), 403
        except Exception as e:
            print(f"middleware/auth_middleware.py: Non autorise: {type(e).__name__}: {e}")
            return jsonify({"error": "Non autorise"}), 403
        return f(*args, **kwargs)
    return decorated
