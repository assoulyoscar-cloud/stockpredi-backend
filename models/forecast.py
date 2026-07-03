import pandas as pd
import numpy as np
import json
from datetime import datetime

# Prophet avec fallback sklearn si non installe
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    from sklearn.linear_model import LinearRegression


class StockForecast:
    """Previsions de stock avec Prophet (ou LinearRegression fallback)."""

    def __init__(self, df: pd.DataFrame):
        """
        df doit avoir colonnes : ds (date), y (quantite)
        product_id optionnel
        """
        self.df = df.copy()
        self.df["ds"] = pd.to_datetime(self.df["ds"])
        self.df["y"] = pd.to_numeric(self.df["y"], errors="coerce").fillna(0)
        self.model = None
        self.forecast = None

    def fit_and_predict(self, periods: int = 30):
        """Entraine le modele et retourne les previsions."""
        if PROPHET_AVAILABLE:
            return self._prophet_forecast(periods)
        return self._linear_forecast(periods)

    def _prophet_forecast(self, periods: int):
        m = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            interval_width=0.8
        )
        m.fit(self.df[["ds", "y"]])
        future = m.make_future_dataframe(periods=periods)
        forecast = m.predict(future)
        self.model = m
        self.forecast = forecast
        return self._format_output(forecast, periods)

    def _linear_forecast(self, periods: int):
        """Fallback simple si Prophet pas installe."""
        df = self.df.copy().sort_values("ds")
        df["t"] = (df["ds"] - df["ds"].min()).dt.days
        X = df[["t"]].values
        y = df["y"].values
        reg = LinearRegression().fit(X, y)

        last_date = df["ds"].max()
        future_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1), periods=periods
        )
        t_future = [(d - df["ds"].min()).days for d in future_dates]
        preds = reg.predict(np.array(t_future).reshape(-1, 1))
        std = float(np.std(y)) * 0.3

        results = []
        for i, (d, p) in enumerate(zip(future_dates, preds)):
            val = max(0, float(p))
            results.append({
                "date": d.strftime("%Y-%m-%d"),
                "forecast": round(val, 2),
                "confidence_lower": round(max(0, val - std), 2),
                "confidence_upper": round(val + std, 2)
            })
        return {
            "predictions": results,
            "accuracy_score": round(1 - (std / (np.mean(y) + 1e-9)), 3),
            "model": "linear_regression",
            "periods": periods
        }

    def _format_output(self, forecast, periods: int):
        future = forecast.tail(periods)
        predictions = []
        for _, row in future.iterrows():
            predictions.append({
                "date": row["ds"].strftime("%Y-%m-%d"),
                "forecast": round(max(0, row["yhat"]), 2),
                "confidence_lower": round(max(0, row["yhat_lower"]), 2),
                "confidence_upper": round(max(0, row["yhat_upper"]), 2)
            })

        # Calcul accuracy sur historique (MAE-based)
        hist = forecast.head(len(self.df))
        mae = float(np.mean(np.abs(
            self.df["y"].values - hist["yhat"].values
        )))
        mean_y = float(self.df["y"].mean()) + 1e-9
        accuracy = round(max(0, 1 - mae / mean_y), 3)

        return {
            "predictions": predictions,
            "accuracy_score": accuracy,
            "model": "prophet",
            "periods": periods
        }


def detect_alerts(predictions: list, threshold_low: float = 0.2,
                  threshold_high: float = 2.0) -> list:
    """Detecte ruptures et surplus potentiels."""
    if not predictions:
        return []

    values = [p["forecast"] for p in predictions]
    mean_val = np.mean(values)
    alerts = []

    for p in predictions:
        if mean_val > 0:
            ratio = p["forecast"] / mean_val
            if ratio < threshold_low:
                alerts.append({
                    "type": "stockout",
                    "date": p["date"],
                    "forecast": p["forecast"],
                    "action": f"Commander urgence le {p['date']} — stock critique prevu ({p['forecast']:.0f} unites)"
                })
            elif ratio > threshold_high:
                alerts.append({
                    "type": "surplus",
                    "date": p["date"],
                    "forecast": p["forecast"],
                    "action": f"Reduire commandes pour {p['date']} — surplus prevu ({p['forecast']:.0f} unites)"
                })
    return alerts
