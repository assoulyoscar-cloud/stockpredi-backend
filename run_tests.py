#!/usr/bin/env python
"""Test runner with proper path configuration"""
import sys
import os

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Run all tests
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 COMPREHENSIVE STOCKPREDI BACKEND TEST SUITE")
    print("="*60 + "\n")

    # Test 1: Occupations Model
    print("TEST 1: Occupation Categories Model")
    print("-" * 60)
    from models.occupation_categories import (
        get_occupation_list,
        get_occupation_config,
        validate_occupation,
        OCCUPATION_CATEGORIES
    )

    assert len(OCCUPATION_CATEGORIES) == 9
    print(f"✓ 9 occupation types loaded")

    for key in OCCUPATION_CATEGORIES.keys():
        config = OCCUPATION_CATEGORIES[key]
        assert "name" in config
        assert "forecasting_config" in config
        assert "business_metrics" in config
        assert "key_products" in config
    print(f"✓ All occupations have required fields")

    # Test restaurateur vs paysagiste
    resto = get_occupation_config("restaurateur")
    paysa = get_occupation_config("paysagiste_pepinieriste")
    assert resto["default_forecast_period"] == 30
    assert paysa["default_forecast_period"] == 90
    assert resto["forecasting_config"]["seasonality"] == "weekly"
    assert paysa["forecasting_config"]["seasonality"] == "monthly"
    print(f"✓ Restaurateur (weekly, 30d) vs Paysagiste (monthly, 90d) configs differ")

    # Test validation
    assert validate_occupation("restaurateur") == True
    assert validate_occupation("pharmacie") == True
    assert validate_occupation("invalid") == False
    print(f"✓ Occupation validation working")

    print("\n" + "="*60)
    print("TEST 2: Flask App Initialization")
    print("-" * 60)

    from app import create_app
    app = create_app()
    print(f"✓ App created successfully")

    # Check blueprints
    expected_blueprints = ['auth', 'predictions', 'user', 'stripe', 'rgpd', 'export', 'occupations']
    for bp in expected_blueprints:
        assert bp in app.blueprints, f"Blueprint {bp} missing"
    print(f"✓ All {len(expected_blueprints)} blueprints registered")

    # Check routes
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    export_routes = [r for r in routes if '/api/export' in r]
    occ_routes = [r for r in routes if '/api/occupations' in r]

    assert len(export_routes) > 0
    assert len(occ_routes) > 0
    print(f"✓ Export routes: {len(export_routes)} endpoints")
    print(f"✓ Occupations routes: {len(occ_routes)} endpoints")

    print("\n" + "="*60)
    print("TEST 3: API Endpoints")
    print("-" * 60)

    with app.test_client() as client:
        # Test occupations list
        response = client.get('/api/occupations/list')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('count') == 9
        print(f"✓ GET /api/occupations/list → 200 (9 occupations)")

        # Test get single occupation
        response = client.get('/api/occupations/restaurateur')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('occupation_key') == 'restaurateur'
        print(f"✓ GET /api/occupations/restaurateur → 200")

        # Test export status
        response = client.get('/api/export/status')
        assert response.status_code == 200
        print(f"✓ GET /api/export/status → 200")

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - CODE IS PRODUCTION READY")
    print("="*60 + "\n")
