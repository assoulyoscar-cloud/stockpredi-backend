"""
Routes RGPD - Export données, suppression compte, contact DPO
"""
from flask import Blueprint, request, jsonify, Response
import os
from datetime import datetime
from middleware.auth_middleware import auth_required
from services.archive_service import generate_archive_pdf
from services.google_drive_service import get_google_drive_service
from supabase import create_client

rgpd_bp = Blueprint('rgpd', __name__)


def get_supabase():
    """Crée une instance Supabase lazy (à la demande) — clé service,
    même pattern que middleware/auth_middleware.py et routes/user.py."""
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise Exception("Supabase env vars not configured")

    return create_client(SUPABASE_URL, SUPABASE_KEY)


@rgpd_bp.route('/debug', methods=['GET'])
def debug_status():
    """Endpoint de debug - vérifie la configuration RGPD"""
    try:
        status = {
            'supabase_url': bool(os.getenv('SUPABASE_URL')),
            'supabase_anon_key': bool(os.getenv('SUPABASE_ANON_KEY')),
            'supabase_service_key': bool(os.getenv('SUPABASE_SERVICE_KEY')),
            'google_service_account': bool(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')),
            'google_drive_folder': bool(os.getenv('GOOGLE_DRIVE_FOLDER_ID')),
            'owner_email': os.getenv('OWNER_EMAIL', 'not set'),
            'all_configured': all([
                os.getenv('SUPABASE_URL'),
                os.getenv('SUPABASE_SERVICE_KEY'),
            ])
        }
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rgpd_bp.route('/export', methods=['POST'])
@auth_required
def export_user_data():
    """
    Génère un PDF avec les données personnelles de l'utilisateur, le
    renvoie DIRECTEMENT en téléchargement (pas d'email), et en archive
    une copie sur Google Drive pour l'audit RGPD interne.
    """
    user_id = request.user_id
    user_email = request.user_email

    try:
        print(f"[RGPD EXPORT] Exporting for user {user_id} ({user_email})")

        supabase = get_supabase()

        # Récupère les infos de l'utilisateur depuis Supabase
        user_data = {}
        try:
            user_response = supabase.table('users').select('*').eq('id', user_id).single().execute()
            user_data = user_response.data or {}
        except Exception as e:
            print(f"[RGPD EXPORT] Impossible de charger la ligne users: {str(e)}")

        # Prépare les données du client — `or` plutôt que `.get(k, default)`
        # pour ne pas laisser passer une valeur explicitement NULL en base.
        client_data = {
            'email': user_email,
            'name': user_data.get('name') or 'Client',
            'user_id': user_id,
            'plan': user_data.get('plan') or 'trial',
            'created_at': user_data.get('created_at') or datetime.now().isoformat()
        }

        print(f"[RGPD EXPORT] Client data prepared: {client_data}")

        # Génère le PDF
        pdf_bytes = generate_archive_pdf(client_data)

        timestamp = datetime.now().strftime('%Y%m%d')
        safe_name = (client_data.get('name') or 'client').replace(' ', '_').lower()
        filename = f"{safe_name}_{timestamp}.pdf"

        # Archive une copie sur Google Drive — best-effort, ne doit jamais
        # empêcher le client de récupérer son téléchargement.
        drive_uploaded = False
        drive_file_id = None
        try:
            drive_service = get_google_drive_service()
            if drive_service:
                drive_result = drive_service.upload_pdf(pdf_bytes, filename)
                drive_uploaded = bool(drive_result and drive_result.get('success'))
                drive_file_id = drive_result.get('file_id') if drive_result else None
                if not drive_uploaded:
                    print(f"[RGPD EXPORT] Upload Drive echoue: {drive_result}")
            else:
                print("[RGPD EXPORT] Google Drive non configure — export local uniquement")
        except Exception as e:
            print(f"[RGPD EXPORT] Erreur upload Google Drive: {str(e)}")

        # Log l'action dans rgpd_audit — ne bloque jamais le téléchargement
        try:
            supabase.table('rgpd_audit').insert({
                'user_id': user_id,
                'action': 'data_export',
                'details': {'drive_uploaded': drive_uploaded, 'drive_file_id': drive_file_id, 'filename': filename},
                'status': 'success',
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }).execute()
        except Exception as e:
            print(f"[RGPD EXPORT] Erreur audit: {str(e)}")

        # Renvoie le PDF directement au client — téléchargement local
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Access-Control-Expose-Headers': 'Content-Disposition',
            }
        )

    except Exception as e:
        print(f"[RGPD EXPORT] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Log l'échec dans l'audit si possible
        try:
            get_supabase().table('rgpd_audit').insert({
                'user_id': user_id,
                'action': 'data_export',
                'details': {'error': str(e)},
                'status': 'failed',
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }).execute()
        except Exception:
            pass
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@rgpd_bp.route('/status', methods=['GET'])
@auth_required
def export_status():
    """Récupère l'historique des exports de l'utilisateur"""
    try:
        user_id = request.user_id
        supabase = get_supabase()

        exports = supabase.table('rgpd_audit').select(
            'id, action, details, status, timestamp'
        ).eq('user_id', user_id).eq('action', 'data_export').order(
            'timestamp', desc=True
        ).limit(10).execute()

        return jsonify({
            'success': True,
            'exports': exports.data
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@rgpd_bp.route('/delete', methods=['DELETE'])
@auth_required
def delete_account():
    """Supprime complètement le compte et les données de l'utilisateur"""
    try:
        user_id = request.user_id
        user_email = request.user_email
        supabase = get_supabase()

        # Log la suppression
        try:
            supabase.table('rgpd_audit').insert({
                'user_id': user_id,
                'action': 'account_deletion',
                'details': {'email': user_email},
                'status': 'success',
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }).execute()
        except Exception as e:
            print(f"Erreur audit suppression: {str(e)}")

        # Supprime les données utilisateur
        try:
            supabase.table('users').delete().eq('id', user_id).execute()
            supabase.table('predictions').delete().eq('user_id', user_id).execute()
        except Exception as e:
            print(f"Erreur suppression données: {str(e)}")

        # Supprime le compte auth
        try:
            supabase.auth.admin.delete_user(user_id)
        except Exception as e:
            print(f"Erreur suppression compte auth: {str(e)}")

        return jsonify({
            'success': True,
            'message': 'Compte supprimé avec succès'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@rgpd_bp.route('/contact', methods=['POST'])
def contact_dpo():
    """Formulaire de contact pour le DPO"""
    try:
        data = request.get_json()

        required_fields = ['email', 'subject', 'message']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Champs requis: email, subject, message'}), 400

        # Log la demande
        try:
            supabase = get_supabase()
            supabase.table('rgpd_audit').insert({
                'user_id': None,
                'action': 'dpo_contact',
                'details': {
                    'email': data.get('email'),
                    'subject': data.get('subject')
                },
                'status': 'received',
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }).execute()
        except Exception as e:
            print(f"Erreur log contact DPO: {str(e)}")

        return jsonify({
            'success': True,
            'message': 'Demande reçue, le DPO vous contactera rapidement'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500
