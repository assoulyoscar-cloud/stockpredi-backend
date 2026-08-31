"""
Routes d'archivage automatique des clients
"""
from flask import Blueprint, request, jsonify
from functools import wraps
import os
from services.archive_service import archive_client_signup
from services.google_drive_service import GoogleDriveService
from datetime import datetime

archive_bp = Blueprint('archive', __name__)


def require_api_key(f):
    """Décorateur pour vérifier la clé API"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('INTERNAL_API_KEY', 'dev-key'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


@archive_bp.route('/api/archive/signup', methods=['POST'])
@require_api_key
def archive_new_signup():
    """
    Archive automatiquement un nouveau client après signup

    Body JSON:
    {
        "email": "oscar@stockpredi.fr",
        "name": "Oscar Assouly",
        "user_id": "uuid",
        "plan": "trial" ou "premium",
        "created_at": "2026-08-30T15:00:00Z"
    }
    """
    try:
        data = request.get_json()

        # Valide les champs requis
        required_fields = ['email', 'name', 'user_id']
        if not all(field in data for field in required_fields):
            return jsonify({
                'error': 'Champs requis: email, name, user_id'
            }), 400

        # Prépare les données du client
        client_data = {
            'email': data.get('email'),
            'name': data.get('name'),
            'user_id': data.get('user_id'),
            'plan': data.get('plan', 'trial'),
            'created_at': data.get('created_at', datetime.now().isoformat())
        }

        # Initialise le service Google Drive (optionnel)
        drive_service = None
        try:
            service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

            if service_account_json and folder_id:
                drive_service = GoogleDriveService(service_account_json, folder_id)
        except Exception as e:
            print(f"Google Drive non disponible: {str(e)}")

        # Lance l'archivage
        result = archive_client_signup(client_data, drive_service)

        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Client archivé avec succès',
                'archive': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erreur archivage')
            }), 500

    except Exception as e:
        return jsonify({
            'error': f'Erreur serveur: {str(e)}'
        }), 500


@archive_bp.route('/api/archive/list', methods=['GET'])
@require_api_key
def list_archived_files():
    """Liste les fichiers archivés sur Google Drive"""
    try:
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

        if not service_account_json or not folder_id:
            return jsonify({
                'error': 'Google Drive non configuré'
            }), 400

        drive_service = GoogleDriveService(service_account_json, folder_id)
        files = drive_service.list_files(max_results=50)

        return jsonify({
            'success': True,
            'count': len(files),
            'files': files
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Erreur listing: {str(e)}'
        }), 500


@archive_bp.route('/api/archive/status', methods=['GET'])
def archive_status():
    """Vérifie que le service d'archivage est opérationnel"""
    try:
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        resend_key = os.getenv('RESEND_API_KEY')

        status = {
            'google_drive_configured': bool(service_account_json and folder_id),
            'resend_configured': bool(resend_key),
            'archive_enabled': bool(service_account_json and folder_id and resend_key)
        }

        return jsonify(status), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
