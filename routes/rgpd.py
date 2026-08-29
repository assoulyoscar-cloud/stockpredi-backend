"""
StockPredi — RGPD Compliance Routes
Endpoints : export PDF, suppression, statut, contact DPO
"""
import os, io, json, logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from functools import wraps
import jwt

# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Supabase + Resend
from supabase import create_client
import requests as http_requests

logger = logging.getLogger(__name__)
rgpd_bp = Blueprint("rgpd", __name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def get_supabase():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Token manquant"}), 401
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get("sub")
            user_email = payload.get("email", "")
            if not user_id:
                return jsonify({"error": "Token invalide"}), 401
        except Exception:
            return jsonify({"error": "Token invalide"}), 401
        return f(user_id, user_email, *args, **kwargs)
    return decorated

def send_email(to_email, subject, html_body, attachments=None):
    """Envoie un email via Resend API."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY non configuré — email non envoyé")
        return False
    payload = {
        "from": os.environ.get("RESEND_FROM", "StockPredi <onboarding@resend.dev>"),
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }
    if attachments:
        payload["attachments"] = attachments
    r = http_requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return r.status_code in (200, 201)

def log_audit(user_id, action, details=None, status="success"):
    """Crée un enregistrement dans rgpd_audit (best-effort)."""
    try:
        sb = get_supabase()
        sb.table("rgpd_audit").insert({
            "user_id": user_id,
            "action": action,
            "details": details or {},
            "status": status,
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "")[:255],
        }).execute()
    except Exception as e:
        logger.error(f"Audit log échoué: {e}")

def generate_rgpd_pdf(user_id, user_email, member_since, predictions):
    """Génère un PDF ReportLab avec toutes les données utilisateur."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style  = ParagraphStyle("Title2", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    h2_style     = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceAfter=4, textColor=colors.HexColor("#333"))
    body_style   = styles["Normal"]
    small_style  = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
    story = []

    # En-tête
    story.append(Paragraph("STOCKPREDI — EXPORT RGPD", title_style))
    story.append(Paragraph(f"Généré le {now_str}", small_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 0.4*cm))

    # Section 1 : Identité
    story.append(Paragraph("1. Données personnelles", h2_style))
    id_data = [
        ["Champ", "Valeur"],
        ["Email", user_email],
        ["Identifiant utilisateur", str(user_id)],
        ["Date d'inscription", member_since or "—"],
        ["Date d'export", now_str],
    ]
    t = Table(id_data, colWidths=[5*cm, 12*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Section 2 : Prévisions
    story.append(Paragraph("2. Historique des prévisions", h2_style))
    if predictions:
        pred_data = [["Date", "Produit", "Horizon", "Tendance", "Précision"]]
        for p in predictions:
            fd = p.get("forecast_data") or {}
            pred_data.append([
                datetime.fromisoformat(p["created_at"]).strftime("%d/%m/%Y") if p.get("created_at") else "—",
                str(fd.get("product_name") or p.get("filename") or "—")[:30],
                f"{fd.get('periods','—')} j",
                str(fd.get("trend") or "—"),
                f"{round((fd.get('forecast',{}).get('accuracy_score',0) or 0)*100)}%" if fd.get('forecast') else "—",
            ])
        t2 = Table(pred_data, colWidths=[2.5*cm, 6*cm, 2*cm, 3*cm, 2.5*cm])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.black),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(t2)
    else:
        story.append(Paragraph("Aucune prévision enregistrée.", body_style))
    story.append(Spacer(1, 0.5*cm))

    # Section 3 : Données collectées (cookies, tracking)
    story.append(Paragraph("3. Données collectées par StockPredi", h2_style))
    collected = [
        ["Type de donnée", "Finalité", "Durée de conservation"],
        ["Email", "Authentification, facturation", "Durée du compte + 3 ans"],
        ["Historique prévisions", "Service principal", "Durée du compte"],
        ["Données de paiement", "Facturation Stripe", "10 ans (obligation légale)"],
        ["Adresse IP", "Sécurité, audit RGPD", "12 mois"],
        ["Cookies de session", "Authentification Supabase", "Session navigateur"],
        ["Journaux d'accès", "Sécurité et audit", "12 mois"],
    ]
    t3 = Table(collected, colWidths=[4.5*cm, 6*cm, 5.5*cm])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("WORDWRAP",   (0,0), (-1,-1), True),
    ]))
    story.append(t3)
    story.append(Spacer(1, 0.5*cm))

    # Section 4 : Droits RGPD
    story.append(Paragraph("4. Vos droits RGPD", h2_style))
    droits = [
        "• <b>Droit d'accès (Art. 15)</b> : Obtenir une copie de vos données — via ce PDF.",
        "• <b>Droit à la portabilité (Art. 20)</b> : Recevoir vos données dans un format structuré — via ce PDF.",
        "• <b>Droit à l'effacement (Art. 17)</b> : Demander la suppression de votre compte et données.",
        "• <b>Droit de rectification (Art. 16)</b> : Corriger vos données inexactes.",
        "• <b>Droit d'opposition (Art. 21)</b> : Vous opposer au traitement.",
        "• <b>Contact DPO</b> : support@stockpredi.fr",
    ]
    for d in droits:
        story.append(Paragraph(d, body_style))
        story.append(Spacer(1, 0.15*cm))
    story.append(Spacer(1, 0.5*cm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.2*cm))
    seller = os.environ.get("SELLER_NAME", "StockPredi")
    siret  = os.environ.get("SELLER_SIRET", "—")
    story.append(Paragraph(
        f"{seller} — SIRET {siret} — APE 6201Z — stockpredi.fr | "
        f"Export RGPD conforme aux articles 15 & 20 du RGPD — {now_str}",
        small_style
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()

# ── Endpoints ─────────────────────────────────────────────────────────────────

@rgpd_bp.route("/export", methods=["POST"])
@require_auth
def rgpd_export(user_id, user_email):
    """POST /api/rgpd/export — Génère et envoie le PDF RGPD par email."""
    try:
        sb = get_supabase()
        # Profil
        profile = sb.table("users").select("*").eq("id", user_id).maybe_single().execute()
        member_since = None
        if profile.data:
            ms = profile.data.get("created_at") or ""
            if ms:
                try:
                    member_since = datetime.fromisoformat(ms).strftime("%d/%m/%Y")
                except Exception:
                    member_since = ms[:10]
        # Prévisions
        preds_res = sb.table("predictions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        predictions = preds_res.data or []
        # Générer PDF
        pdf_bytes = generate_rgpd_pdf(user_id, user_email, member_since, predictions)
        import base64
        pdf_b64 = base64.b64encode(pdf_bytes).decode()
        filename = f"StockPredi_RGPD_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        # Envoyer email
        html = f"""
        <p>Bonjour,</p>
        <p>Votre export RGPD StockPredi est disponible en pièce jointe.</p>
        <p>Ce document contient :</p>
        <ul>
          <li>Vos données personnelles</li>
          <li>Votre historique de prévisions ({len(predictions)} entrée(s))</li>
          <li>La liste des données collectées par StockPredi</li>
          <li>Un rappel de vos droits RGPD</li>
        </ul>
        <p>Conservez ce document pour vos archives.</p>
        <p>— L'équipe StockPredi</p>
        """
        email_sent = send_email(
            user_email,
            "Votre export RGPD — StockPredi",
            html,
            attachments=[{"filename": filename, "content": pdf_b64}]
        )
        log_audit(user_id, "DATA_EXPORT", {"predictions_count": len(predictions), "email_sent": email_sent})
        return jsonify({
            "success": True,
            "export_id": filename.replace(".pdf", ""),
            "email_sent": email_sent,
            "predictions_count": len(predictions),
            "pdf_size_bytes": len(pdf_bytes),
        })
    except Exception as e:
        logger.error(f"RGPD export error: {e}")
        log_audit(user_id, "DATA_EXPORT", {"error": str(e)}, status="error")
        return jsonify({"error": f"Erreur lors de l'export : {str(e)}"}), 500


@rgpd_bp.route("/status", methods=["GET"])
@require_auth
def rgpd_status(user_id, user_email):
    """GET /api/rgpd/status — Retourne l'historique exports et statut conformité."""
    try:
        sb = get_supabase()
        # Derniers exports
        try:
            audits = sb.table("rgpd_audit").select("timestamp,action,status").eq("user_id", user_id).eq("action", "DATA_EXPORT").order("timestamp", desc=True).limit(5).execute()
            exports = audits.data or []
        except Exception:
            exports = []
        # Nb prévisions
        preds = sb.table("predictions").select("id", count="exact").eq("user_id", user_id).execute()
        preds_count = preds.count or 0
        last_export = exports[0]["timestamp"] if exports else None
        return jsonify({
            "user_id": user_id,
            "email": user_email,
            "last_export": last_export,
            "exports_count": len(exports),
            "predictions_count": preds_count,
        })
    except Exception as e:
        logger.error(f"RGPD status error: {e}")
        return jsonify({"error": str(e)}), 500


@rgpd_bp.route("/delete", methods=["DELETE"])
@require_auth
def rgpd_delete(user_id, user_email):
    """DELETE /api/rgpd/delete — Supprime les prévisions de l'utilisateur."""
    try:
        sb = get_supabase()
        result = sb.table("predictions").delete().eq("user_id", user_id).execute()
        deleted = len(result.data) if result.data else 0
        # Email confirmation
        html = f"""
        <p>Bonjour,</p>
        <p>Vos données de prévisions ont été supprimées de StockPredi ({deleted} entrée(s)).</p>
        <p>Votre compte reste actif. Pour supprimer votre compte définitivement, contactez support@stockpredi.fr.</p>
        <p>— L'équipe StockPredi</p>
        """
        send_email(user_email, "Suppression de vos données — StockPredi", html)
        log_audit(user_id, "DATA_DELETE", {"deleted_predictions": deleted})
        return jsonify({"success": True, "deleted_predictions": deleted})
    except Exception as e:
        logger.error(f"RGPD delete error: {e}")
        return jsonify({"error": str(e)}), 500


@rgpd_bp.route("/contact", methods=["POST"])
def rgpd_contact():
    """POST /api/rgpd/contact — Formulaire contact DPO (auth optionnelle)."""
    try:
        body = request.get_json() or {}
        email   = body.get("email", "")
        subject = body.get("subject", "Demande RGPD")
        message = body.get("message", "")
        req_type = body.get("type", "question")
        if not email or not message:
            return jsonify({"error": "Email et message requis"}), 400
        owner_email = os.environ.get("OWNER_EMAIL", "")
        # Email au DPO
        if owner_email:
            html_owner = f"""
            <p><b>Nouvelle demande RGPD — {req_type}</b></p>
            <p><b>De :</b> {email}</p>
            <p><b>Sujet :</b> {subject}</p>
            <p><b>Message :</b></p>
            <p>{message}</p>
            """
            send_email(owner_email, f"[RGPD] {req_type} — {email}", html_owner)
        # Accusé réception
        html_user = f"""
        <p>Bonjour,</p>
        <p>Nous avons bien reçu votre demande RGPD de type <b>{req_type}</b>.</p>
        <p>Nous vous répondrons dans un délai maximum de 30 jours conformément au RGPD.</p>
        <p>— L'équipe StockPredi</p>
        """
        send_email(email, "Accusé de réception — Demande RGPD StockPredi", html_user)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"RGPD contact error: {e}")
        return jsonify({"error": str(e)}), 500
