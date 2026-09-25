"""
Routes admin — reservees au proprietaire du compte StockPredi.
GET /api/admin/export-clients : CSV des paiements clients (URSSAF / impots).
"""
import csv
import io
from datetime import datetime

from flask import Blueprint, request, jsonify, Response
from supabase import create_client

from config import Config
from middleware.auth_middleware import auth_required

admin_bp = Blueprint("admin", __name__)

ADMIN_EMAIL = "assouly.oscar@gmail.com"

STATUTS = {"active": "actif", "cancelling": "annulation en cours", "cancelled": "annulé", "canceled": "annulé"}

CSV_COLUMNS = [
    "date_paiement", "email_client", "montant_ht", "montant_ttc",
    "mode_paiement", "numero_facture", "stripe_invoice_id", "statut",
]


def get_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


def _eur(value):
    # Format francais pour Excel : 35,00
    return f"{float(value or 0):.2f}".replace(".", ",")


@admin_bp.route("/export-clients", methods=["GET"])
@auth_required
def export_clients():
    """CSV (separateur ;) d'une ligne par paiement encaisse.

    Source : table invoices (alimentee par le webhook invoice.paid), statut
    depuis users.plan. Franchise en base de TVA : HT = TTC.
    Filtre optionnel : ?annee=2026
    """
    if (getattr(request, "user_email", "") or "").lower() != ADMIN_EMAIL:
        return jsonify({"error": "Acces reserve a l'administrateur"}), 403

    annee = request.args.get("annee", "").strip()
    if annee and not (annee.isdigit() and len(annee) == 4):
        return jsonify({"error": "Parametre annee invalide (ex: 2026)"}), 400

    try:
        supabase = get_client()
        q = supabase.table("invoices").select(
            "invoice_number, user_id, client_email, amount_ht, amount_ttc, stripe_invoice_id, paid_at"
        )
        if annee:
            q = q.gte("paid_at", f"{annee}-01-01").lt("paid_at", f"{int(annee) + 1}-01-01")
        invoices = q.order("paid_at").execute().data or []

        user_ids = sorted({r["user_id"] for r in invoices if r.get("user_id")})
        plans = {}
        if user_ids:
            users = supabase.table("users").select("id, plan").in_("id", user_ids).execute().data or []
            plans = {u["id"]: u.get("plan") for u in users}
    except Exception as e:
        return jsonify({"error": "Export clients impossible", "detail": str(e)}), 500

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for r in invoices:
        plan = plans.get(r.get("user_id"))
        writer.writerow([
            (r.get("paid_at") or "")[:10],
            r.get("client_email") or "",
            _eur(r.get("amount_ht") if r.get("amount_ht") is not None else r.get("amount_ttc")),
            _eur(r.get("amount_ttc")),
            "carte bancaire (Stripe)",
            r.get("invoice_number") or "",
            r.get("stripe_invoice_id") or "",
            STATUTS.get(plan, plan or "inconnu"),
        ])

    filename = f"StockPredi_clients_{annee or datetime.now().strftime('%Y-%m-%d')}.csv"
    # BOM UTF-8 : accents corrects a l'ouverture dans Excel
    return Response(
        "﻿" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
