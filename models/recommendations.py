import requests
import json
import numpy as np
from config import Config


class OllamaRecommender:

    def __init__(self):
        self.base_url = Config.OLLAMA_URL
        self.model = Config.OLLAMA_MODEL
        self.timeout = 30

    def _is_ollama_available(self):
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def _build_prompt(self, context):
        product = context.get("product_name", "produit")
        alerts = context.get("alerts", [])
        accuracy = context.get("accuracy", 0)
        trend = context.get("trend", "stable")
        cv = context.get("cv", 0)
        return f"""Tu es un expert en gestion de stock pour PME françaises.

Produit: {product}
Tendance: {trend}
Précision modèle: {accuracy:.0%}
Coefficient de variation (variabilité): {cv:.0%}
Alertes: {json.dumps(alerts, ensure_ascii=False)}

Donne 3 recommandations concrètes et adaptées à la situation réelle.
Si la précision est faible (<50%), signale-le clairement.
Si les données sont très variables (cv>80%), avertis le gérant.
Format JSON: [{{"action":"...", "detail":"...", "priority":"OK|ATTENTION|CRITIQUE"}}]
Réponse JSON uniquement."""

    def _ollama_recommend(self, context):
        prompt = self._build_prompt(context)
        payload = {"model": self.model, "prompt": prompt, "stream": False, "format": "json"}
        r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        r.raise_for_status()
        raw = r.json().get("response", "[]")
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    def _smart_fallback(self, context):
        alerts = context.get("alerts", [])
        accuracy = context.get("accuracy", 0)
        trend = context.get("trend", "stable")
        cv = context.get("cv", 0)
        seasonality = context.get("seasonality_context", "")
        recs = []
        if accuracy < 0.40:
            recs.append({"action": "Données trop irrégulières pour une prévision fiable", "detail": f"Précision du modèle : {accuracy:.0%}. Vos données varient trop fortement — enrichissez l'historique ou vérifiez vos chiffres.", "priority": "CRITIQUE"})
        elif accuracy < 0.60:
            recs.append({"action": "Prévision à prendre avec précaution", "detail": f"Précision de {accuracy:.0%} — les prévisions sont indicatives. Augmentez votre historique.", "priority": "ATTENTION"})
        if cv > 0.80:
            recs.append({"action": "Forte variabilité détectée", "detail": f"Vos ventes fluctuent de {cv:.0%} en moyenne. Vérifiez si des événements exceptionnels faussent l'analyse.", "priority": "ATTENTION"})
        stockouts = [a for a in alerts if a.get("type") == "stockout"]
        surpluses = [a for a in alerts if a.get("type") == "surplus"]
        if stockouts:
            recs.append({"action": f"Risque de rupture détecté ({len(stockouts)} période(s))", "detail": f"Première rupture prévue le {stockouts[0].get('date','?')}. Passez commande dès maintenant.", "priority": "CRITIQUE"})
        if surpluses:
            recs.append({"action": f"Surplus prévu ({len(surpluses)} période(s))", "detail": f"Réduisez vos commandes pour la période du {surpluses[0].get('date','?')}.", "priority": "ATTENTION"})
        if trend == "hausse" and accuracy >= 0.60:
            recs.append({"action": "Tendance à la hausse — Anticipez vos approvisionnements", "detail": "Vos ventes progressent. Augmentez légèrement vos commandes.", "priority": "OK"})
        elif trend == "baisse" and accuracy >= 0.60:
            recs.append({"action": "Tendance à la baisse — Réduisez vos stocks", "detail": "Vos ventes diminuent. Limitez vos commandes pour éviter les invendus.", "priority": "ATTENTION"})
        elif accuracy >= 0.60 and not stockouts and not surpluses:
            recs.append({"action": "Situation stable — Maintenez votre rythme actuel", "detail": "Aucune alerte détectée. Continuez sur cette lancée.", "priority": "OK"})
        if seasonality and accuracy >= 0.55 and not any(r['priority'] == 'CRITIQUE' for r in recs):
            recs.append({"action": seasonality, "detail": "Anticipez vos commandes en fonction de ces variations saisonnières.", "priority": "OK"})
        if not recs:
            recs.append({"action": "Données insuffisantes pour une recommandation précise", "detail": "Ajoutez plus de données historiques (minimum 20 semaines recommandées).", "priority": "ATTENTION"})
        return recs[:4]

    def recommend(self, context):
        if self._is_ollama_available():
            try:
                recs = self._ollama_recommend(context)
                if recs:
                    return {"recommendations": recs, "ai_source": "ollama"}
            except Exception:
                pass
        recs = self._smart_fallback(context)
        return {"recommendations": recs, "ai_source": "rules"}


def compute_trend(df):
    if df is None or len(df) < 4:
        return "stable"
    y = df["y"].values
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]
    mean_y = y.mean()
    if mean_y == 0:
        return "stable"
    relative_slope = slope / mean_y
    if relative_slope > 0.015:
        return "hausse"
    elif relative_slope < -0.015:
        return "baisse"
    return "stable"


def compute_cv(df):
    if df is None or len(df) < 2:
        return 0.0
    mean = df["y"].mean()
    if mean == 0:
        return 0.0
    return float(df["y"].std() / mean)
