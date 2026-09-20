"""
tests/test_retail.py - Unit tests for retail sector module
"""
import pytest
import json
from datetime import datetime


@pytest.fixture
def client(test_app):
    """Create test client"""
    return test_app.test_client()


@pytest.fixture
def auth_headers(client):
    """Get auth headers for testing"""
    # For tests, we mock the auth decorator
    return {"Authorization": "Bearer test_token"}


def test_get_products(client, auth_headers):
    """Test GET /api/sectors/retail/products"""
    response = client.get(
        "/api/sectors/retail/products",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "categories" in data
    assert len(data["categories"]) == 8
    assert "clothing" in data["categories"]


def test_seasonal_factors_all_months(client, auth_headers):
    """Test GET /api/sectors/retail/seasonal-factors returns all months"""
    response = client.get(
        "/api/sectors/retail/seasonal-factors",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "seasonal_factors" in data
    assert len(data["seasonal_factors"]) == 12


def test_seasonal_factors_january(client, auth_headers):
    """Test seasonal factor for January (-20%)"""
    response = client.get(
        "/api/sectors/retail/seasonal-factors?month=1",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["factor"] == -0.20
    assert data["multiplier"] == 0.80


def test_seasonal_factors_december(client, auth_headers):
    """Test seasonal factor for December (+150%)"""
    response = client.get(
        "/api/sectors/retail/seasonal-factors?month=12",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["factor"] == 1.50
    assert data["multiplier"] == 2.50


def test_seasonal_factors_invalid_month(client, auth_headers):
    """Test invalid month parameter"""
    response = client.get(
        "/api/sectors/retail/seasonal-factors?month=13",
        headers=auth_headers
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_apply_promotion_flash(client, auth_headers):
    """Test flash promotion impact"""
    payload = {
        "base_forecast": 1000,
        "promotion_type": "flash",
        "discount_percent": 25,
        "current_month": 7  # July (high season)
    }
    response = client.post(
        "/api/sectors/retail/apply-promotion",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["base_forecast"] == 1000
    assert data["promotion_type"] == "flash"
    # July has +30% seasonal factor
    assert data["seasonal_multiplier"] == 1.30
    # Flash adds +200%
    assert data["adjusted_forecast"] > data["seasonal_forecast"]


def test_apply_promotion_weekly(client, auth_headers):
    """Test weekly promotion impact"""
    payload = {
        "base_forecast": 1000,
        "promotion_type": "weekly",
        "discount_percent": 15,
        "current_month": 11  # November (Black Friday season)
    }
    response = client.post(
        "/api/sectors/retail/apply-promotion",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["promotion_type"] == "weekly"
    assert data["seasonal_factor"] == 0.70  # +70% for November


def test_apply_promotion_seasonal(client, auth_headers):
    """Test seasonal promotion type"""
    payload = {
        "base_forecast": 1000,
        "promotion_type": "seasonal",
        "discount_percent": 50,
        "current_month": 2  # February (baseline)
    }
    response = client.post(
        "/api/sectors/retail/apply-promotion",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["seasonal_multiplier"] == 1.0  # February is baseline


def test_apply_promotion_invalid_type(client, auth_headers):
    """Test invalid promotion type"""
    payload = {
        "base_forecast": 1000,
        "promotion_type": "invalid",
        "discount_percent": 25
    }
    response = client.post(
        "/api/sectors/retail/apply-promotion",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_apply_promotion_missing_forecast(client, auth_headers):
    """Test missing base_forecast"""
    payload = {
        "promotion_type": "flash",
        "discount_percent": 25
    }
    response = client.post(
        "/api/sectors/retail/apply-promotion",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 400


def test_apply_promotion_negative_discount(client, auth_headers):
    """Test invalid discount percent"""
    payload = {
        "base_forecast": 1000,
        "promotion_type": "flash",
        "discount_percent": -10
    }
    response = client.post(
        "/api/sectors/retail/apply-promotion",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 400


def test_forecast_demand_clothing_summer(client, auth_headers):
    """Test demand forecast for clothing in summer"""
    payload = {
        "product_category": "clothing",
        "base_demand": 500,
        "current_month": 7  # July: +30%
    }
    response = client.post(
        "/api/sectors/retail/forecast",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["product"] == "clothing"
    assert data["forecast"] > data["base_demand"]


def test_forecast_demand_electronics_december(client, auth_headers):
    """Test demand forecast for electronics in December (peak)"""
    payload = {
        "product_category": "electronics",
        "base_demand": 1000,
        "current_month": 12  # December: +150%
    }
    response = client.post(
        "/api/sectors/retail/forecast",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 200
    data = response.get_json()
    # December multiplier = 2.5 (1 + 1.50)
    assert data["forecast"] == pytest.approx(2500, rel=0.01)


def test_forecast_demand_with_promotion(client, auth_headers):
    """Test demand forecast with promotion applied"""
    payload = {
        "product_category": "toys",
        "base_demand": 500,
        "current_month": 11,  # November: +70%
        "promotion": {
            "type": "flash",
            "discount": 40
        }
    }
    response = client.post(
        "/api/sectors/retail/forecast",
        headers=auth_headers,
        json=payload
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["forecast"] > 0


def test_all_seasonal_months_positive(client, auth_headers):
    """Test all 12 months have valid multipliers"""
    for month in range(1, 13):
        response = client.get(
            f"/api/sectors/retail/seasonal-factors?month={month}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "multiplier" in data
        assert data["multiplier"] >= 0


def test_health_check(client):
    """Test health endpoint doesn't require auth"""
    response = client.get("/api/sectors/retail/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "retail"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
