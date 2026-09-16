"""
Tests for Export Routes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

def test_export_status():
    """Test export status endpoint"""
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    
    response = client.get('/api/export/status')
    assert response.status_code == 200
    data = response.get_json()
    assert 'google_drive_configured' in data
    print("✓ Export status endpoint working")

def test_occupations_routes_registered():
    """Test occupations blueprint is registered"""
    app = create_app()
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    occ_routes = [r for r in routes if '/api/occupations' in r]
    assert len(occ_routes) > 0
    assert '/api/occupations/list' in routes
    print(f"✓ Occupations routes registered: {len(occ_routes)} endpoints")

def test_occupations_list():
    """Test occupations list endpoint"""
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    
    response = client.get('/api/occupations/list')
    assert response.status_code == 200
    data = response.get_json()
    assert data.get('count') == 9
    print(f"✓ Occupations list returns 9 occupations")

if __name__ == "__main__":
    print("\n🧪 Running Export Routes Tests\n" + "="*50)
    test_export_status()
    test_occupations_routes_registered()
    test_occupations_list()
    print("\n" + "="*50)
    print("✅ ALL TESTS PASSED")
