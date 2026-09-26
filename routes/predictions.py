from flask import Blueprint, request, jsonify
import pandas as pd
import numpy as np
from middleware.auth_middleware import auth_required
from models.forecast import StockForecast, detect_alerts
from models.recommendations import OllamaRecommender, compute_trend, compute_cv

predictions_bp = Blueprint("predictions", __name__)


class DataError(ValueError):
    """Donnees envoyees invalides : message redige pour l'utilisateur."""


def parse_data(raw: list) -> pd.DataFrame:
    """Valide et convertit les donnees entrantes en DataFrame Prophet."""
    if not raw or not isinstance(raw, list):
        raise DataError("data doit etre une liste non vide")
    try:
        df = pd.DataFrame(raw)
    except Exception:
        raise DataError("Format de donnees invalide : liste de {ds, y} attendue")
    if "ds" not in df.columns or "y" not in df.columns:
        raise DataError("Chaque enregistrement doit avoir 'ds' (date) et 'y' (quantite)")
    df["ds"] = pd.to_datetime(df["ds"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0)
    df = df.dropna(subset=["ds"]).sort_values("ds")
    if len(df) < 7:
        raise DataError("Minimum 7 points de donnees requis pour une prevision fiable")
    return df[["ds", "y"]]


@predictions_bp.route("/forecast", methods=["POST", "OPTIONS"])
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
    except DataError as e:
        return jsonify({"error": str(e)}), 400  # message ecrit par nous, pas une exception brute

    try:
        forecaster = StockForecast(df)
        result = forecaster.fit_and_predict(periods=periods)
        alerts = detect_alerts(result["predictions"])
        result["alerts"] = alerts
        result["data_points"] = len(df)
        return jsonify(result), 200
    except Exception as e:
        print(f"routes/predictions.py: Erreur forecasting: {type(e).__name__}: {e}")
        return jsonify({"error": "Erreur forecasting"}), 500


@predictions_bp.route("/recommendations", methods=["POST", "OPTIONS"])
@auth_required
def recommendations():
    """POST /api/predictions/recommendations
    Body: { "data": [...], "product_name": "Widget A", "periods": 30 }
    """
    try:
        body = request.get_json(silent=True) or {}
        raw = body.get("data", [])
        product_name = body.get("product_name", "Produit")
        sector = body.get("sector") or "general"
        sector_params = body.get("sector_params") or {}
        if not isinstance(sector_params, dict):
            sector_params = {}
        periods = int(body.get("periods", 30))
        periods = max(7, min(periods, 365))

        try:
            df = parse_data(raw)
        except DataError as e:
            return jsonify({"error": str(e)}), 400  # message ecrit par nous, pas une exception brute

        # 1. Forecast
        forecaster = StockForecast(df)
        forecast_result = forecaster.fit_and_predict(periods=periods)
        alerts = detect_alerts(forecast_result["predictions"])
        preds = forecast_result["predictions"]

        # 2. Context pour le moteur (cles lues par OllamaRecommender)
        accuracy = forecast_result.get("accuracy_score", 0) or 0
        avg_forecast = float(np.mean([p["forecast"] for p in preds])) if preds else 0
        trend = compute_trend(preds)
        context = {
            "product_name": product_name,
            "alerts": alerts,
            "accuracy": accuracy,
            "avg_forecast": avg_forecast,
            "trend": trend,
            "cv": compute_cv(df),
            "seasonality_context": forecast_result.get("seasonality_context", ""),
            "sector": sector,
            "sector_params": sector_params,
            "data_points": len(df),
        }

        # 3. Recommandations IA (with better error handling)
        try:
            recommender = OllamaRecommender()
            # recommend() : get_recommendations() n'existe pas -> le fallback s'affichait toujours
            recs = recommender.recommend(context)
            if accuracy < 0.40:
                recs["summary"] = f"Donnees tres irregulieres — precision {accuracy:.0%}. Les previsions sont peu fiables. Enrichissez votre historique."
            elif accuracy < 0.60:
                recs["summary"] = f"Precision moderee ({accuracy:.0%}). {len(alerts)} alerte(s). Tendance : {trend}. A confirmer avec plus de donnees."
            else:
                recs["summary"] = f"{len(alerts)} alerte(s) detectee(s). Tendance {trend}. Precision modele : {accuracy:.0%}."
        except Exception as e:
            # Fallback if recommendations fail
            print(f"recommendations: moteur en echec: {type(e).__name__}: {e}")
            recs = {
                "recommendations": [{
                    "priority": "OK",
                    "action": "Consulter l'historique",
                    "detail": "Recommandations générées par le moteur StockPredi"
                }],
                "summary": "Analyse basique activee",
                "source": "fallback"
            }

        return jsonify({
            "forecast": forecast_result,
            "alerts": alerts,
            "recommendations": recs.get("recommendations", []),
            "summary": recs.get("summary", ""),
            "ai_source": recs.get("ai_source") or recs.get("source", "rules"),
            "trend": trend,
            "product_name": product_name
        }), 200
    except Exception as e:
        # Trace dans les logs Render, pas dans la reponse envoyee au navigateur
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Erreur recommandations"}), 500
