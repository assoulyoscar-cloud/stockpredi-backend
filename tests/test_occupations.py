"""
Tests for Occupations API
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.occupation_categories import (
    get_occupation_list,
    get_occupation_config,
    validate_occupation,
    OCCUPATION_CATEGORIES
)

def test_occupation_list():
    """Test getting all occupations"""
    occupations = get_occupation_list()
    assert len(occupations) == 9, f"Expected 9 occupations, got {len(occupations)}"
    assert all('key' in occ for occ in occupations)
    assert all('name' in occ for occ in occupations)
    print(f"✓ All 9 occupations present")

def test_occupation_config():
    """Test getting occupation config"""
    config = get_occupation_config("restaurateur")
    assert config is not None
    assert "forecasting_config" in config
    assert "business_metrics" in config
    print(f"✓ Restaurateur config complete")

def test_restaurateur_vs_paysagiste():
    """Test that restaurateur and paysagiste differ"""
    resto = get_occupation_config("restaurateur")
    paysa = get_occupation_config("paysagiste_pepinieriste")
    
    assert resto.get("default_forecast_period") == 30
    assert paysa.get("default_forecast_period") == 90
    assert resto.get("forecasting_config", {}).get("seasonality") == "weekly"
    assert paysa.get("forecasting_config", {}).get("seasonality") == "monthly"
    print(f"✓ Restaurateur (weekly, 30d) vs Paysagiste (monthly, 90d) differ correctly")

def test_validate_occupation():
    """Test occupation validation"""
    assert validate_occupation("restaurateur") == True
    assert validate_occupation("pharmacie") == True
    assert validate_occupation("invalid") == False
    print(f"✓ Occupation validation working")

def test_all_occupations_have_required_fields():
    """Test all occupations have required fields"""
    for key, config in OCCUPATION_CATEGORIES.items():
        assert "name" in config
        assert "forecasting_config" in config
        assert "business_metrics" in config
        assert "key_products" in config
    print(f"✓ All {len(OCCUPATION_CATEGORIES)} occupations have required fields")

if __name__ == "__main__":
    print("\n🧪 Running Occupations Tests\n" + "="*50)
    test_occupation_list()
    test_occupation_config()
    test_restaurateur_vs_paysagiste()
    test_validate_occupation()
    test_all_occupations_have_required_fields()
    print("\n" + "="*50)
    print("✅ ALL TESTS PASSED")
