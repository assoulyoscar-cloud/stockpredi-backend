"""
Phase 5 P3: Retail Sector - DLUO Tracking Unit Tests

Tests for expiration date management, discount suggestions,
and inventory reconciliation with expiry awareness.
"""

import pytest
from datetime import datetime, timedelta
import json
from io import BytesIO


@pytest.fixture
def client(test_app):
    """Test client fixture."""
    return test_app.test_client()


@pytest.fixture
def auth_headers():
    """Authorization headers with mock JWT token."""
    return {
        'Authorization': 'Bearer mock_jwt_token_xyz'
    }


class TestDLUOImport:
    """Tests for CSV/XLSX import with DLUO parsing."""

    def test_import_dluo_csv_valid(self, client, auth_headers):
        """Test successful CSV import with valid DLUO dates."""
        csv_content = b"""product,quantity,dluo
Bread Whole Wheat,24,2026-09-24
Yogurt Strawberry,48,2026-09-26
Croissants,12,2026-09-22
"""
        data = {
            'file': (BytesIO(csv_content), 'inventory.csv')
        }

        response = client.post(
            '/api/sectors/retail/import-dluo',
            data=data,
            headers=auth_headers,
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['products_parsed'] == 3
        assert len(result['products']) == 3

        # Verify parsed data
        bread = result['products'][0]
        assert bread['product'] == 'Bread Whole Wheat'
        assert bread['quantity'] == 24
        assert bread['dluo'] == '2026-09-24'
        assert isinstance(bread['days_remaining'], int)
        assert bread['urgency'] in ['critical', 'high', 'medium', 'low', 'expired']

    def test_import_dluo_multiple_date_formats(self, client, auth_headers):
        """Test CSV import with multiple date formats."""
        csv_content = b"""product,quantity,dluo
Product A,10,2026-09-25
Product B,20,25/09/2026
Product C,15,25-09-2026
"""
        data = {'file': (BytesIO(csv_content), 'inventory.csv')}

        response = client.post(
            '/api/sectors/retail/import-dluo',
            data=data,
            headers=auth_headers,
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['products_parsed'] == 3
        # All should parse successfully despite different formats
        assert all(p['dluo'] for p in result['products'])

    def test_import_dluo_missing_required_fields(self, client, auth_headers):
        """Test CSV import with missing required fields."""
        csv_content = b"""product,quantity,dluo
Bread,24,2026-09-24
Yogurt,,2026-09-26
Croissants,12,
"""
        data = {'file': (BytesIO(csv_content), 'inventory.csv')}

        response = client.post(
            '/api/sectors/retail/import-dluo',
            data=data,
            headers=auth_headers,
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['products_parsed'] == 1  # Only first row valid
        assert result['errors'] is not None
        assert len(result['errors']) == 2

    def test_import_dluo_invalid_date_format(self, client, auth_headers):
        """Test CSV import with invalid date format."""
        csv_content = b"""product,quantity,dluo
Bread,24,invalid-date
Yogurt,48,2026-99-99
"""
        data = {'file': (BytesIO(csv_content), 'inventory.csv')}

        response = client.post(
            '/api/sectors/retail/import-dluo',
            data=data,
            headers=auth_headers,
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['products_parsed'] == 0
        assert result['errors'] is not None

    def test_import_dluo_no_file(self, client, auth_headers):
        """Test import without file."""
        response = client.post(
            '/api/sectors/retail/import-dluo',
            data={},
            headers=auth_headers,
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        result = response.get_json()
        assert 'No file' in result['error']

    def test_import_dluo_missing_auth(self, client):
        """Test import without authentication."""
        csv_content = b"""product,quantity,dluo
Bread,24,2026-09-24
"""
        data = {'file': (BytesIO(csv_content), 'inventory.csv')}

        response = client.post(
            '/api/sectors/retail/import-dluo',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 401


class TestExpiringCriteria:
    """Tests for identifying and categorizing expiring items."""

    @pytest.mark.parametrize('days_remaining,expected_urgency', [
        (-1, 'expired'),
        (0, 'critical'),
        (1, 'critical'),
        (2, 'critical'),
        (3, 'high'),
        (7, 'high'),
        (8, 'medium'),
        (14, 'medium'),
        (15, 'low'),
        (30, 'low'),
    ])
    def test_urgency_categorization(self, days_remaining, expected_urgency, client, auth_headers):
        """Test urgency categorization based on days remaining."""
        # This is tested implicitly through import
        # Here we verify the logic matches expected categories
        today = datetime.now().date()
        dluo_date = today + timedelta(days=days_remaining)

        csv_content = f"""product,quantity,dluo
Test,10,{dluo_date.isoformat()}
""".encode()

        data = {'file': (BytesIO(csv_content), 'inventory.csv')}

        response = client.post(
            '/api/sectors/retail/import-dluo',
            data=data,
            headers=auth_headers,
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['products_parsed'] == 1
        assert result['products'][0]['urgency'] == expected_urgency


class TestExpiringSearch:
    """Tests for querying expiring products."""

    def test_get_expiring_soon_default(self, client, auth_headers):
        """Test getting expiring products with default threshold (7 days)."""
        response = client.get(
            '/api/sectors/retail/expiring-soon',
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['threshold_days'] == 7
        assert 'expiring_products' in result
        assert 'count' in result
        assert 'total_units_at_risk' in result
        assert 'total_recovery_potential' in result

    def test_get_expiring_soon_custom_threshold(self, client, auth_headers):
        """Test querying with custom days threshold."""
        for days in [3, 14, 30]:
            response = client.get(
                f'/api/sectors/retail/expiring-soon?days_threshold={days}',
                headers=auth_headers
            )

            assert response.status_code == 200
            result = response.get_json()
            assert result['threshold_days'] == days

    def test_get_expiring_soon_invalid_threshold(self, client, auth_headers):
        """Test with invalid threshold values."""
        invalid_thresholds = [0, -5, 91, 1000]

        for threshold in invalid_thresholds:
            response = client.get(
                f'/api/sectors/retail/expiring-soon?days_threshold={threshold}',
                headers=auth_headers
            )

            assert response.status_code == 400
            result = response.get_json()
            assert 'between 1 and 90' in result['error']

    def test_get_expiring_soon_sort_by_days(self, client, auth_headers):
        """Test sorting by days remaining."""
        response = client.get(
            '/api/sectors/retail/expiring-soon?sort_by=days',
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.get_json()
        products = result['expiring_products']

        # Verify sorted by days_remaining ascending
        days_list = [p['days_remaining'] for p in products]
        assert days_list == sorted(days_list)

    def test_get_expiring_soon_sort_by_quantity(self, client, auth_headers):
        """Test sorting by quantity."""
        response = client.get(
            '/api/sectors/retail/expiring-soon?sort_by=quantity',
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.get_json()
        products = result['expiring_products']

        # Verify sorted by quantity descending
        qty_list = [p['quantity'] for p in products]
        assert qty_list == sorted(qty_list, reverse=True)

    def test_get_expiring_soon_invalid_sort(self, client, auth_headers):
        """Test with invalid sort parameter."""
        response = client.get(
            '/api/sectors/retail/expiring-soon?sort_by=price',
            headers=auth_headers
        )

        assert response.status_code == 400
        result = response.get_json()
        assert 'sort_by must be' in result['error']


class TestDiscountSuggestion:
    """Tests for optimal discount calculation."""

    def test_suggest_discount_basic(self, client, auth_headers):
        """Test basic discount suggestion."""
        payload = {
            'product_id': 'prod_001',
            'current_price': 10.00,
            'quantity': 50,
            'days_remaining': 3,
            'margin_percent': 15,
        }

        response = client.post(
            '/api/sectors/retail/discount-suggestion',
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['suggested_price'] < result['current_price']
        assert result['discount_percent'] > 0
        assert result['discount_percent'] < 100

    def test_suggest_discount_urgency_factors(self, client, auth_headers):
        """Test that discount increases with urgency."""
        base_payload = {
            'product_id': 'prod_001',
            'current_price': 10.00,
            'quantity': 50,
            'margin_percent': 15,
        }

        discounts = {}
        for days in [1, 5, 10, 20]:
            payload = {**base_payload, 'days_remaining': days}
            response = client.post(
                '/api/sectors/retail/discount-suggestion',
                json=payload,
                headers=auth_headers
            )

            assert response.status_code == 200
            discounts[days] = response.get_json()['discount_percent']

        # Verify urgency: fewer days → larger discount
        assert discounts[1] > discounts[5]
        assert discounts[5] > discounts[10]
        assert discounts[10] > discounts[20]

    @pytest.mark.parametrize('days,expected_factor', [
        (1, 0.40),  # -40%
        (5, 0.30),  # -30%
        (10, 0.20), # -20%
        (20, 0.10), # -10%
    ])
    def test_suggest_discount_urgency_factor(self, days, expected_factor, client, auth_headers):
        """Test urgency factor calculation."""
        payload = {
            'product_id': 'prod_001',
            'current_price': 10.00,
            'quantity': 50,
            'days_remaining': days,
            'margin_percent': 15,
        }

        response = client.post(
            '/api/sectors/retail/discount-suggestion',
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['urgency_factor'] == expected_factor

    def test_suggest_discount_margin_preservation(self, client, auth_headers):
        """Test that suggested price maintains margin."""
        payload = {
            'product_id': 'prod_001',
            'current_price': 10.00,
            'quantity': 50,
            'days_remaining': 5,
            'margin_percent': 20,
        }

        response = client.post(
            '/api/sectors/retail/discount-suggestion',
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.get_json()

        # Verify margin is maintained
        cost = 10.00 / 1.20  # original price / (1 + margin%)
        expected_price = cost * 1.20  # cost × (1 + margin%)
        # Suggested price should be less due to discount
        assert result['suggested_price'] < expected_price
        assert result['suggested_price'] > cost  # But above cost

    def test_suggest_discount_invalid_inputs(self, client, auth_headers):
        """Test with invalid input values."""
        invalid_payloads = [
            {'current_price': -5, 'quantity': 50, 'days_remaining': 5},
            {'current_price': 10, 'quantity': -10, 'days_remaining': 5},
            {'current_price': 10, 'quantity': 50, 'days_remaining': -1},
            {'current_price': 10, 'quantity': 50, 'days_remaining': 5, 'margin_percent': 150},
        ]

        for payload in invalid_payloads:
            response = client.post(
                '/api/sectors/retail/discount-suggestion',
                json=payload,
                headers=auth_headers
            )

            assert response.status_code == 400


class TestInventoryReconciliation:
    """Tests for order quantity suggestions with expiry."""

    def test_reconcile_with_valid_expiry(self, client, auth_headers):
        """Test inventory reconciliation with valid expiration."""
        future_date = (datetime.now().date() + timedelta(days=15)).isoformat()

        payload = {
            'product_id': 'prod_001',
            'current_stock': 50,
            'forecasted_demand': 100,
            'lead_time_days': 7,
            'expiration_date': future_date,
            'safety_stock_percent': 20,
        }

        response = client.post(
            '/api/sectors/retail/inventory-reconciliation',
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert 'suggested_order_quantity' in result
        assert result['days_to_expiry'] == 15
        assert result['usable_stock'] == 50

    def test_reconcile_expired_stock(self, client, auth_headers):
        """Test with stock that expires during lead time."""
        past_date = (datetime.now().date() + timedelta(days=3)).isoformat()

        payload = {
            'product_id': 'prod_001',
            'current_stock': 50,
            'forecasted_demand': 100,
            'lead_time_days': 7,
            'expiration_date': past_date,
            'safety_stock_percent': 20,
        }

        response = client.post(
            '/api/sectors/retail/inventory-reconciliation',
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['usable_stock'] == 0  # Expired before new order
        assert 'CRITICAL' in result['expiry_warning']

    def test_reconcile_no_order_needed(self, client, auth_headers):
        """Test case where sufficient stock exists."""
        future_date = (datetime.now().date() + timedelta(days=30)).isoformat()

        payload = {
            'product_id': 'prod_001',
            'current_stock': 100,  # Plenty
            'forecasted_demand': 50,  # Low demand
            'lead_time_days': 7,
            'expiration_date': future_date,
            'safety_stock_percent': 20,
        }

        response = client.post(
            '/api/sectors/retail/inventory-reconciliation',
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['suggested_order_quantity'] == 0
        assert 'No order needed' in result['recommendation']

    def test_reconcile_invalid_date_format(self, client, auth_headers):
        """Test with invalid expiration date format."""
        payload = {
            'product_id': 'prod_001',
            'current_stock': 50,
            'forecasted_demand': 100,
            'lead_time_days': 7,
            'expiration_date': 'invalid-date',
            'safety_stock_percent': 20,
        }

        response = client.post(
            '/api/sectors/retail/inventory-reconciliation',
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 400
        result = response.get_json()
        assert 'Invalid expiration_date format' in result['error']

    def test_reconcile_missing_expiration(self, client, auth_headers):
        """Test with missing expiration date."""
        payload = {
            'product_id': 'prod_001',
            'current_stock': 50,
            'forecasted_demand': 100,
            'lead_time_days': 7,
            'safety_stock_percent': 20,
        }

        response = client.post(
            '/api/sectors/retail/inventory-reconciliation',
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 400
        result = response.get_json()
        assert 'expiration_date required' in result['error']


class TestHealthCheck:
    """Tests for service health."""

    def test_health_check_no_auth(self, client):
        """Test health endpoint without auth (public)."""
        response = client.get('/api/sectors/retail/health')

        assert response.status_code == 200
        result = response.get_json()
        assert result['status'] == 'healthy'
        assert result['service'] == 'retail-dluo'
        assert 'endpoints' in result

    def test_health_endpoints_listed(self, client):
        """Verify all endpoints are documented."""
        response = client.get('/api/sectors/retail/health')

        result = response.get_json()
        endpoints = result['endpoints']

        required = [
            'POST /import-dluo',
            'GET /expiring-soon',
            'POST /discount-suggestion',
            'POST /inventory-reconciliation',
            'GET /health'
        ]

        for endpoint in required:
            assert endpoint in endpoints


class TestAuthRequirements:
    """Tests for authentication enforcement."""

    def test_import_dluo_requires_auth(self, client):
        """Test that import endpoint requires auth."""
        response = client.post('/api/sectors/retail/import-dluo')
        assert response.status_code == 401

    def test_expiring_search_requires_auth(self, client):
        """Test that search endpoint requires auth."""
        response = client.get('/api/sectors/retail/expiring-soon')
        assert response.status_code == 401

    def test_discount_suggestion_requires_auth(self, client):
        """Test that discount endpoint requires auth."""
        response = client.post('/api/sectors/retail/discount-suggestion', json={})
        assert response.status_code == 401

    def test_reconciliation_requires_auth(self, client):
        """Test that reconciliation endpoint requires auth."""
        response = client.post('/api/sectors/retail/inventory-reconciliation', json={})
        assert response.status_code == 401
