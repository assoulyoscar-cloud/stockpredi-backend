# routes/stripe_routes.py — VERSION FINALE avec facturation automatique
# Remplace intégralement le fichier existant.
# Nouveautés : handler invoice.paid → PDF reportlab + envoi Resend (client + récap fiscal Oscar)

import os
import base64
import logging
from datetime import datetime, timezone
from io import BytesIO
from zoneinfo import ZoneInfo
from calendar import monthrange

import requests as http
import stripe
from flask import Blueprint, request, jsonify
from middleware.auth_middleware import auth_required
from config import Config
from supabase import create_client

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

stripe.api_key = Config.STRIPE_SECRET_KEY
stripe_bp = Blueprint("stripe", __name__)
logger = logging.getLogger("stockpredi.billing")

# ---------------------------------------------------------------------------
# CONFIGURATION FACTURATION (variables d'environnement Render)
# ---------------------------------------------------------------------------
SELLER_NAME = os.getenv("SELLER_NAME", "StockPredi")
SELLER_OWNER = os.getenv("SELLER_OWNER", "Assouly Oscar")
SELLER_SIRET = os.getenv("SELLER_SIRET", "")          # vide = mode BROUILLON
SELLER_ADDRESS = os.getenv("SELLER_ADDRESS", "(à remplir)")
SELLER_APE = os.getenv("SELLER_APE", "6201Z")
SELLER_SITE = os.getenv("SELLER_SITE", "stockpredi.fr")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "assouly.oscar@gmail.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
# Tant que stockpredi.fr n'est pas vérifié dans Resend, garder l'expéditeur ci-dessous.
# Ensuite : RESEND_FROM="StockPredi <facturation@stockpredi.fr>"
RESEND_FROM = os.getenv("RESEND_FROM", "StockPredi <onboarding@resend.dev>")
# Taux cotisations micro-entreprise BNC libérale non réglementée — 25,6 % en 2026
# (le taux 24,6 % du brief était celui de 2025 ; ajustable sans redéploiement via env)
URSSAF_RATE = float(os.getenv("URSSAF_RATE", "0.256"))
TVA_THRESHOLD = float(os.getenv("TVA_THRESHOLD", "37500"))
TVA_ALERT_LEVEL = float(os.getenv("TVA_ALERT_LEVEL", "30000"))
# Logo : chargé une fois depuis le frontend (aucun fichier à ajouter au repo)
LOGO_URL = os.getenv("LOGO_URL", "https://stockpredi.vercel.app/logoSTOCKPREDI.png")
PARIS = ZoneInfo("Europe/Paris")

_LOGO_CACHE = {"tried": False, "img": None}


def _get_logo():
    """Télécharge le logo une seule fois (cache mémoire). Retourne ImageReader ou None."""
    if not _LOGO_CACHE["tried"]:
        _LOGO_CACHE["tried"] = True
        try:
            r = http.get(LOGO_URL, timeout=5)
            if r.status_code == 200:
                _LOGO_CACHE["img"] = ImageReader(BytesIO(r.content))
        except Exception:
            logger.warning("Logo indisponible (%s) — repli vectoriel", LOGO_URL)
    return _LOGO_CACHE["img"]


def _draw_folder_icon(c, x, y, size):
    """Repli vectoriel si le PNG est indisponible : dossier gris (esprit du logo)."""
    grey1, grey2 = HexColor("#9AA5AE"), HexColor("#C7CDD3")
    c.saveState()
    c.setFillColor(grey1)
    c.roundRect(x, y, size, size * 0.72, size * 0.06, fill=1, stroke=0)
    c.setFillColor(grey1)
    c.roundRect(x, y + size * 0.62, size * 0.42, size * 0.16, size * 0.05, fill=1, stroke=0)
    c.setFillColor(grey2)
    c.roundRect(x + size * 0.04, y, size * 0.96, size * 0.60, size * 0.06, fill=1, stroke=0)
    c.restoreState()

DRAFT_MODE = not SELLER_SIRET.strip()  # True tant que le SIRET n'est pas configuré


def get_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


def _eur(amount):
    """35.0 -> '35,00 €' (format français)."""
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",") + " €"


def _fdate(dt):
    return dt.astimezone(PARIS).strftime("%d/%m/%Y")


MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]


def _mois_annee(dt):
    d = dt.astimezone(PARIS)
    return f"{MOIS_FR[d.month - 1].capitalize()} {d.year}"


# ---------------------------------------------------------------------------
# ROUTES EXISTANTES (inchangées)
# ---------------------------------------------------------------------------
@stripe_bp.route("/create-subscription", methods=["POST"])
@auth_required
def create_subscription():
    """Cree un abonnement Stripe pour l'utilisateur connecte."""
    supabase = get_client()
    try:
        user_res = supabase.table("users").select("stripe_customer_id, email") \
            .eq("id", request.user_id).single().execute()
        user = user_res.data

        customer_id = user.get("stripe_customer_id")
        if not customer_id:
            customer = stripe.Customer.create(email=user["email"])
            customer_id = customer.id
            supabase.table("users").update({"stripe_customer_id": customer_id}) \
                .eq("id", request.user_id).execute()

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": Config.STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=f"{Config.FRONTEND_URL}/dashboard?payment=success",
            cancel_url=f"{Config.FRONTEND_URL}/dashboard?payment=cancelled",
            client_reference_id=request.user_id,
            subscription_data={"trial_period_days": 14}
        )
        return jsonify({"checkout_url": session.url, "session_id": session.id}), 200
    except stripe.StripeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Erreur creation abonnement", "detail": str(e)}), 500


@stripe_bp.route("/cancel-subscription", methods=["POST"])
@auth_required
def cancel_subscription():
    """Annule l'abonnement Stripe de l'utilisateur."""
    supabase = get_client()
    try:
        user_res = supabase.table("users").select("stripe_subscription_id") \
            .eq("id", request.user_id).single().execute()
        sub_id = user_res.data.get("stripe_subscription_id")
        if not sub_id:
            return jsonify({"error": "Aucun abonnement actif"}), 404

        stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        supabase.table("users").update({"plan": "cancelling"}) \
            .eq("id", request.user_id).execute()
        return jsonify({"message": "Abonnement annule en fin de periode"}), 200
    except stripe.StripeError as e:
        return jsonify({"error": str(e)}), 400


@stripe_bp.route("/status", methods=["GET"])
@auth_required
def subscription_status():
    """Retourne le statut abonnement de l'utilisateur."""
    supabase = get_client()
    try:
        res = supabase.table("users") \
            .select("plan, stripe_customer_id, stripe_subscription_id") \
            .eq("id", request.user_id).single().execute()
        return jsonify(res.data), 200
    except Exception as e:
        return jsonify({"error": "Statut introuvable", "detail": str(e)}), 404


# ---------------------------------------------------------------------------
# FACTURATION — génération PDF
# ---------------------------------------------------------------------------
def _build_invoice_pdf(num, emission_dt, client_email, period_start, period_end,
                       amount):
    """Génère la facture PDF en mémoire. Retourne des bytes."""
    buf = BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    ink = HexColor("#111111")
    grey = HexColor("#666666")

    # Filigrane BROUILLON tant que SIRET absent
    if DRAFT_MODE:
        c.saveState()
        c.setFont("Courier-Bold", 58)
        c.setFillColor(HexColor("#DDDDDD"))
        c.translate(w / 2, h / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, "BROUILLON")
        c.restoreState()

    # En-tête — logo (PNG du site, repli vectoriel sinon) + titres en Courier
    logo = _get_logo()
    if logo:
        c.drawImage(logo, 20 * mm, h - 34 * mm, width=16 * mm, height=16 * mm,
                    mask="auto", preserveAspectRatio=True)
    else:
        _draw_folder_icon(c, 20 * mm, h - 33 * mm, 14 * mm)

    c.setFillColor(ink)
    c.setFont("Courier-Bold", 20)
    c.drawString(40 * mm, h - 25 * mm, "STOCKPREDI")
    c.setFont("Courier", 8)
    c.setFillColor(grey)
    c.drawString(40 * mm, h - 31 * mm, "Prévisions de stock IA pour PME françaises")

    c.setFillColor(ink)
    c.setFont("Courier-Bold", 13)
    c.drawRightString(w - 20 * mm, h - 25 * mm, f"FACTURE {num}")
    c.setFont("Courier", 9)
    c.drawRightString(w - 20 * mm, h - 31 * mm, f"Date d'émission : {_fdate(emission_dt)}")

    # Prestataire
    y = h - 50 * mm
    c.setFont("Courier-Bold", 10)
    c.drawString(20 * mm, y, "Prestataire")
    c.setFont("Courier", 8.5)
    siret_txt = SELLER_SIRET if SELLER_SIRET else "(à remplir — en cours d'attribution)"
    for line in [f"{SELLER_NAME} — {SELLER_OWNER}", "Micro-entreprise",
                 f"SIRET : {siret_txt}", f"Adresse : {SELLER_ADDRESS}",
                 f"Code APE : {SELLER_APE}", f"Site : {SELLER_SITE}"]:
        y -= 4.5 * mm
        c.drawString(20 * mm, y, line)

    # Client
    y2 = h - 50 * mm
    c.setFont("Courier-Bold", 10)
    c.drawString(115 * mm, y2, "Client")
    c.setFont("Courier", 8.5)
    c.drawString(115 * mm, y2 - 4.5 * mm, client_email)

    # Tableau prestation
    y = y - 15 * mm
    c.setFillColor(HexColor("#F2F2F2"))
    c.rect(20 * mm, y - 2 * mm, w - 40 * mm, 8 * mm, fill=1, stroke=0)
    c.setFillColor(ink)
    c.setFont("Courier-Bold", 9)
    c.drawString(22 * mm, y, "Description")
    c.drawRightString(w - 22 * mm, y, "Montant")

    y -= 8 * mm
    c.setFont("Courier", 8.5)
    c.drawString(22 * mm, y, "Abonnement mensuel StockPredi — prévisions de stock IA")
    c.drawRightString(w - 22 * mm, y, _eur(amount))
    y -= 5 * mm
    c.setFillColor(grey)
    c.drawString(22 * mm, y,
                 f"Période couverte : {_fdate(period_start)} → {_fdate(period_end)}")
    c.setFillColor(ink)

    # Totaux
    y -= 12 * mm
    c.line(115 * mm, y + 3 * mm, w - 20 * mm, y + 3 * mm)
    c.setFont("Courier", 10)
    c.drawString(115 * mm, y - 2 * mm, "Montant HT")
    c.drawRightString(w - 20 * mm, y - 2 * mm, _eur(amount))
    y -= 7 * mm
    c.drawString(115 * mm, y - 2 * mm, "TVA")
    c.drawRightString(w - 20 * mm, y - 2 * mm, "Non applicable")
    y -= 7 * mm
    c.setFont("Courier-Bold", 11)
    c.drawString(115 * mm, y - 2 * mm, "Montant TTC")
    c.drawRightString(w - 20 * mm, y - 2 * mm, _eur(amount))

    # Mentions obligatoires
    y -= 16 * mm
    c.setFont("Courier-Bold", 9)
    c.drawString(20 * mm, y, "TVA non applicable — article 293 B du CGI")
    y -= 6 * mm
    c.setFont("Courier", 8.5)
    c.drawString(20 * mm, y, "Moyen de paiement : Prélèvement automatique (Stripe)")

    # Pied de page
    c.setFont("Courier-Oblique", 8)
    c.setFillColor(grey)
    c.drawCentredString(w / 2, 15 * mm,
                        "Paiement effectué via Stripe — Merci de votre confiance")
    c.showPage()
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# FACTURATION — envoi Resend
# ---------------------------------------------------------------------------
def _resend_send(to, subject, html, attachments=None):
    """Envoie un email via l'API Resend (module requests, déjà en dépendance)."""
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY absente — email non envoyé : %s", subject)
        return False
    payload = {"from": RESEND_FROM, "to": [to], "subject": subject, "html": html}
    if attachments:
        payload["attachments"] = attachments
    r = http.post("https://api.resend.com/emails",
                  headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
                  json=payload, timeout=20)
    if r.status_code >= 300:
        logger.error("Resend %s : %s", r.status_code, r.text[:300])
        return False
    return True


def _email_client_html(first_payment, num, period_start, period_end, amount):
    intro = (
        "<p>Bienvenue chez StockPredi ! Votre abonnement est maintenant actif. "
        "Vous avez accès aux prévisions IA illimitées, à l'import CSV/Excel "
        "et au support en moins de 4h.</p>"
        if first_payment else
        "<p>Votre abonnement StockPredi a bien été renouvelé. Merci de votre fidélité !</p>"
    )
    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:auto;color:#111">
  <h2 style="letter-spacing:1px">STOCKPREDI</h2>
  {intro}
  <table style="border-collapse:collapse;width:100%;margin:16px 0">
    <tr><td style="padding:6px 0;color:#666">Facture</td>
        <td style="text-align:right"><strong>{num}</strong></td></tr>
    <tr><td style="padding:6px 0;color:#666">Période</td>
        <td style="text-align:right">{period_start} → {period_end}</td></tr>
    <tr><td style="padding:6px 0;color:#666">Montant</td>
        <td style="text-align:right"><strong>{_eur(amount)}</strong>
        (TVA non applicable — art. 293 B du CGI)</td></tr>
  </table>
  <p>Votre facture est en pièce jointe.</p>
  <p style="color:#666;font-size:12px">Une question ? Répondez à cet email ou
  rendez-vous sur stockpredi.fr/contact.<br>
  Paiement effectué via Stripe — Merci de votre confiance.</p>
</div>"""


def _email_oscar_html(num, paid_dt, client_email, amount,
                      ca_mois, ca_annee, nb_mois, nb_annee):
    cotis_mois = ca_mois * URSSAF_RATE
    cotis_annee = ca_annee * URSSAF_RATE
    d = paid_dt.astimezone(PARIS)
    # Date limite déclaration mensuelle URSSAF : fin du mois suivant
    ny, nm = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    limite = datetime(ny, nm, monthrange(ny, nm)[1])
    alerte_tva = ""
    if ca_annee > TVA_ALERT_LEVEL:
        alerte_tva = (f"<p style='color:#B00020'><strong>⚠️ ALERTE TVA :</strong> "
                      f"CA cumulé {_eur(ca_annee)} — seuil franchise {_eur(TVA_THRESHOLD)}. "
                      f"Anticiper le passage à la TVA (facturation + Stripe Tax).</p>")
    return f"""
<div style="font-family:Arial,Helvetica,sans-serif;max-width:640px;margin:auto;color:#111">
  <h2>💰 Paiement reçu — récap fiscal</h2>
  <table border="1" cellpadding="8" style="border-collapse:collapse;width:100%;font-size:13px">
    <tr style="background:#f2f2f2">
      <th># Facture</th><th>Date</th><th>Client</th><th>Montant TTC</th>
      <th>Montant HT</th><th>TVA</th><th>Statut</th><th>À déclarer URSSAF</th>
    </tr>
    <tr>
      <td>{num}</td><td>{_fdate(paid_dt)}</td><td>{client_email}</td>
      <td>{_eur(amount)}</td><td>{_eur(amount)}</td><td>0 € (art. 293 B)</td>
      <td>paid</td><td><strong>{_eur(amount)}</strong></td>
    </tr>
  </table>
  <h3>Récap {_mois_annee(paid_dt)}</h3>
  <ul style="line-height:1.7">
    <li>CA du mois en cours : <strong>{_eur(ca_mois)}</strong> ({nb_mois} facture(s))</li>
    <li>CA cumulé depuis le 1er janvier : <strong>{_eur(ca_annee)}</strong> ({nb_annee} facture(s))</li>
    <li>Cotisations URSSAF estimées (taux {URSSAF_RATE * 100:.1f} % — BNC 2026) :
        mois {_eur(cotis_mois)} · cumul {_eur(cotis_annee)}</li>
    <li>📅 Date limite déclaration URSSAF (mensuelle) :
        <strong>{limite.strftime('%d/%m/%Y')}</strong></li>
    <li>Seuil franchise TVA : {_eur(TVA_THRESHOLD)} —
        marge restante : {_eur(max(0, TVA_THRESHOLD - ca_annee))}</li>
  </ul>
  {alerte_tva}
  <p style="color:#666;font-size:12px">Email automatique StockPredi —
  facture client en pièce jointe pour archivage.</p>
</div>"""


# ---------------------------------------------------------------------------
# FACTURATION — handler principal invoice.paid
# ---------------------------------------------------------------------------
def _handle_invoice_paid(supabase, invoice):
    amount_paid = invoice.get("amount_paid", 0)  # en centimes
    if amount_paid <= 0:
        # Facture 0 € émise à la création de l'abonnement (essai 14 jours) : ignorer.
        logger.info("invoice.paid 0 € ignorée (%s)", invoice.get("id"))
        return

    stripe_invoice_id = invoice["id"]
    customer_id = invoice.get("customer")
    client_email = invoice.get("customer_email") or ""

    # Idempotence : Stripe peut renvoyer le même événement plusieurs fois.
    existing = supabase.table("invoices").select("*") \
        .eq("stripe_invoice_id", stripe_invoice_id).execute()
    row = existing.data[0] if existing.data else None
    if row and row.get("sent_to_client"):
        logger.info("Facture déjà traitée : %s", stripe_invoice_id)
        return

    # Utilisateur lié
    user_id = None
    if customer_id:
        u = supabase.table("users").select("id, email") \
            .eq("stripe_customer_id", customer_id).execute()
        if u.data:
            user_id = u.data[0]["id"]
            client_email = client_email or u.data[0]["email"]

    # Période couverte
    now = datetime.now(timezone.utc)
    try:
        period = invoice["lines"]["data"][0]["period"]
        p_start = datetime.fromtimestamp(period["start"], tz=timezone.utc)
        p_end = datetime.fromtimestamp(period["end"], tz=timezone.utc)
    except Exception:
        p_start, p_end = now, now

    amount = amount_paid / 100.0

    # Numéro + insertion (ou reprise si un envoi précédent a échoué)
    if row:
        num = row["invoice_number"]
    else:
        num = supabase.rpc("next_invoice_number").execute().data
        supabase.table("invoices").insert({
            "invoice_number": num,
            "user_id": user_id,
            "client_email": client_email,
            "amount_ttc": amount,
            "amount_ht": amount,
            "stripe_invoice_id": stripe_invoice_id,
            "stripe_customer_id": customer_id,
            "period_start": p_start.date().isoformat(),
            "period_end": p_end.date().isoformat(),
            "paid_at": now.isoformat(),
        }).execute()

    # Génération PDF
    pdf_bytes = _build_invoice_pdf(num, now, client_email, p_start, p_end, amount)
    supabase.table("invoices").update({"pdf_generated": True}) \
        .eq("stripe_invoice_id", stripe_invoice_id).execute()
    attachment = [{
        "filename": f"Facture_{num}.pdf",
        "content": base64.b64encode(pdf_bytes).decode(),
    }]

    # 1er paiement de ce client ? (bienvenue vs renouvellement)
    hist = supabase.table("invoices").select("id", count="exact") \
        .eq("stripe_customer_id", customer_id).execute()
    first_payment = (hist.count or 1) <= 1

    # Email client — en mode BROUILLON, redirigé vers Oscar pour contrôle
    to_client = OWNER_EMAIL if DRAFT_MODE else client_email
    subject = f"Votre facture StockPredi — {_mois_annee(now)}"
    if DRAFT_MODE:
        subject = f"[BROUILLON — destinataire réel : {client_email}] {subject}"
    ok_client = _resend_send(
        to_client, subject,
        _email_client_html(first_payment, num, _fdate(p_start), _fdate(p_end), amount),
        attachments=attachment)
    if ok_client:
        supabase.table("invoices").update({"sent_to_client": True}) \
            .eq("stripe_invoice_id", stripe_invoice_id).execute()

    # Récap fiscal Oscar (CA recalculé depuis la table invoices)
    paris_now = now.astimezone(PARIS)
    month_start = paris_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = paris_now.replace(month=1, day=1, hour=0, minute=0,
                                   second=0, microsecond=0)
    inv_year = supabase.table("invoices").select("amount_ttc, paid_at") \
        .gte("paid_at", year_start.isoformat()).execute()
    ca_annee = sum(float(r["amount_ttc"]) for r in (inv_year.data or []))
    rows_mois = [r for r in (inv_year.data or [])
                 if r["paid_at"] and r["paid_at"] >= month_start.isoformat()]
    ca_mois = sum(float(r["amount_ttc"]) for r in rows_mois)
    _resend_send(
        OWNER_EMAIL,
        f"💰 StockPredi — paiement {num} ({_eur(amount)}) — récap fiscal",
        _email_oscar_html(num, now, client_email, amount, ca_mois, ca_annee,
                          len(rows_mois), len(inv_year.data or [])),
        attachments=attachment)


# ---------------------------------------------------------------------------
# WEBHOOK
# ---------------------------------------------------------------------------
@stripe_bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    """Webhook Stripe — mise a jour plan utilisateur + facturation."""
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, Config.STRIPE_WEBHOOK_SECRET
        )
    except stripe.errors.SignatureVerificationError:
        return jsonify({"error": "Signature invalide"}), 400

    supabase = get_client()
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = data.get("client_reference_id")
        sub_id = da