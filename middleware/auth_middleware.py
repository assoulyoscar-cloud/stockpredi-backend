import os
from functools import wraps
from flask import request, jsonify
from supabase import create_client
from config import config

def get_supabase_admin():
    """Client admin avec service key pour verifier tokens."""
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

def auth_required(f):
    """Decorateur - verifie JWT Supabase sur chaque route protegee."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token manquant"}), 401

        token = auth_header.split(" ")[1]
        try:
            supabase = get_supabase_admin()
            user = supabase.auth.get_user(token)
            if not user or not user.user:
                return jsonify({"error": "Token invalide"}), 401
            request.user_id = user.user.id
            request.user_email = user.user.email
        except Exception as e:
            return jsonify({"error": "Token invalide", "detail": str(e)}), 401

        return f(*args, **kwargs)
    return decorated
