from flask import Blueprint, request, jsonify
import pandas as pd
import numpy as np
from middleware.auth_middleware import auth_required
from models.forecast import StockForecast, detect_alerts
from models.recommendations import OllamaRecommender, compute_trend

predictions_bp = Blueprint("predictions", __name__)


def parse_data(raw: list) -> pd.DataFrame:
    """Valide et convertit les donnees entrantes en DataFrame Prophet."""
    if not raw or not isinstance(raw, list):
        raise ValueError("data doit etre une liste non vide")
    df = pd.DataFrame(raw)
    if "ds" not in df.columns or "y" not in df.columns:
        raise ValueError("Chaque enregistrement doit avoir 'ds' (date) et 'y' (quantite)")
    df["ds"] = pd.to_datetime(df["ds"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
    df = df.dropna(subset=["ds"]).sort_values("ds")
    if len(df) < 7:
        raise ValueError("Minimum 7 points de donnees requis pour une prevision fiable")
    return df[["ds", "y"]]


@predictions_bp.route("/forecast", methods=["POST"])
@auth_required
def forecast():
    """POST /api/predictions/forecast
    Body: { "data": [{"ds": "2024-01-01", "y": 42}, ...], "periods": 30 }
    """
    body = request.get_json(silent=True) or {}
    raw = body.get("data", [])
    periods = int(body.get("periods", 30))
    periods = max(7, min(periods, 365))

    try:
        df = parse_data(raw)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    try:
        forecaster = StockForecast(df)
        result = forecaster.fit_and_predict(periods=periods)
        alerts = detect_alerts(result["predictions"])
        result["alerts"] = alerts
        result["data_points"] = len(df)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": "Erreur forecasting", "detail": str(e)}), 500


@predictions_bp.route("/recommendations", methods=["POST"])
@auth_required
def recommendations():
    """POST /api/predictions/recommendations
    Body: { "data": [...], "product_name": "Widget A", "periods": 30 }
    """
    body = request.get_json(silent=True) or {}
    raw = body.get("data", [])
    product_name = body.get("product_name", "Produit")
    periods = int(body.get("periods", 30))
    periods = max(7, min(periods, 365))

    try:
        df = parse_data(raw)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    try:
        # 1. Forecast
        forecaster = StockForecast(df)
        forecast_result = forecaster.fit_and_predict(periods=periods)
        alerts = detect_alerts(forecast_result["predictions"])
        preds = forecast_result["predictions"]

        # 2. Context pour Ollama
        avg_forecast = float(np.mean([p["forecast"] for p in preds])) if preds else 0
        trend = compute_trend(preds)
        context = {
            "product_name": product_name,
            "alerts": alerts,
            "accuracy_score": forecast_result.get("accuracy_score", 0),
            "avg_forecast": avg_forecast,
            "trend": trend
        }

        # 3. Recommandations IA
        recommender = OllamaRecommender()
        recs = recommender.get_recommendations(context)

        return jsonify({
            "forecast": forecast_result,
            "alerts": alerts,
            "recommendations": recs.get("recommendations", []),
            "summary": recs.get("summary", ""),
            "ai_source": recs.get("source", "rules"),
            "trend": trend,
            "product_name": product_name
        }), 200
    except Exception as e:
        return jsonify({"error": "Erreur recommandations", "detail": str(e)}), 500
