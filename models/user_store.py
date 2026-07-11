"""Acces a la table public.users — creation automatique si absente."""


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
