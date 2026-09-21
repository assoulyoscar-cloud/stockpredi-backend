"""
Sector Settings Routes
- GET /api/sectors/{sector}/settings - Retrieve sector-specific settings
- POST /api/sectors/{sector}/settings - Update sector-specific settings
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
from supabase import create_client
from config import Config
import logging

logger = logging.getLogger(__name__)

sector_settings_bp = Blueprint('sector_settings', __name__)

# Initialize Supabase client
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

# Valid sectors
VALID_SECTORS = ['fob', 'retail', 'manufacturing']


def auth_required(f):
    """Decorator to verify JWT token and extract user_id"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get('sub')
        except:
            return jsonify({'error': 'Invalid token'}), 401
        
        if not user_id:
            return jsonify({'error': 'Could not extract user ID from token'}), 401
        
        # Store user_id in request context for use in route handlers
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated_function


@sector_settings_bp.route('/<sector>/settings', methods=['GET'])
@auth_required
def get_sector_settings(sector):
    """
    Get sector-specific settings for the current user.
    
    Args:
        sector: The sector identifier (fob, retail, manufacturing)
    
    Response:
        {
            "success": true,
            "sector": "retail",
            "settings": {
                "store_size": "small",
                "category_focus": "food",
                "location": "Paris"
            }
        }
    """
    try:
        # Validate sector
        if sector not in VALID_SECTORS:
            return jsonify({'error': f'Invalid sector. Must be one of: {", ".join(VALID_SECTORS)}'}), 400
        
        user_id = request.user_id
        
        # Query sector_settings table
        try:
            response = supabase.table('sector_settings').select('settings').eq(
                'user_id', user_id
            ).eq('sector', sector).single().execute()
            
            settings = response.data.get('settings', {}) if response.data else {}
        except Exception as e:
            # If record doesn't exist, return empty settings (not an error)
            logger.info(f"No existing settings for user {user_id} in sector {sector}")
            settings = {}
        
        return jsonify({
            'success': True,
            'sector': sector,
            'settings': settings
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting sector settings: {str(e)}")
        return jsonify({'error': f'Failed to get settings: {str(e)}'}), 500


@sector_settings_bp.route('/<sector>/settings', methods=['POST'])
@auth_required
def update_sector_settings(sector):
    """
    Update sector-specific settings for the current user.
    
    Args:
        sector: The sector identifier (fob, retail, manufacturing)
    
    Request Body:
        {
            "store_size": "medium",
            "category_focus": "food_electronics",
            "location": "Lyon"
        }
    
    Response:
        {
            "success": true,
            "sector": "retail",
            "message": "Settings updated successfully"
        }
    """
    try:
        # Validate sector
        if sector not in VALID_SECTORS:
            return jsonify({'error': f'Invalid sector. Must be one of: {", ".join(VALID_SECTORS)}'}), 400
        
        data = request.get_json() or {}
        user_id = request.user_id
        
        # Validate that at least one setting is provided
        if not data:
            return jsonify({'error': 'No settings provided'}), 400
        
        # Prepare the record for upsert
        record = {
            'user_id': user_id,
            'sector': sector,
            'settings': data
        }
        
        # Upsert settings (create if doesn't exist, update if exists)
        response = supabase.table('sector_settings').upsert(record).execute()
        
        if not response.data:
            raise Exception("Failed to upsert settings")
        
        return jsonify({
            'success': True,
            'sector': sector,
            'message': 'Settings updated successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating sector settings: {str(e)}")
        return jsonify({'error': f'Failed to update settings: {str(e)}'}), 500


@sector_settings_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for sector settings API"""
    return jsonify({'status': 'ok', 'service': 'sector_settings'}), 200
