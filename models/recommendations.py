import requests
import json
import numpy as np
from config import Config


SECTOR_CONFIG = {
    "restaurant": {
        "label": "Restaurant / Traiteur",
        "unit": "couverts",
        "perishable": True,
        "peak_days": "vendredi-samedi",
        "seasonality": "Pics le week-end et jours fériés. Baisse en janvier et août.",
        "stockout_advice": "Rupture = clients perdus définitivement. Commandez 10-15% de marge.",
        "surplus_advice": "Produits périssables = perte sèche. Réduisez les quantités ou congelez.",
        "stable_advice": "Maintenez vos commandes fournisseurs actuelles. Surveillez les réservations.",
        "hausse_advice": "Préparez vos fournisseurs à une hausse. Négociez des conditions de volume.",
        "baisse_advice": "Adaptez vos menus et portions. Réduisez le gaspillage.",
    },
    "epicerie": {
        "label": "Épicerie / Alimentation",
        "unit": "articles",
        "perishable": True,
        "peak_days": "samedi",
        "seasonality": "Pics avant fêtes (Noël, Pâques). Baisse en été (vacances).",
        "stockout_advice": "Rayons vides = image dégradée. Passez commande immédiatement.",
        "surplus_advice": "Vérifiez les DLC. Mettez en promotion avant péremption.",
        "stable_advice": "Optimisez vos rotations. Vérifiez les DLC des produits à faible rotation.",
        "hausse_advice": "Augmentez les commandes sur les références à forte rotation.",
        "baisse_advice": "Réduisez les références peu vendues. Concentrez-vous sur les best-sellers.",
    },
    "boulangerie": {
        "label": "Boulangerie / Pâtisserie",
        "unit": "pièces",
        "perishable": True,
        "peak_days": "dimanche matin",
        "seasonality": "Pics le dimanche et jours fériés. Galettes en janvier, bûches en décembre.",
        "stockout_advice": "Pain en rupture = perte de clientèle fidèle. Augmentez les fournées.",
        "surplus_advice": "Invendus du jour = perte. Ajustez les quantités au plus juste.",
        "stable_advice": "Production régulière adaptée. Surveillez la météo (impact sur la fréquentation).",
        "hausse_advice": "Prévoyez des fournées supplémentaires. Vérifiez vos stocks de matières premières.",
        "baisse_advice": "Réduisez les fournées. Proposez des offres fin de journée pour limiter les pertes.",
    },
    "pepiniere": {
        "label": "Pépinière / Jardinerie",
        "unit": "plants/articles",
        "perishable": False,
        "peak_days": "samedi-dimanche",
        "seasonality": "Très forte saisonnalité : pic mars-juin (plantations), creux nov-fév. Second pic sept-oct.",
        "stockout_advice": "La saison de plantation n'attend pas. Commandez 3-4 mois en avance auprès des producteurs.",
        "surplus_advice": "Les plants invendus perdent de la valeur mais survivent. Stockez ou soldez en fin de saison.",
        "stable_advice": "Préparez la saison suivante. Commandez les vivaces et arbustes maintenant.",
        "hausse_advice": "Saison forte en approche. Sécurisez vos approvisionnements chez les grossistes.",
        "baisse_advice": "Hors saison normal. Concentrez-vous sur le conseil, l'entretien et les accessoires.",
    },
    "boutique": {
        "label": "Boutique / Commerce de détail",
        "unit": "articles",
        "perishable": False,
        "peak_days": "samedi",
        "seasonality": "Pics : soldes (jan/juil), rentrée (sept), fêtes (déc). Creux : février, août.",
        "stockout_advice": "Article manquant = vente perdue. Réapprovisionnez les best-sellers en priorité.",
        "surplus_advice": "Stock dormant = trésorerie bloquée. Soldez ou faites des ventes privées.",
        "stable_advice": "Bon rythme. Optimisez l'assortiment et renouvelez les vitrines.",
        "hausse_advice": "Augmentez vos commandes sur les tendances fortes. Préparez votre vitrine.",
        "baisse_advice": "Période creuse. Déstockez, faites du click & collect ou des promotions ciblées.",
    },
    "bureau_etude": {
        "label": "Bureau d'études / Services",
        "unit": "fournitures/consommables",
        "perishable": False,
        "peak_days": "lundi-vendredi",
        "seasonality": "Activité liée aux cycles projets. Creux en août et fin décembre.",
        "stockout_advice": "Consommables manquants = projets ralentis. Passez commande groupée.",
        "surplus_advice": "Surstock de fournitures = capital immobilisé inutilement.",
        "stable_advice": "Consommation régulière. Mettez en place une commande automatique mensuelle.",
        "hausse_advice": "Nouveaux projets en vue. Anticipez les besoins en fournitures et licences.",
        "baisse_advice": "Période calme. Reportez les achats non urgents.",
    },
    "general": {
        "label": "Général",
        "unit": "unités",
        "perishable": False,
        "peak_days": "",
        "seasonality": "",
        "stockout_advice": "Passez commande dès maintenant.",
        "surplus_advice": "Réduisez vos commandes pour la période concernée.",
        "stable_advice": "Maintenez votre rythme actuel.",
        "hausse_advice": "Augmentez légèrement vos commandes.",
        "baisse_advice": "Limitez vos commandes pour éviter les invendus.",
    },
}


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
        sector = context.get("sector", "general")
        cfg = SECTOR_CONFIG.get(sector, SECTOR_CONFIG["general"])
        sector_label = cfg["label"]
        sector_season = cfg.get("seasonality", "")
        return f"""Tu es un expert en gestion de stock pour PME françaises, spécialisé {sector_label}.

Produit: {product}
Secteur: {sector_label}
Tendance: {trend}
Précision modèle: {accuracy:.0%}
Coefficient de variation (variabilité): {cv:.0%}
Alertes: {json.dumps(alerts, ensure_ascii=False)}
Saisonnalité du secteur: {sector_season}

Donne 3 recommandations concrètes et adaptées au secteur {sector_label}.
Utilise le vocabulaire métier approprié.
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
        sector = context.get("sector", "general")
        cfg = SECTOR_CONFIG.get(sector, SECTOR_CONFIG["general"])
        sp = context.get("sector_params", {})
        perissable = sp.get("perissable", 30)
        saisonnalite = sp.get("saisonnalite", 50)
        marge_securite = sp.get("marge_securite", 20)
        tolerance_rupture = sp.get("tolerance_rupture", 30)
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
            urgency = "CRITIQUE" if tolerance_rupture < 20 else "ATTENTION"
            margin_tip = f" Prévoyez +{marge_securite}% de marge de sécurité." if marge_securite > 15 else ""
            recs.append({"action": f"Risque de rupture détecté ({len(stockouts)} période(s))", "detail": f"Première rupture prévue le {stockouts[0].get('date','?')}. {cfg['stockout_advice']}{margin_tip}", "priority": urgency})
        if surpluses:
            severity = "CRITIQUE" if perissable > 70 else "ATTENTION"
            recs.append({"action": f"Surplus prévu ({len(surpluses)} période(s))", "detail": f"Période du {surpluses[0].get('date','?')}. {cfg['surplus_advice']}", "priority": severity})
        if trend == "hausse" and accuracy >= 0.60:
            recs.append({"action": "Tendance à la hausse — Anticipez", "detail": cfg["hausse_advice"], "priority": "OK"})
        elif trend == "baisse" and accuracy >= 0.60:
            recs.append({"action": "Tendance à la baisse — Ajustez", "detail": cfg["baisse_advice"], "priority": "ATTENTION"})
        elif accuracy >= 0.60 and not stockouts and not surpluses:
            recs.append({"action": "Situation stable", "detail": cfg["stable_advice"], "priority": "OK"})
        sector_season = cfg.get("seasonality", "")
        if sector_season and saisonnalite >= 40 and accuracy >= 0.50 and not any(r['priority'] == 'CRITIQUE' for r in recs):
            priority = "ATTENTION" if saisonnalite > 75 else "OK"
            recs.append({"action": f"Saisonnalité {cfg['label']}", "detail": sector_season, "priority": priority})
        elif seasonality and accuracy >= 0.55 and not any(r['priority'] == 'CRITIQUE' for r in recs):
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
