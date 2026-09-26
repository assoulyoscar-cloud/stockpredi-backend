import logging

from flask import Blueprint, request, jsonify
from middleware.auth_middleware import auth_required
from models.user_store import ensure_user_row
from supabase import create_client
from config import Config

user_bp = Blueprint("user", __name__)
logger = logging.getLogger(__name__)


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
        print(f"routes/user.py: Profil introuvable: {type(e).__name__}: {e}")
        return jsonify({"error": "Profil introuvable"}), 404


@user_bp.route("/profile", methods=["PATCH", "OPTIONS"])
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
        print(f"routes/user.py: Mise a jour impossible: {type(e).__name__}: {e}")
        return jsonify({"error": "Mise a jour impossible"}), 500


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
        print(f"routes/user.py: Historique introuvable: {type(e).__name__}: {e}")
        return jsonify({"error": "Historique introuvable"}), 500


# ===== Secteur d'activite (memes cles que le dropdown du Dashboard) =====

VALID_SECTORS = ["general", "restaurant", "epicerie", "boulangerie",
                 "pepiniere", "boutique", "bureau_etude"]


@user_bp.route("/sector", methods=["POST"])
@auth_required
def set_active_sector():
    """POST /api/user/sector — Body: { "sector": "restaurant" }"""
    body = request.get_json(silent=True) or {}
    sector = str(body.get("sector", "")).strip().lower()
    if sector not in VALID_SECTORS:
        return jsonify({"error": f"Secteur invalide. Valeurs : {', '.join(VALID_SECTORS)}"}), 400
    supabase = get_client()
    try:
        ensure_user_row(supabase, request.user_id, request.user_email)
        supabase.table("users").update({"active_sector": sector})             .eq("id", request.user_id).execute()
        return jsonify({"active_sector": sector}), 200
    except Exception as e:
        logger.error("set_active_sector: %s", e)
        print(f"routes/user.py: Secteur non enregistre: {type(e).__name__}: {e}")
        return jsonify({"error": "Secteur non enregistre"}), 500


@user_bp.route("/sector", methods=["GET"])
@auth_required
def get_active_sector():
    """GET /api/user/sector — secteur memorise (defaut : general)."""
    supabase = get_client()
    try:
        res = supabase.table("users").select("active_sector")             .eq("id", request.user_id).limit(1).execute()
        row = (res.data or [{}])[0]
        return jsonify({"active_sector": row.get("active_sector") or "general"}), 200
    except Exception as e:
        logger.error("get_active_sector: %s", e)
        print(f"routes/user.py: Secteur introuvable: {type(e).__name__}: {e}")
        return jsonify({"error": "Secteur introuvable"}), 500
