# Politique de securite — StockPredi

## Gestion des secrets

- Aucune cle reelle ne doit etre committee dans ce repo (voir .env.example pour la liste des variables).
- Les cles Stripe exposees pendant le developpement doivent etre regenerees avant le lancement (dashboard Stripe > Developpeurs > Cles API), puis mises a jour sur Render.
- La cle SUPABASE_SERVICE_KEY ne doit exister que dans les variables d'environnement Render, jamais cote frontend.

## Mesures en place

- Authentification : JWT Supabase verifies sur chaque endpoint protege (middleware auth_required).
- CORS restreint au frontend (FRONTEND_URL) + localhost:3000 en dev.
- Rate limiting global : 200 requetes/heure et 50/minute par IP (flask-limiter).
- Webhook Stripe : verification de signature via STRIPE_WEBHOOK_SECRET.
- Dependances epinglees et corrigees des CVE connues (audit pip-audit, juillet 2026).
- Donnees hebergees en UE (Supabase Frankfurt) — conformite RGPD.

## Audits

- pip-audit a relancer avant chaque mise a jour de dependances.
- Frontend : les vulnerabilites npm audit restantes concernent uniquement la chaine de build react-scripts (dev), sans impact sur le bundle en production.

## Signalement

Vulnerabilite a signaler a : contact@stockpredi.fr
