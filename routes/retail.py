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


# ===== DLUO Tracking Routes (P3) =====

@retail_bp.route('/import-dluo', methods=['POST'])
@auth_required
def import_dluo_csv():
    """
    Parse CSV with DLUO column and return normalized data.

    Expected CSV columns:
    - product (required)
    - quantity (required)
    - dluo (required, format: YYYY-MM-DD)
    - category (optional)
    - batch_id (optional)

    Response: list of normalized products with expiration tracking
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith(('.csv', '.xlsx')):
            return jsonify({'error': 'Only CSV/XLSX files allowed'}), 400

        import csv
        from io import StringIO

        # Parse CSV
        if file.filename.endswith('.csv'):
            stream = StringIO(file.stream.read().decode('utf-8'))
            reader = csv.DictReader(stream)
        else:
            import openpyxl
            wb = openpyxl.load_workbook(file)
            ws = wb.active
            headers = [cell.value for cell in ws[1]]
            rows = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                rows.append(dict(zip(headers, row)))
            reader = rows

        # Validate and normalize
        products = []
        errors = []

        for idx, row in enumerate(reader, start=2):
            try:
                # Required fields
                product = row.get('product') or row.get('nom')
                quantity_str = str(row.get('quantity') or row.get('quantité') or '')
                dluo_str = str(row.get('dluo') or row.get('DLUO') or row.get('expiration') or '')

                if not product:
                    errors.append(f"Row {idx}: Missing product name")
                    continue

                if not quantity_str.strip():
                    errors.append(f"Row {idx} ({product}): Missing quantity")
                    continue

                if not dluo_str.strip():
                    errors.append(f"Row {idx} ({product}): Missing DLUO date")
                    continue

                # Parse quantity
                try:
                    quantity = float(quantity_str.replace(',', '.'))
                except ValueError:
                    errors.append(f"Row {idx} ({product}): Invalid quantity '{quantity_str}'")
                    continue

                # Parse DLUO date (multiple formats supported)
                dluo_date = None
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        dluo_date = datetime.strptime(dluo_str.strip(), fmt).date()
                        break
                    except ValueError:
                        continue

                if not dluo_date:
                    errors.append(f"Row {idx} ({product}): Invalid DLUO format '{dluo_str}' (use YYYY-MM-DD)")
                    continue

                # Calculate days remaining
                today = datetime.now().date()
                days_remaining = (dluo_date - today).days

                # Categorize urgency
                if days_remaining < 0:
                    urgency = 'expired'
                elif days_remaining <= 2:
                    urgency = 'critical'
                elif days_remaining <= 7:
                    urgency = 'high'
                elif days_remaining <= 14:
                    urgency = 'medium'
                else:
                    urgency = 'low'

                products.append({
                    'product': product,
                    'quantity': quantity,
                    'dluo': dluo_date.isoformat(),
                    'days_remaining': days_remaining,
                    'urgency': urgency,
                    'category': row.get('category') or row.get('catégorie') or 'General',
                    'batch_id': row.get('batch_id') or row.get('lot'),
                })

            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

        return jsonify({
            'success': len(products) > 0,
            'products_parsed': len(products),
            'products': products,
            'errors': errors if errors else None,
            'message': f"Parsed {len(products)} products" + (f" with {len(errors)} errors" if errors else "")
        }), 200

    except Exception as e:
        return jsonify({'error': f'CSV parsing failed: {str(e)}'}), 400


@retail_bp.route('/expiring-soon', methods=['GET'])
@auth_required
def get_expiring_soon():
    """
    Get products expiring within the next N days.

    Query parameters:
    - days_threshold: days until expiration (default: 7)
    - category: filter by category (optional)
    - sort_by: 'days' (default) or 'quantity'

    Response: sorted list of expiring products with suggested actions
    """
    try:
        days_threshold = request.args.get('days_threshold', 7, type=int)
        category_filter = request.args.get('category', None)
        sort_by = request.args.get('sort_by', 'days')  # 'days' or 'quantity'

        if days_threshold < 1 or days_threshold > 90:
            return jsonify({'error': 'days_threshold must be between 1 and 90'}), 400

        if sort_by not in ['days', 'quantity']:
            return jsonify({'error': 'sort_by must be "days" or "quantity"'}), 400

        # In production, this would query Supabase
        # For now, return schema example
        expiring = [
            {
                'id': 'prod_001',
                'product': 'Bread (Whole Wheat)',
                'category': 'Bakery',
                'quantity': 24,
                'unit': 'units',
                'dluo': (datetime.now().date() + timedelta(days=3)).isoformat(),
                'days_remaining': 3,
                'urgency': 'high',
                'batch_id': 'LOT-2026-0921-001',
                'current_price': 3.50,
                'suggested_discount': 0.25,  # 25% discount
                'suggested_price': 2.62,
                'estimated_recovery': 63.00,  # 24 × 2.62
                'action': 'Discount to move stock before expiry',
            },
            {
                'id': 'prod_002',
                'product': 'Yogurt (Strawberry)',
                'category': 'Dairy',
                'quantity': 48,
                'unit': 'units',
                'dluo': (datetime.now().date() + timedelta(days=5)).isoformat(),
                'days_remaining': 5,
                'urgency': 'high',
                'batch_id': 'LOT-2026-0916-003',
                'current_price': 1.25,
                'suggested_discount': 0.35,  # 35% discount
                'suggested_price': 0.81,
                'estimated_recovery': 39.00,  # 48 × 0.81
                'action': 'Bundle promotion recommended',
            }
        ]

        return jsonify({
            'success': True,
            'threshold_days': days_threshold,
            'count': len(expiring),
            'total_units_at_risk': sum(item['quantity'] for item in expiring),
            'total_recovery_potential': sum(item['estimated_recovery'] for item in expiring),
            'expiring_products': expiring,
            'recommendations': {
                'high_urgency': len([x for x in expiring if x['urgency'] == 'high']),
                'suggested_actions': [
                    'Apply 25-35% discounts to high-urgency items',
                    'Create bundle promotions (combine slow + expiring items)',
                    'Email customers about limited-time deals',
                    'Consider donation if discount doesn\'t move stock'
                ]
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Query failed: {str(e)}'}), 500


@retail_bp.route('/discount-suggestion', methods=['POST'])
@auth_required
def suggest_discount():
    """
    Calculate optimal discount to move expiring stock.

    Request body:
    - product_id: product identifier
    - current_price: current selling price
    - quantity: units to move
    - days_remaining: days until expiration
    - margin_percent: desired margin (default: 15%)
    - category: product category

    Response: suggested discount with projected revenue
    """
    try:
        data = request.get_json() or {}

        # Validate inputs
        current_price = data.get('current_price', 0)
        quantity = data.get('quantity', 0)
        days_remaining = data.get('days_remaining', 0)
        margin_percent = data.get('margin_percent', 15)

        if current_price <= 0:
            return jsonify({'error': 'current_price must be positive'}), 400
        if quantity <= 0:
            return jsonify({'error': 'quantity must be positive'}), 400
        if days_remaining < 0:
            return jsonify({'error': 'days_remaining cannot be negative'}), 400
        if margin_percent < 0 or margin_percent > 100:
            return jsonify({'error': 'margin_percent must be 0-100'}), 400

        # Urgency-based discount calculation
        if days_remaining <= 2:
            urgency_factor = 0.40  # -40% from current price
        elif days_remaining <= 7:
            urgency_factor = 0.30  # -30%
        elif days_remaining <= 14:
            urgency_factor = 0.20  # -20%
        else:
            urgency_factor = 0.10  # -10%

        # Cost basis calculation (reverse from margin)
        cost_per_unit = current_price / (1 + margin_percent / 100)

        # Suggested price maintains margin
        suggested_price = cost_per_unit * (1 + margin_percent / 100) * (1 - urgency_factor)
        suggested_discount = ((current_price - suggested_price) / current_price) * 100

        # Projections
        current_revenue = current_price * quantity
        suggested_revenue = suggested_price * quantity
        revenue_loss = current_revenue - suggested_revenue

        # Breakeven: at what discount do we lose more to spoilage than to discounting?
        # Assume 100% loss if not sold (spoilage = current_price × quantity)
        move_probability_at_discount = 1 - (suggested_discount / 100) * 0.5  # rough heuristic
        expected_revenue = suggested_revenue * move_probability_at_discount

        return jsonify({
            'success': True,
            'product_id': data.get('product_id'),
            'current_price': current_price,
            'suggested_price': round(suggested_price, 2),
            'discount_percent': round(suggested_discount, 1),
            'urgency_factor': urgency_factor,
            'quantity': quantity,
            'current_revenue': round(current_revenue, 2),
            'suggested_revenue': round(suggested_revenue, 2),
            'revenue_loss_per_unit': round(current_price - suggested_price, 2),
            'total_revenue_impact': round(suggested_revenue - current_revenue, 2),
            'expected_revenue_at_discount': round(expected_revenue, 2),
            'recommendation': 'Apply discount to maximize recovery' if expected_revenue > (cost_per_unit * quantity) else 'Consider donation',
        }), 200

    except Exception as e:
        return jsonify({'error': f'Calculation failed: {str(e)}'}), 500


@retail_bp.route('/inventory-reconciliation', methods=['POST'])
@auth_required
def reconcile_with_expiry():
    """
    Suggest order quantities considering expiration dates.

    Request body:
    - product_id: product identifier
    - current_stock: current quantity on hand
    - forecasted_demand: units forecast
    - lead_time_days: days to receive new stock
    - expiration_date: DLUO of current stock (YYYY-MM-DD)
    - safety_stock_percent: buffer % (default: 20%)

    Response: recommended order quantity accounting for expiry
    """
    try:
        data = request.get_json() or {}

        current_stock = data.get('current_stock', 0)
        forecasted_demand = data.get('forecasted_demand', 0)
        lead_time = data.get('lead_time_days', 7)
        expiration_str = data.get('expiration_date')
        safety_percent = data.get('safety_stock_percent', 20)

        if not expiration_str:
            return jsonify({'error': 'expiration_date required (YYYY-MM-DD)'}), 400

        try:
            expiry_date = datetime.strptime(expiration_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid expiration_date format'}), 400

        days_to_expiry = (expiry_date - datetime.now().date()).days

        # Calculate usable stock (won't expire before lead time + buffer)
        if days_to_expiry < lead_time:
            usable_stock = 0  # Expired before new order arrives
        else:
            usable_stock = current_stock

        # Demand over lead time
        demand_during_lead_time = forecasted_demand * (lead_time / 30)  # assume 30-day forecast period

        # Safety stock
        safety_stock = forecasted_demand * (safety_percent / 100)

        # Suggested order
        if usable_stock >= (demand_during_lead_time + safety_stock):
            order_quantity = 0  # Don't order
        else:
            order_quantity = (demand_during_lead_time + safety_stock) - usable_stock

        return jsonify({
            'success': True,
            'product_id': data.get('product_id'),
            'current_stock': current_stock,
            'days_to_expiry': days_to_expiry,
            'usable_stock': max(0, usable_stock),
            'forecasted_demand_monthly': forecasted_demand,
            'demand_during_lead_time': round(demand_during_lead_time, 1),
            'safety_stock_required': round(safety_stock, 1),
            'suggested_order_quantity': round(max(0, order_quantity), 0),
            'recommendation': (
                'No order needed - sufficient stock' if order_quantity <= 0
                else f'Order {max(0, order_quantity)} units to meet demand + safety'
            ),
            'expiry_warning': (
                'CRITICAL: Stock expires before new order arrives!' if days_to_expiry < lead_time
                else 'Stock remains valid during lead time' if days_to_expiry >= lead_time + 14
                else 'WARNING: Stock expires shortly after lead time'
            )
        }), 200

    except Exception as e:
        return jsonify({'error': f'Reconciliation failed: {str(e)}'}), 500


@retail_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint (no auth required)."""
    return jsonify({
        'status': 'healthy',
        'service': 'retail-dluo',
        'timestamp': datetime.now().isoformat(),
        'endpoints': [
            'POST /import-dluo',
            'GET /expiring-soon',
            'POST /discount-suggestion',
            'POST /inventory-reconciliation',
            'GET /health'
        ]
    }), 200
