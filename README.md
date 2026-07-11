# StockPredi Backend

API Flask de previsions de stock IA pour PME francaises.

## Stack

- Flask 3 + gunicorn (Render, auto-deploy depuis main)
- Supabase (auth JWT + base de donnees, region Frankfurt EU)
- scikit-learn (regression lineaire) pour les previsions
- Ollama / Llama 3.1 pour les recommandations, avec fallback regles metier automatique
- Stripe (abonnement 35 EUR/mois, webhook de synchronisation du plan)
- flask-limiter (rate limiting : 200 req/h, 50 req/min)

## Endpoints

- GET /health : statut du service
- POST /api/auth/signup, /api/auth/login, /api/auth/refresh
- POST /api/predictions/forecast : body { data: [{ds, y}...], periods } (min 7 points, JWT requis)
- POST /api/predictions/recommendations : previsions + recommandations (JWT requis)
- GET/PATCH /api/user/profile, GET /api/user/history
- POST /api/stripe/create-subscription, GET /api/stripe/status, POST /api/stripe/webhook

## Lancer en local

1. `pip install -r requirements.txt`
2. Copier .env.example en .env et remplir les valeurs
3. `python app.py` (ou `gunicorn app:app`)

## Deploiement

Voir DEPLOY.md. Variables d'environnement a configurer sur Render : voir .env.example.

## Securite

Voir SECURITY.md. Ne jamais committer de cles reelles.
