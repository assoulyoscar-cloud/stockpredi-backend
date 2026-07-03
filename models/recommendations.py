import requests
import json
from config import Config


FALLBACK_RULES = [
    {"condition": "stockout", "action": "Commander en urgence", "priority": "CRITIQUE"},
    {"condition": "surplus", "action": "Reduire les commandes prochaines", "priority": "ATTENTION"},
    {"condition": "normal", "action": "Maintenir le rythme actuel", "priority": "OK"},
]


class OllamaRecommender:
    """Recommandations IA via Ollama/Llama3.1 avec fallback regles metier."""

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
        accuracy = context.get("accuracy_score", 0)
        avg_forecast = context.get("avg_forecast", 0)
        trend = context.get("trend", "stable")

        alert_text = ""
        if alerts:
            alert_text = "\n".join(
                f"- {a['type'].upper()} le {a['date']}: {a['action']}"
                for a in alerts[:3]
            )
        else:
            alert_text = "Aucune alerte majeure detectee."

        return f"""Tu es un expert en gestion de stock. Analyse ces donnees et donne 3 recommandations concretes et courtes.

Produit: {product}
Tendance: {trend}
Prevision moyenne 30j: {avg_forecast:.0f} unites/jour
Precision modele: {accuracy*100:.0f}%
Alertes:
{alert_text}

Reponds en JSON avec ce format exact:
{{
  "recommendations": [
    {{"priority": "CRITIQUE|ATTENTION|OK", "action": "action concrete", "detail": "explication courte"}},
    {{"priority": "CRITIQUE|ATTENTION|OK", "action": "action concrete", "detail": "explication courte"}},
    {{"priority": "OK", "action": "action concrete", "detail": "explication courte"}}
  ],
  "summary": "une phrase resume"
}}"""

    def _call_ollama(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 512}
        }
        r = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout
        )
        r.raise_for_status()
        text = r.json().get("response", "")
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise ValueError("No JSON in Ollama response")

    def _fallback_recommendations(self, context: dict) -> dict:
        alerts = context.get("alerts", [])
        trend = context.get("trend", "stable")
        accuracy = context.get("accuracy_score", 0)

        recs = []
        # Priority based on alerts
        for alert in alerts[:2]:
            if alert["type"] == "stockout":
                recs.append({
                    "priority": "CRITIQUE",
                    "action": alert["action"],
                    "detail": f"Risque de rupture detecte le {alert['date']}"
                })
            elif alert["type"] == "surplus":
                recs.append({
                    "priority": "ATTENTION",
                    "action": alert["action"],
                    "detail": f"Surplus prevu le {alert['date']}"
                })

        # Trend recommendation
        if trend == "hausse":
            recs.append({
                "priority": "ATTENTION",
                "action": "Augmenter les commandes de 15-20%",
                "detail": "Tendance haussiere detectee sur 30 jours"
            })
        elif trend == "baisse":
            recs.append({
                "priority": "ATTENTION",
                "action": "Reduire les commandes de 10-15%",
                "detail": "Tendance baissiere detectee sur 30 jours"
            })
        else:
            recs.append({
                "priority": "OK",
                "action": "Maintenir le niveau de commandes actuel",
                "detail": "Stock stable, aucune action urgente"
            })

        # Accuracy warning
        if accuracy < 0.6:
            recs.append({
                "priority": "ATTENTION",
                "action": "Fournir plus de donnees historiques",
                "detail": f"Precision modele faible ({accuracy*100:.0f}%) — minimum 90 jours recommandes"
            })
        else:
            recs.append({
                "priority": "OK",
                "action": "Previsions fiables",
                "detail": f"Modele precis a {accuracy*100:.0f}%"
            })

        # Cap at 3
        recs = recs[:3]
        while len(recs) < 3:
            recs.append({
                "priority": "OK",
                "action": "Surveiller les indicateurs",
                "detail": "Aucune action requise pour le moment"
            })

        n_alerts = len(alerts)
        summary = (
            f"{n_alerts} alerte(s) detectee(s). Tendance {trend}. "
            f"Precision modele : {accuracy*100:.0f}%."
        )
        return {"recommendations": recs, "summary": summary, "source": "rules"}

    def get_recommendations(self, context: dict) -> dict:
        if self._is_ollama_available():
            try:
                prompt = self._build_prompt(context)
                result = self._call_ollama(prompt)
                result["source"] = "ollama"
                return result
            except Exception as e:
                pass  # Silent fallback
        return self._fallback_recommendations(context)


def compute_trend(predictions: list) -> str:
    """Detecte la tendance generale sur les previsions."""
    if len(predictions) < 7:
        return "stable"
    values = [p["forecast"] for p in predictions]
    first_week = sum(values[:7]) / 7
    last_week = sum(values[-7:]) / 7
    if first_week == 0:
        return "stable"
    delta = (last_week - first_week) / first_week
    if delta > 0.15:
        return "hausse"
    if delta < -0.15:
        return "baisse"
    return "stable"
