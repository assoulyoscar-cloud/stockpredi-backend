"""
Occupations API Routes
"""
from flask import Blueprint, jsonify
from models.occupation_categories import (
    get_occupation_list,
    get_occupation_config,
    validate_occupation,
    get_occupation_forecast_config,
    get_occupation_business_metrics
)

occupations_bp = Blueprint('occupations', __name__, url_prefix='/api/occupations')


@occupations_bp.route('/list', methods=['GET'])
def list_occupations():
    """List all occupations"""
    try:
        occupations = get_occupation_list()
        return jsonify({
            "success": True,
            "count": len(occupations),
            "occupations": occupations
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@occupations_bp.route('/<occupation_key>', methods=['GET'])
def get_occupation(occupation_key):
    """Get full occupation configuration"""
    try:
        config = get_occupation_config(occupation_key)
        if not config:
            return jsonify({"error": f"Occupation '{occupation_key}' not found"}), 404
        
        return jsonify({
            "success": True,
            "occupation_key": occupation_key,
            "config": config
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@occupations_bp.route('/<occupation_key>/forecast-config', methods=['GET'])
def get_forecast_config(occupation_key):
    """Get forecast configuration only"""
    try:
        config = get_occupation_forecast_config(occupation_key)
        if not config:
            return jsonify({"error": f"Occupation '{occupation_key}' not found"}), 404
        
        return jsonify({
            "success": True,
            "occupation": occupation_key,
            **config
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@occupations_bp.route('/<occupation_key>/business-metrics', methods=['GET'])
def get_business_metrics(occupation_key):
    """Get business metrics only"""
    try:
        metrics = get_occupation_business_metrics(occupation_key)
        if metrics is None:
            return jsonify({"error": f"Occupation '{occupation_key}' not found"}), 404
        
        return jsonify({
            "success": True,
            "occupation": occupation_key,
            "business_metrics": metrics
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@occupations_bp.route('/<occupation_key>/key-products', methods=['GET'])
def get_key_products(occupation_key):
    """Get key products for occupation"""
    try:
        config = get_occupation_config(occupation_key)
        if not config:
            return jsonify({"error": f"Occupation '{occupation_key}' not found"}), 404
        
        products = config.get("key_products", [])
        return jsonify({
            "success": True,
            "occupation": occupation_key,
            "key_products": products,
            "count": len(products)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@occupations_bp.route('/validate', methods=['POST'])
def validate():
    """Validate if occupation exists"""
    from flask import request
    try:
        data = request.get_json() or {}
        occupation = data.get("occupation", "").lower()
        
        is_valid = validate_occupation(occupation)
        return jsonify({
            "valid": is_valid,
            "occupation": occupation
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
