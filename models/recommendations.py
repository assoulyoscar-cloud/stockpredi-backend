import requests
import json
import numpy as np
from config import Config


class OllamaRecommender:

    def __init__(self):
        self.base_url = Config.OLLAMA_URL
        self.model = Config.OLLAMA_MODEL
        self.timeout = 30

    def _is_ollama_available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def _build_prompt(self, context: dict) -> str:
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
Si la précision est faible (<50%), signale-le clairement et déconseille de trop se fier aux prévisions.
Si les données sont très variables (cv>80%), avertis le gérant.
Format JSON: [{{"action":"...", "detail":"...", "priority":"OK|ATTENTION|CRITIQUE"}}]
Réponse JSON uniquement, sans texte autour."""

    def _ollama_recommend(self, context: dict) -> list:
        prompt = self._build_prompt(context)
        payload = {"model": self.model, "prompt": prompt, "stream": False, "format": "json"}
        r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        r.raise_for_status()
        raw = r.json().get("response", "[]")
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    def _smart_fallback(self, context: dict) -> list:
        alerts = context.get("alerts", [])
        accuracy = context.get("accuracy", 0)
        trend = context.get("trend", "stable")
        cv = context.get("cv", 0)
        recs = []

        if accuracy < 0.40:
            recs.append({
                "action": "Donnees trop irregulières pour une prevision fiable",
                "detail": f"Precision du modele : {accuracy:.0%}. Vos donnees varient trop fortement — enrichissez l'historique ou verifiez vos chiffres.",
                "priority": "CRITIQUE"
            })
        elif accuracy < 0.60:
            recs.append({
                "action": "Prevision a prendre avec precaution",
                "detail": f"Precision de {accuracy:.0%} — Les previsions sont indicatives. Augmentez votre historique pour de meilleurs resultats.",
                "priority": "ATTENTION"
            })

        if cv > 0.80:
            recs.append({
                "action": "Forte variabilite detectee dans vos donnees",
                "detail": f"Vos ventes fluctuent de {cv:.0%} en moyenne. Verifiez si des evenements exceptionnels faussent l'analyse.",
                "priority": "ATTENTION"
            })

        stockouts = [a for a in alerts if a.get("type") == "stockout"]
        surpluses = [a for a in alerts if a.get("type") == "surplus"]

        if stockouts:
            recs.append({
                "action": f"Risque de rupture detecte ({len(stockouts)} periode(s))",
                "detail": f"Premiere rupture prevue le {stockouts[0].get('date','?')}. Passez commande des maintenant.",
                "priority": "CRITIQUE"
            })
        if surpluses:
            recs.append({
                "action": f"Surplus prevu ({len(surpluses)} periode(s))",
                "detail": f"Reduisez vos commandes pour la periode du {surpluses[0].get('date','?')}.",
                "priority": "ATTENTION"
            })

        if trend == "hausse" and accuracy >= 0.60:
            recs.append({
                "action": "Tendance a la hausse — Anticipez vos approvisionnements",
                "detail": "Vos ventes progressent. Augmentez legerement vos commandes pour eviter les ruptures.",
                "priority": "OK"
            })
        elif trend == "baisse" and accuracy >= 0.60:
            recs.append({
                "action": "Tendance a la baisse — Reduisez vos stocks",
                "detail": "Vos ventes diminuent. Limitez vos commandes pour eviter les invendus.",
                "priority": "ATTENTION"
            })
        elif accuracy >= 0.60 and not stockouts and not surpluses:
            recs.append({
                "action": "Situation stable — Maintenez votre rythme actuel",
                "detail": "Aucune alerte detectee. Continuez sur cette lancee.",
                "priority": "OK"
            })

        if not recs:
            recs.append({
                "action": "Donnees insuffisantes pour une recommandation precise",
                "detail": "Ajoutez plus de donnees historiques (minimum 20 semaines recommandees).",
                "priority": "ATTENTION"
            })

        return recs[:4]

    def recommend(self, context: dict) -> dict:
        if self._is_ollama_available():
            try:
                recs = self._ollama_recommend(context)
                if recs:
                    return {"recommendations": recs, "ai_source": "ollama"}
            except Exception:
                pass
        recs = self._smart_fallback(context)
        return {"recommendations": recs, "ai_source": "rules"}


def compute_trend(df) -> str:
    import numpy as np
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


def compute_cv(df) -> float:
    if df is None or len(df) < 2:
        return 0.0
    mean = df["y"].mean()
    if mean == 0:
        return 0.0
    return float(df["y"].std() / mean)
