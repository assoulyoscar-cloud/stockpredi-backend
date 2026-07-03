# StockPredi — Guide de déploiement backend (Render)

## Ce qui est prêt

### Backend Flask (`stockpredi-backend/`)
- `app.py` — Flask app principale (CORS, blueprints, error handlers)
- `config.py` — Variables d'environnement
- `middleware/auth_middleware.py` — Décorateur `@auth_required` (JWT Supabase)
- `routes/auth.py` — POST /api/auth/signup|login|logout|refresh
- `routes/predictions.py` — POST /api/predictions/forecast|recommendations
- `routes/user.py` — GET|PATCH /api/user/profile, GET /api/user/predictions
- `routes/stripe_routes.py` — POST /api/stripe/create-subscription|cancel|webhook
- `models/forecast.py` — ProphetForecaster (fallback LinearRegression)
- `models/recommendations.py` — OllamaRecommender (fallback règles métier)
- `requirements.txt`, `Procfile`, `render.yaml`

### Frontend React (`stockpredi/src/`)
- `pages/Login.jsx` → /login
- `pages/Signup.jsx` → /signup
- `pages/Dashboard.jsx` → /dashboard
- `components/ProtectedRoute.jsx` — Redirect /login si non authentifié
- `api/backendClient.js` — Toutes les fonctions d'appel API
- `App.jsx` — Routes /login, /signup, /dashboard ajoutées

---

## Étapes manuelles (Oscar)

### 1. Supabase SERVICE_KEY
Supabase Dashboard → Settings → API → `service_role` (secret)
→ Ajouter dans `stockpredi-backend/.env` : `SUPABASE_SERVICE_KEY=sb_secret_XXXX`

### 2. Clés Stripe
Stripe Dashboard → Developers → API keys (mode Test)
→ `STRIPE_SECRET_KEY=sk_test_XXXX`
→ `STRIPE_PUBLISHABLE_KEY=pk_test_XXXX`
Stripe → Products → Créer produit "StockPredi" 35€/mois → copier Price ID
→ `STRIPE_PRICE_ID=price_XXXX`

### 3. Tables Supabase (SQL Editor)
```sql
create table if not exists public.users (
  id uuid references auth.users(id) primary key,
  email text not null,
  stripe_customer_id text,
  stripe_subscription_id text,
  plan text default 'trial',
  company_name text,
  preferences jsonb default '{}',
  created_at timestamptz default now()
);

alter table public.users enable row level security;
create policy "users_own_row" on public.users
  for all using (auth.uid() = id);

create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.users (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
```

### 4. Déployer sur Render
1. render.com → New → Web Service → connecter repo `stockpredi-backend`
2. Build: `pip install -r requirements.txt` / Start: `gunicorn app:app`
3. Env vars : copier tout le `.env` + `FLASK_ENV=production`
4. Déployer → noter URL `https://stockpredi-backend.onrender.com`

### 5. Stripe Webhook
Stripe → Developers → Webhooks → Add endpoint
- URL: `https://stockpredi-backend.onrender.com/api/stripe/webhook`
- Events: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted, invoice.payment_failed
- Copier Signing secret → `STRIPE_WEBHOOK_SECRET` dans Render

### 6. Connecter frontend
Vercel Dashboard → stockpredi → Environment Variables :
`REACT_APP_BACKEND_URL=https://stockpredi-backend.onrender.com`
→ Redéployer (git push)

### 7. Test
```bash
curl https://stockpredi-backend.onrender.com/health
# → {"status": "ok", "service": "stockpredi-backend"}
```

---

## Note Ollama
Ollama (Llama3.1) ne tourne pas sur Render free tier.
Le fallback règles métier s'active automatiquement — aucune action requise.
Pour activer Ollama en prod : VPS dédié ou Render paid tier.

---

Architecture: React (Vercel) → Flask/Gunicorn (Render) → Supabase + Stripe
