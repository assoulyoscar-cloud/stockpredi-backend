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
        res = supabase.table("users").select("*").eq("id", request.user_id).single().execute()
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
        res = supabase.table("users").update(updates).eq("id", request.user_id).execute()
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
        res = supabase.table("predictions").select("*").eq("user_id", request.user_id).order("created_at", desc=True).limit(limit).execute()
        return jsonify({"predictions": res.data, "count": len(res.data)}), 200
    except Exception as e:
        return jsonify({"error": "Historique introuvable", "detail": str(e)}), 500


@user_bp.route("/export", methods=["GET"])
@auth_required
def export_data():
    """GET /api/user/export — RGPD Article 20: Droit à la portabilité.
    Exporte TOUTES les données utilisateur en JSON.
    """
    supabase = get_client()
    user_id = request.user_id
    try:
        # Récupérer le profil
        user_res = supabase.table("users").select("*").eq("id", user_id).single().execute()
        user_data = user_res.data if user_res.data else {}

        # Récupérer toutes les prédictions
        pred_res = supabase.table("predictions").select("*").eq("user_id", user_id).execute()
        predictions = pred_res.data if pred_res.data else []

        # Récupérer tous les scénarios
        scen_res = supabase.table("saved_scenarios").select("*").eq("user_id", user_id).execute()
        scenarios = scen_res.data if scen_res.data else []

        # Construire l'export
        export_data = {
            "export_date": __import__('datetime').datetime.utcnow().isoformat(),
            "user_profile": user_data,
            "predictions": predictions,
            "scenarios": scenarios,
            "note": "Cet export contient TOUTES vos données personnelles dans StockPredi"
        }

        return jsonify(export_data), 200
    except Exception as e:
        return jsonify({"error": "Export impossible", "detail": str(e)}), 500


@user_bp.route("/delete-account", methods=["DELETE"])
@auth_required
def delete_account():
    """DELETE /api/user/delete-account — RGPD Article 17: Droit à l'oubli.
    Supprime TOUTES les données utilisateur.
    """
    supabase = get_client()
    user_id = request.user_id
    try:
        # Log d'audit (optionnel — pour traçabilité)
        import datetime
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "action": "account_deletion",
            "user_id": user_id,
            "status": "initiated"
        }
        # TODO: Envoyer ce log à un système d'audit

        # Supprimer toutes les prédictions
        supabase.table("predictions").delete().eq("user_id", user_id).execute()

        # Supprimer tous les scénarios sauvegardés
        supabase.table("saved_scenarios").delete().eq("user_id", user_id).execute()

        # Supprimer le profil utilisateur
        supabase.table("users").delete().eq("id", user_id).execute()

        return jsonify({
            "success": True,
            "message": "Compte et toutes les données supprimés définitivement"
        }), 200
    except Exception as e:
        return jsonify({"error": "Suppression impossible", "detail": str(e)}), 500



