"""
Routes RGPD - Export données, suppression compte, contact DPO
"""
from flask import Blueprint, request, jsonify
from functools import wraps
import os
from datetime import datetime
import jwt
from services.archive_service import archive_client_signup
from services.google_drive_service import GoogleDriveService
from supabase import create_client

rgpd_bp = Blueprint('rgpd', __name__)


def get_supabase():
    """Crée une instance Supabase lazy (à la demande)"""
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise Exception("Supabase env vars not configured")

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_current_user(f):
    """Décorateur pour vérifier l'authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Pas de token', 'code': 'NO_AUTH_HEADER'}), 401

        try:
            token = auth_header.split(' ')[1]
            supabase = get_supabase()
            user_data = supabase.auth.get_user(token)
            request.user = user_data
            request.user_id = user_data.user.id
            request.user_email = user_data.user.email
        except Exception as e:
            return jsonify({'error': f'Token invalide: {str(e)}', 'code': 'INVALID_TOKEN'}), 401

        return f(*args, **kwargs)
    return decorated_function


@rgpd_bp.route('/api/rgpd/debug', methods=['GET'])
def debug_status():
    """Endpoint de debug - vérifie la configuration RGPD"""
    try:
        status = {
            'supabase_url': bool(os.getenv('SUPABASE_URL')),
            'supabase_key': bool(os.getenv('SUPABASE_ANON_KEY')),
            'resend_api_key': bool(os.getenv('RESEND_API_KEY')),
            'google_service_account': bool(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')),
            'google_drive_folder': bool(os.getenv('GOOGLE_DRIVE_FOLDER_ID')),
            'owner_email': os.getenv('OWNER_EMAIL', 'not set'),
            'all_configured': all([
                os.getenv('SUPABASE_URL'),
                os.getenv('SUPABASE_ANON_KEY'),
                os.getenv('RESEND_API_KEY'),
                os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'),
                os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            ])
        }
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rgpd_bp.route('/api/rgpd/export', methods=['POST'])
@get_current_user
def export_user_data():
    """
    Exporte les données personnelles de l'utilisateur en PDF
    Envoie le PDF à L'EMAIL DU CLIENT (pas au propriétaire)
    """
    try:
        user_email = request.user_email
        user_id = request.user_id

        print(f"[RGPD EXPORT] Exporting for user {user_id} ({user_email})")

        supabase = get_supabase()

        # Récupère les infos de l'utilisateur depuis Supabase
        print(f"[RGPD EXPORT] Fetching user data from Supabase...")
        user_response = supabase.table('users').select('*').eq('id', user_id).single().execute()
        user_data = user_response.data
        print(f"[RGPD EXPORT] User data fetched: {user_data.get('name')}")

        # Prépare les données du client AVEC son email
        client_data = {
            'email': user_email,  # EMAIL DU CLIENT, pas du propriétaire
            'name': user_data.get('name', 'Client'),
            'user_id': user_id,
            'plan': user_data.get('plan', 'trial'),
            'created_at': user_data.get('created_at', datetime.now().isoformat())
        }

        print(f"[RGPD EXPORT] Client data prepared: {client_data}")

        # Initialise Google Drive (optionnel)
        drive_service = None
        try:
            service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            if service_account_json and folder_id:
                print(f"[RGPD EXPORT] Initializing Google Drive service...")
                drive_service = GoogleDriveService(service_account_json, folder_id)
                print(f"[RGPD EXPORT] Google Drive service initialized")
            else:
                print(f"[RGPD EXPORT] Google Drive not configured (account: {bool(service_account_json)}, folder: {bool(folder_id)})")
        except Exception as e:
            print(f"[RGPD EXPORT] Google Drive error: {str(e)}")

        # Lance l'archivage (envoie à l'email du client)
        print(f"[RGPD EXPORT] Starting archive_client_signup...")
        result = archive_client_signup(client_data, drive_service)
        print(f"[RGPD EXPORT] Archive result: {result}")

        # Log l'action dans rgpd_audit
        try:
            print(f"[RGPD EXPORT] Logging to audit table...")
            supabase.table('rgpd_audit').insert({
                'user_id': user_id,
                'action': 'data_export',
                'details': {'email_sent': result.get('email_sent'), 'filename': result.get('filename')},
                'status': 'success' if result['success'] else 'failed',
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }).execute()
            print(f"[RGPD EXPORT] Audit logged successfully")
        except Exception as e:
            print(f"[RGPD EXPORT] Erreur audit: {str(e)}")

        if result['success']:
            return jsonify({
                'success': True,
                'message': f'Export envoyé à {user_email}',
                'details': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erreur export')
            }), 500

    except Exception as e:
        print(f"[RGPD EXPORT] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@rgpd_bp.route('/api/rgpd/status', methods=['GET'])
@get_current_user
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


@rgpd_bp.route('/api/rgpd/delete', methods=['DELETE'])
@get_current_user
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


@rgpd_bp.route('/api/rgpd/contact', methods=['POST'])
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
