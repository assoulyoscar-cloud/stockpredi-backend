from flask import Blueprint, request, jsonify
from middleware.auth_middleware import auth_required
from models.user_store import ensure_user_row
from supabase import create_client
from config import Config

user_bp = Blueprint("user", __name__)


def get_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


@user_bp.route("/profile", methods=["GET"])
@auth_required
def get_profile():
    """GET /api/user/profile — profil utilisateur connecte."""
    supabase = get_client()
    try:
        ensure_user_row(supabase, request.user_id, request.user_email)
        res = supabase.table("users").select("*")             .eq("id", request.user_id).single().execute()
        return jsonify(res.data), 200
    except Exception as e:
        return jsonify({"error": "Profil introuvable", "detail": str(e)}), 404


@user_bp.route("/profile", methods=["PATCH"])
@auth_required
def update_profile():
    """PATCH /api/user/profile — mise a jour profil."""
    supabase = get_client()
    body = request.get_json(silent=True) or {}
    allowed = {"company_name", "plan", "preferences"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        return jsonify({"error": "Aucune donnee valide"}), 400
    try:
        res = supabase.table("users").update(updates)             .eq("id", request.user_id).execute()
        return jsonify(res.data[0] if res.data else {}), 200
    except Exception as e:
        return jsonify({"error": "Mise a jour impossible", "detail": str(e)}), 500


@user_bp.route("/predictions", methods=["GET"])
@auth_required
def get_user_predictions():
    """GET /api/user/predictions — historique previsions user."""
    supabase = get_client()
    limit = min(int(request.args.get("limit", 20)), 100)
    try:
        res = supabase.table("predictions")             .select("*")             .eq("user_id", request.user_id)             .order("created_at", desc=True)             .limit(limit)             .execute()
        return jsonify({"predictions": res.data, "count": len(res.data)}), 200
    except Exception as e:
        return jsonify({"error": "Historique introuvable", "detail": str(e)}), 500
