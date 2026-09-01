import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Prophet avec fallback sklearn
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    from sklearn.linear_model import LinearRegression

# Jours fériés France
JOURS_FERIES_FR = [
    "01-01",  # Jour de l'An
    "05-01",  # Fête du Travail
    "05-08",  # Victoire 1945
    "07-14",  # Fête Nationale
    "08-15",  # Assomption
    "11-01",  # Toussaint
    "11-11",  # Armistice
    "12-25",  # Noël
]

# Périodes saisonnières connues (mois: coefficient)
SAISONNALITE_MENSUELLE = {
    1:  -0.10,  # Janvier — creux post-Noël
    2:  -0.05,  # Février — calme
    3:   0.02,  # Mars — reprise
    4:   0.05,  # Avril — Pâques, printemps
    5:   0.08,  # Mai — ponts, terrasses
    6:   0.12,  # Juin — début été
    7:   0.18,  # Juillet — vacances, tourisme
    8:   0.15,  # Août — pic estival
    9:   0.05,  # Septembre — rentrée
    10:  0.02,  # Octobre
    11: -0.03,  # Novembre — Toussaint, grisaille
    12:  0.20,  # Décembre — Noël, fêtes
}


def interpolate_missing(df):
    """
    Remplit les semaines manquantes et les valeurs aberrantes (0 isolés).
    Détecte les fermetures (suite de 0) et les distingue des données manquantes.
    """
    df = df.copy().sort_values("ds").reset_index(drop=True)
    if len(df) < 2:
        return df
    diffs = df["ds"].diff().dropna().dt.days
    freq_days = int(diffs.median())
    freq_days = max(1, min(freq_days, 30))
    full_range = pd.date_range(start=df["ds"].min(), end=df["ds"].max(), freq=f"{freq_days}D")
    df_full = pd.DataFrame({"ds": full_range})
    df_merged = df_full.merge(df, on="ds", how="left")
    zero_mask = df_merged["y"] == 0
    for i in range(1, len(df_merged) - 1):
        if zero_mask.iloc[i] and not zero_mask.iloc[i-1] and not zero_mask.iloc[i+1]:
            df_merged.loc[df_merged.index[i], "y"] = float("nan")
    df_merged["y"] = df_merged["y"].interpolate(method="linear", limit_direction="both")
    median_val = df_merged["y"].median()
    df_merged["y"] = df_merged["y"].fillna(median_val)
    return df_merged[["ds", "y"]].reset_index(drop=True)


def detect_anomalies(df):
    warnings_list = []
    if len(df) < 4:
        return warnings_list
    y = df["y"].values
    mean_y = np.mean(y)
    std_y = np.std(y)
    
    if std_y == 0:
        return warnings_list
    z_scores = np.abs((y - mean_y) / std_y)
    outlier_indices = np.where(z_scores > 2.5)[0]
    if len(outlier_indices) > 0:
        for idx in outlier_indices[:3]:
            val = y[idx]
            date = df["ds"].iloc[idx].strftime("%d/%m/%Y")
            if val > mean_y:
                warnings_list.append(f"Pic exceptionnel détecté le {date} ({val:.0f} vs moyenne {mean_y:.0f}) — événement particulier ?")
            else:
                warnings_list.append(f"Creux inhabituel le {date} ({val:.0f} vs moyenne {mean_y:.0f}) — fermeture ou incident ?")
    zero_runs = []
    count = 0
    for v in y:
        if v == 0:
            count += 1
        else:
            if count >= 2:
                zero_runs.append(count)
            count = 0
    if zero_runs:
        warnings_list.append(f"Période(s) de fermeture détectée(s) ({max(zero_runs)} semaines consécutives à 0) — les données ont été interpolées.")
    cv = std_y / (mean_y + 1e-9)
    if cv > 1.0:
        warnings_list.append(f"Données très variables (écart-type {std_y:.0f} pour une moyenne de {mean_y:.0f}) — prévisions indicatives.")
    return warnings_list


def get_seasonality_context(df):
    if len(df) < 12:
        return ""
    df = df.copy()
    df["month"] = df["ds"].dt.month
    monthly_avg = df.groupby("month")["y"].mean()
    if monthly_avg.empty:
        return ""
    peak_month = monthly_avg.idxmax()
    low_month = monthly_avg.idxmin()
    month_names = {1:"Janvier",2:"Février",3:"Mars",4:"Avril",5:"Mai",6:"Juin",
                   7:"Juillet",8:"Août",9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"}
    peak_ratio = monthly_avg[peak_month] / (monthly_avg[low_month] + 1e-9)
    if peak_ratio > 1.5:
        return f"Forte saisonnalité détectée : pic en {month_names.get(peak_month,'?')} (+{(peak_ratio-1)*100:.0f}% vs creux de {month_names.get(low_month,'?')})"
    return ""


class StockForecast:

    def __init__(self, df):
        self.df_raw = df.copy()
        self.df_raw["ds"] = pd.to_datetime(self.df_raw["ds"])
        self.df_raw["y"] = pd.to_numeric(self.df_raw["y"], errors="coerce").fillna(0)
        self.df = interpolate_missing(self.df_raw)
        self.anomalies = detect_anomalies(self.df)
        self.seasonality_context = get_seasonality_context(self.df)

    def fit_and_predict(self, periods=30):
        if PROPHET_AVAILABLE and len(self.df) >= 10:
            return self._prophet_forecast(periods)
        return self._linear_forecast(periods)

    def _prophet_forecast(self, periods):
        try:
            fr_holidays = []
            for year in range(self.df["ds"].dt.year.min(), self.df["ds"].dt.year.max() + 3):
                for mmdd in JOURS_FERIES_FR:
                    try:
                        fr_holidays.append({
                            "holiday": "jour_ferie_fr",
                            "ds": pd.Timestamp(f"{year}-{mmdd}"),
                            "lower_window": -1,
                            "upper_window": 1,
                        })
                    except Exception:
                        pass
            holidays_df = pd.DataFrame(fr_holidays)
            m = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=len(self.df) >= 14,
                daily_seasonality=False,
                holidays=holidays_df,
                seasonality_mode="multiplicative" if self.df["y"].std() / (self.df["y"].mean() + 1e-9) > 0.3 else "additive",
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
                interval_width=0.8,
            )
            m.fit(self.df[["ds", "y"]])
            future = m.make_future_dataframe(periods=periods, freq="D")
            forecast = m.predict(future)
            future_fc = forecast.tail(periods)
            accuracy = self._compute_accuracy_prophet(m, self.df)
            predictions = []
            for _, row in future_fc.iterrows():
                val = max(0, float(row["yhat"]))
                low = max(0, float(row["yhat_lower"]))
                high = max(0, float(row["yhat_upper"]))
                predictions.append({
                    "date": row["ds"].strftime("%Y-%m-%d"),
                    "forecast": round(val),
                    "confidence_lower": round(low) if low > 0.5 else "< 1",
                    "confidence_upper": round(high),
                })
            return {
                "predictions": predictions,
                "accuracy_score": round(accuracy, 3),
                "model": "prophet",
                "periods": periods,
                "anomalies": self.anomalies,
                "seasonality_context": self.seasonality_context,
            }
        except Exception:
            return self._linear_forecast(periods)

    def _compute_accuracy_prophet(self, model, df):
        try:
            if len(df) < 10:
                return 0.5
            n_test = min(5, len(df)//5)
            train = df.iloc[:-n_test]
            test = df.iloc[-n_test:]
            future = model.make_future_dataframe(periods=n_test, freq="D")
            fc = model.predict(future)
            fc_test = fc.tail(n_test)
            y_true = test["y"].values
            y_pred = fc_test["yhat"].values[:len(y_true)]
            mae = np.mean(np.abs(y_true - y_pred))
            mean_y = np.mean(np.abs(y_true)) + 1e-9
            return max(0.0, min(1.0, 1 - mae / mean_y))
        except Exception:
            return 0.6

    def _linear_forecast(self, periods):
        from sklearn.linear_model import LinearRegression
        df = self.df.copy().sort_values("ds")
        df["t"] = (df["ds"] - df["ds"].min()).dt.days
        X = df[["t"]].values
        y = df["y"].values
        reg = LinearRegression().fit(X, y)
        last_date = df["ds"].max()
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods)
        t_future = [(d - df["ds"].min()).days for d in future_dates]
        preds = reg.predict(np.array(t_future).reshape(-1, 1))
        std = float(np.std(y)) * 0.3
        predictions = []
        for i, (d, p) in enumerate(zip(future_dates, preds)):
            month = d.month
            seasonal_factor = 1 + SAISONNALITE_MENSUELLE.get(month, 0)
            val = max(0, float(p) * seasonal_factor)
            low = max(0, val - std)
            predictions.append({
                "date": d.strftime("%Y-%m-%d"),
                "forecast": round(val),
                "confidence_lower": round(low) if low > 0.5 else "< 1",
                "confidence_upper": round(val + std),
            })
        mean_y = np.mean(y) + 1e-9
        accuracy = max(0.0, min(1.0, 1 - (std / mean_y)))
        return {
            "predictions": predictions,
            "accuracy_score": round(accuracy, 3),
            "model": "linear_regression",
            "periods": periods,
            "anomalies": self.anomalies,
            "seasonality_context": self.seasonality_context,
        }


def detect_alerts(predictions, threshold_low=0.2, threshold_high=2.0):
    if not predictions:
        return []
    values = [p["forecast"] if isinstance(p["forecast"], (int, float)) else 0 for p in predictions]
    mean_val = np.mean(values)
    alerts = []
    for p in predictions:
        fc = p["forecast"] if isinstance(p["forecast"], (int, float)) else 0
        if mean_val > 0:
            ratio = fc / mean_val
            if ratio < threshold_low:
                alerts.append({"type": "stockout", "date": p["date"], "forecast": fc, "action": f"Stock critique prévu le {p['date']} ({fc} unités) — commandez en urgence"})
            elif ratio > threshold_high:
                alerts.append({"type": "surplus", "date": p["date"], "forecast": fc, "action": f"Surplus prévu le {p['date']} ({fc} unités) — réduisez les commandes"})
    return alerts[:5]
