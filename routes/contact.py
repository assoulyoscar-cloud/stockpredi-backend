from flask import Blueprint, request, jsonify
from supabase import create_client
from config import Config

contact_bp = Blueprint("contact", __name__)

def get_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

@contact_bp.route("/", methods=["POST"])
def submit_contact():
    """POST /api/contact — soumette formulaire contact."""
    supabase = get_client()
    body = request.get_json(silent=True) or {}
    
    name = body.get("name", "").strip()
    email = body.get("email", "").strip()
    subject = body.get("subject", "").strip()
    message = body.get("message", "").strip()
    
    if not all([name, email, subject, message]):
        return jsonify({"error": "Tous les champs requis"}), 400
    
    if len(message) < 10:
        return jsonify({"error": "Message minimum 10 caracteres"}), 400
    
    try:
        supabase.table("contact_messages").insert({
            "name": name,
            "email": email,
            "subject": subject,
            "message": message
        }).execute()
        
        return jsonify({"message": "Message envoye"}), 201
    except Exception as e:
        return jsonify({"error": "Erreur soumission", "detail": str(e)}), 500