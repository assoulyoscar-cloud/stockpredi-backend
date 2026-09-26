"""Acces a la table public.users — creation automatique si absente."""
import math
from datetime import datetime, timedelta, timezone

TRIAL_DAYS = 14
TRIAL_WARNING_DAYS = 3


def ensure_user_row(supabase, user_id, email=None):
    """Garantit l'existence de la ligne public.users pour l'utilisateur.

    Les comptes crees via supabase.auth n'ont pas automatiquement de ligne
    dans public.users : on la cree au premier acces (plan = defaut DB).
    """
    try:
        res = supabase.table("users").select("id").eq("id", user_id).execute()
        if not res.data:
            row = {"id": user_id}
            if email:
                row["email"] = email
            supabase.table("users").insert(row).execute()
    except Exception:
        # Ne jamais bloquer la requete appelante pour un souci de provisioning
        pass
def _parse_ts(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    # users.created_at est un TIMESTAMP sans fuseau (NOW() cote Supabase = UTC)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def trial_status(row, now=None):
    """Plan effectif d'une ligne users -> (plan, jours_restants ou None).

    Essai gratuit de 14 jours compte depuis users.created_at, pour les comptes
    sans abonnement Stripe. Avec stripe_subscription_id, "trial" = periode
    d'essai Stripe d'un client qui a deja souscrit : jamais "expired" ici.
    """
    row = row or {}
    plan = row.get("plan") or "trial"
    if plan != "trial" or row.get("stripe_subscription_id"):
        return plan, None
    created = _parse_ts(row.get("created_at"))
    if not created:
        return plan, None
    remaining = created + timedelta(days=TRIAL_DAYS) - (now or datetime.now(timezone.utc))
    if remaining.total_seconds() <= 0:
        return "expired", 0
    return plan, math.ceil(remaining.total_seconds() / 86400)
