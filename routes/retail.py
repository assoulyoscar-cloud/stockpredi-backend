"""
routes/retail.py - Retail sector forecasting with seasonal factors & promotions
Phase 5 P2 Implementation
"""
import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from middleware.auth_middleware import auth_required

retail_bp = Blueprint("retail", __name__)
logger = logging.getLogger("stockpredi.retail")

# Seasonal multipliers by month (Jan=1 to Dec=12)
SEASONAL_FACTORS = {
    1: -0.20,   # January: -20% (post-holiday dip)
    2: 0.00,    # February: baseline
    3: 0.15,    # March: +15% (spring refresh)
    4: 0.20,    # April: +20% (Easter)
    5: 0.10,    # May: +10% (late spring)
    6: 0.05,    # June: +5% (summer prep)
    7: 0.30,    # July: +30% (summer peak)
    8: 0.25,    # August: +25% (back-to-school)
    9: 0.20,    # September: +20% (fall/fashion)
    10: 0.40,   # October: +40% (Halloween + fall)
    11: 0.70,   # November: +70% (Black Friday)
    12: 1.50,   # December: +150% (Christmas)
}

PRODUCT_CATEGORIES = [
    "clothing",
    "electronics", 
    "furniture",
    "home_goods",
    "sports",
    "toys",
    "beauty",
    "books"
]

PROMOTION_TYPES = {
    "flash": 2.00,      # 24h promotion: +200% demand
    "weekly": 1.00,     # Weekly sale: +100% demand
    "seasonal": 0.50,   # Seasonal: +50% demand
}


@retail_bp.route("/products", methods=["GET"])
@auth_required
def get_products():
    """Get available product categories for retail sector"""
    return jsonify({
        "categories": PRODUCT_CATEGORIES,
        "count": len(PRODUCT_CATEGORIES)
    }), 200


@retail_bp.route("/seasonal-factors", methods=["GET"])
@auth_required
def get_seasonal_factors():
    """Get seasonal multipliers for all months"""
    month = request.args.get("month", type=int)
    
    if month:
        if not 1 <= month <= 12:
            return jsonify({"error": "Month must be 1-12"}), 400
        
        factor = SEASONAL_FACTORS.get(month, 0)
        return jsonify({
            "month": month,
            "factor": factor,
            "multiplier": 1 + factor,  # e.g., 1.30 for +30%
            "description": f"{'Increase' if factor > 0 else 'Decrease'} demand by {abs(factor)*100:.0f}%"
        }), 200
    
    # Return all months
    all_factors = {}
    for month, factor in SEASONAL_FACTORS.items():
        all_factors[month] = {
            "factor": factor,
            "multiplier": 1 + factor
        }
    
    return jsonify({
        "seasonal_factors": all_factors,
        "note": "Multiplier = 1 + factor (e.g., 1.30 = 30% increase)"
    }), 200


@retail_bp.route("/apply-promotion", methods=["POST"])
@auth_required
def apply_promotion():
    """
    Calculate promotion impact on demand forecast
    
    Request body:
    {
        "base_forecast": 1000,      # Expected units
        "promotion_type": "flash",  # flash | weekly | seasonal
        "discount_percent": 25,     # 0-100
        "current_month": 12         # 1-12 (optional, default to now)
    }
    """
    data = request.get_json()
    
    # Validation
    if not data:
        return jsonify({"error": "Request body required"}), 400
    
    base_forecast = data.get("base_forecast", 0)
    promotion_type = data.get("promotion_type", "").lower()
    discount_percent = data.get("discount_percent", 0)
    current_month = data.get("current_month", datetime.now().month)
    
    # Validate inputs
    if not base_forecast or base_forecast <= 0:
        return jsonify({"error": "base_forecast must be > 0"}), 400
    
    if promotion_type not in PROMOTION_TYPES:
        return jsonify({
            "error": f"promotion_type must be one of: {list(PROMOTION_TYPES.keys())}"
        }), 400
    
    if not 0 <= discount_percent <= 100:
        return jsonify({"error": "discount_percent must be 0-100"}), 400
    
    if not 1 <= current_month <= 12:
        return jsonify({"error": "current_month must be 1-12"}), 400
    
    try:
        # Calculate adjustments
        seasonal_multiplier = 1 + SEASONAL_FACTORS[current_month]
        promotion_multiplier = 1 + PROMOTION_TYPES[promotion_type]
        
        # Seasonal adjusted base
        seasonal_forecast = base_forecast * seasonal_multiplier
        
        # Apply promotion impact
        promotion_impact = base_forecast * (discount_percent / 100) * (PROMOTION_TYPES[promotion_type])
        adjusted_forecast = seasonal_forecast + promotion_impact
        
        # Ensure non-negative
        adjusted_forecast = max(0, adjusted_forecast)
        
        return jsonify({
            "base_forecast": base_forecast,
            "seasonal_factor": SEASONAL_FACTORS[current_month],
            "seasonal_multiplier": seasonal_multiplier,
            "seasonal_forecast": round(seasonal_forecast, 2),
            "promotion_type": promotion_type,
            "promotion_multiplier": PROMOTION_TYPES[promotion_type],
            "discount_percent": discount_percent,
            "promotion_impact": round(promotion_impact, 2),
            "adjusted_forecast": round(adjusted_forecast, 2),
            "increase_percent": round(((adjusted_forecast - base_forecast) / base_forecast * 100), 2)
        }), 200
    
    except Exception as e:
        logger.error(f"Promotion calculation error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@retail_bp.route("/forecast", methods=["POST"])
@auth_required
def forecast_demand():
    """
    Generate retail demand forecast
    
    Request body:
    {
        "product_category": "clothing",
        "base_demand": 1000,
        "current_month": 12,
        "promotion": {
            "type": "flash",
            "discount": 25
        }
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body required"}), 400
    
    product_category = data.get("product_category", "").lower()
    base_demand = data.get("base_demand", 0)
    current_month = data.get("current_month", datetime.now().month)
    promotion = data.get("promotion")
    
    # Validate
    if product_category not in PRODUCT_CATEGORIES:
        return jsonify({
            "error": f"product_category must be one of: {PRODUCT_CATEGORIES}"
        }), 400
    
    if base_demand <= 0:
        return jsonify({"error": "base_demand must be > 0"}), 400
    
    # Apply seasonal factor
    seasonal_multiplier = 1 + SEASONAL_FACTORS[current_month]
    forecast = base_demand * seasonal_multiplier
    
    # Apply promotion if provided
    if promotion and "type" in promotion:
        promo_type = promotion.get("type", "").lower()
        discount = promotion.get("discount", 0)
        
        if promo_type in PROMOTION_TYPES:
            promo_impact = base_demand * (discount / 100) * PROMOTION_TYPES[promo_type]
            forecast += promo_impact
    
    forecast = max(0, forecast)
    
    return jsonify({
        "product": product_category,
        "base_demand": base_demand,
        "month": current_month,
        "seasonal_factor": SEASONAL_FACTORS[current_month],
        "forecast": round(forecast, 2),
        "confidence": "medium",
        "recommendation": "Monitor actual sales daily"
    }), 200


@retail_bp.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "retail",
        "products": len(PRODUCT_CATEGORIES),
        "months": len(SEASONAL_FACTORS)
    }), 200
