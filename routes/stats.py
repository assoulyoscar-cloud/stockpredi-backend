from flask import Blueprint, jsonify, request
import os
from middleware.auth_middleware import auth_required
from supabase import create_client
from config import Config
from datetime import datetime, timezone

stats_bp = Blueprint("stats", __name__)

def get_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

@stats_bp.route("/export", methods=["GET"])
def export_stats():
    """Retourne stats (scheduler ou debug)."""
    
    # Accepte soit JWT valide, soit backend token
    auth_header = request.headers.get("Authorization", "").replace("Bearer ", "")
    backend_token = os.getenv("BACKEND_AUTH_TOKEN", "")
    
    # Si c'est le backend token, OK
    if auth_header == backend_token and backend_token:
        pass
    else:
        # Sinon faut un JWT valide
        @auth_required
        def dummy():
            pass
        dummy()
    
    supabase = get_client()
    try:
        all_users = supabase.table("users").select("id, created_at, plan", count="exact").execute()
        total_users = all_users.count or 0
        active_subs = supabase.table("users").select("id", count="exact").eq("plan", "active").execute()
        active_count = active_subs.count or 0
        trial_subs = supabase.table("users").select("id", count="exact").eq("plan", "trial").execute()
        trial_count = trial_subs.count or 0
        invoices = supabase.table("invoices").select("amount_ttc").execute()
        total_revenue = sum(float(inv.get("amount_ttc", 0)) for inv in (invoices.data or []))
        
        return jsonify({
            "total_users": total_users,
            "users_active_subscription": active_count,
            "users_trial": trial_count,
            "total_revenue_eur": round(total_revenue, 2),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }), 200
    
    except Exception as e:
        return jsonify({"error": "Stats indisponibles", "detail": str(e)}), 500