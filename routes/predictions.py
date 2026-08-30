from flask import Blueprint, request, jsonify
import pandas as pd
import numpy as np
from middleware.auth_middleware import auth_required
from models.forecast import StockForecast, detect_alerts
from models.recommendations import OllamaRecommender, compute_trend, compute_cv

predictions_bp = Blueprint("predictions", __name__)


def parse_data(raw: list) -> pd.DataFrame:
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
    return df[["ds", "y"]].reset_index(drop=True)


@predictions_bp.route("/forecast", methods=["POST"])
@auth_required
def forecast(user_id: str):
    try:
        body = request.get_json() or {}
        raw = body.get("data", [])
        periods = int(body.get("periods", 30))
        df = parse_data(raw)
        model = StockForecast(df)
        result = model.fit_and_predict(periods=periods)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erreur interne: {str(e)}"}), 500


@predictions_bp.route("/recommendations", methods=["POST"])
@auth_required
def recommendations(user_id: str):
    try:
        body = request.get_json() or {}
        raw = body.get("data", [])
        product_name = body.get("product_name", "Mon produit")
        periods = int(body.get("periods", 30))

        df = parse_data(raw)

        model = StockForecast(df)
        forecast_result = model.fit_and_predict(periods=periods)
        accuracy_score = forecast_result.get("accuracy_score", 0)

        predictions_list = forecast_result.get("predictions", [])
        alerts = detect_alerts(predictions_list, df)

        trend = compute_trend(df)
        cv = compute_cv(df)

        recommender = OllamaRecommender()
        context = {
            "product_name": product_name,
            "alerts": alerts,
            "accuracy": accuracy_score,
            "trend": trend,
            "cv": cv,
            "data_points": len(df),
        }
        rec_result = recommender.recommend(context)

        if accuracy_score < 0.40:
            summary = f"Donnees tres irregulières — precision {accuracy_score:.0%}. Les previsions sont peu fiables. Enrichissez votre historique."
        elif accuracy_score < 0.60:
            summary = f"Precision moderee ({accuracy_score:.0%}). {len(alerts)} alerte(s). Tendance : {trend}. A confirmer avec plus de donnees."
        elif alerts:
            summary = f"{len(alerts)} alerte(s) detectee(s). Tendance {trend}. Precision {accuracy_score:.0%}."
        else:
            summary = f"0 alerte(s) detectee(s). Tendance {trend}. Precision modele : {accuracy_score:.0%}."

        return jsonify({
            "summary": summary,
            "trend": trend,
            "recommendations": rec_result.get("recommendations", []),
            "ai_source": rec_result.get("ai_source", "rules"),
            "alerts": alerts,
            "forecast": {
                **forecast_result,
                "data_points": len(df),
            },
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erreur interne: {str(e)}"}), 500
