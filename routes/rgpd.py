"""
RGPD Compliance Routes
Handles automated data exports, email delivery, and audit logging
Format: SP-Data-Export-YYYY-MM-DD-HHmmss-{USER_ID}.pdf
"""

from flask import Blueprint, request, jsonify, current_app, Response
from middleware.auth_middleware import auth_required
from supabase import create_client
from config import Config
from datetime import datetime
import json
import requests
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import base64
from urllib.parse import urlencode

rgpd_bp = Blueprint("rgpd", __name__)

def get_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

def _generate_export_pdf(user_data, predictions_data, export_timestamp):
    """
    Generate RGPD compliant data export PDF
    Format: Professional report with user info, predictions history, and export metadata
    """
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#000000'),
            spaceAfter=12,
            alignment=1  # CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=8,
            spaceBefore=8
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#000000'),
            spaceAfter=6
        )

        elements = []

        # HEADER
        elements.append(Paragraph("DONNÉES PERSONNELLES - EXPORT RGPD", title_style))
        elements.append(Spacer(1, 0.2*inch))

        # EXPORT METADATA
        elements.append(Paragraph("Métadonnées de l'Export", heading_style))
        metadata_data = [
            ["Identifiant Export", f"SP-DATA-EXPORT-{export_timestamp}"],
            ["Date/Heure Export", datetime.now().strftime("%d/%m/%Y %H:%M:%S UTC")],
            ["Format", "PDF - Conforme RGPD Article 20"],
            ["Validité", "À conserver 6 mois minimum"],
        ]
        metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        elements.append(metadata_table)
        elements.append(Spacer(1, 0.2*inch))

        # USER PROFILE
        elements.append(Paragraph("Profil Utilisateur", heading_style))
        user_data_list = [
            ["ID Utilisateur", user_data.get("id", "—")],
            ["Email", user_data.get("email", "—")],
            ["Société", user_data.get("company_name", "—")],
            ["Plan", user_data.get("plan", "—")],
            ["Date Inscription", user_data.get("created_at", "—")],
            ["Préférences", json.dumps(user_data.get("preferences", {}), ensure_ascii=False)],
        ]
        user_table = Table(user_data_list, colWidths=[2*inch, 4*inch])
        user_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        elements.append(user_table)
        elements.append(Spacer(1, 0.2*inch))

        # PREDICTIONS HISTORY
        elements.append(Paragraph(f"Historique des Prévisions ({len(predictions_data)} enregistrements)", heading_style))
        if predictions_data:
            pred_headers = ["Date", "Produit", "Horizon", "Tendance", "Précision"]
            pred_rows = [pred_headers]
            for pred in predictions_data[:20]:  # Limit to 20 most recent
                row = [
                    pred.get("created_at", "—")[:10],  # Date only
                    pred.get("filename", "—")[:30],    # Truncate
                    str(pred.get("forecast_data", {}).get("periods", "—")),
                    pred.get("forecast_data", {}).get("trend", "—"),
                    f"{pred.get('forecast_data', {}).get('forecast', {}).get('accuracy_score', 0) * 100:.0f}%"
                ]
                pred_rows.append(row)

            pred_table = Table(pred_rows, colWidths=[1.2*inch, 1.8*inch, 1*inch, 1*inch, 1*inch])
            pred_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ]))
            elements.append(pred_table)
        else:
            elements.append(Paragraph("Aucune prévision enregistrée.", body_style))

        elements.append(Spacer(1, 0.3*inch))

        # FOOTER
        footer_text = "Cet export contient toutes les données personnelles traitées par StockPredi. Conformément au RGPD, vous avez le droit d'accès, de rectification, d'effacement et de portabilité de vos données."
        elements.append(Paragraph(footer_text, ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            alignment=0  # LEFT
        )))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"PDF Generation Error: {str(e)}")
        raise

def _send_email_via_resend(recipient_email, pdf_bytes, export_id):
    """
    Send RGPD export PDF via Resend email service
    Includes audit logging
    """
    try:
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')

        email_body = f"""Bonjour,

Voici votre export de données RGPD pour StockPredi.

ID Export: {export_id}
Date: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

Cet export contient:
- Votre profil utilisateur
- Votre historique de prévisions
- Métadonnées de traitement

Vous pouvez télécharger le fichier PDF en pièce jointe.

---
Conformément au RGPD Article 15, vous avez le droit d'accès à vos données personnelles.
StockPredi | support@stockpredi.fr
"""

        # Resend API call
        resend_url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {Config.RESEND_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "from": "noreply@stockpredi.fr",
            "to": recipient_email,
            "subject": f"Votre export RGPD StockPredi - {export_id}",
            "html": email_body.replace("\n", "<br>"),
            "attachments": [
                {
                    "filename": f"SP-DATA-EXPORT-{export_id}.pdf",
                    "content": pdf_b64,
                    "content_type": "application/pdf"
                }
            ]
        }

        response = requests.post(resend_url, json=payload, headers=headers, timeout=10)

        if response.status_code not in [200, 201]:
            print(f"Resend API Error: {response.status_code} - {response.text}")
            raise Exception(f"Email delivery failed: {response.status_code}")

        return response.json()
    except Exception as e:
        print(f"Email Send Error: {str(e)}")
        raise

def _log_rgpd_audit(user_id, action, details, status="success"):
    """
    Log RGPD actions for audit trail
    Creates immutable record of all data access/export events
    """
    try:
        supabase = get_client()

        # Create audit record in database
        audit_record = {
            "user_id": user_id,
            "action": action,
            "details": details,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "—")
        }

        # Try to insert into rgpd_audit table
        # If table doesn't exist, log to application logs instead
        try:
            supabase.table("rgpd_audit").insert(audit_record).execute()
        except Exception as db_error:
            print(f"Audit Log DB Error (expected on first run): {str(db_error)}")
            print(f"Audit Entry (fallback): {json.dumps(audit_record)}")

        return audit_record
    except Exception as e:
        print(f"Audit Logging Error: {str(e)}")
        return None

@rgpd_bp.route("/export", methods=["POST", "OPTIONS"])
@auth_required
def export_user_data():
    """
    POST /api/rgpd/export — Generate RGPD data export
    Requires authentication. Returns the PDF (application/pdf) for direct
    download, emails a copy if Resend is configured, logs audit trail.
    """
    try:
        user_id = request.user_id
        user_email = request.user_email

        supabase = get_client()

        # 1. Fetch user profile
        # limit(1) plutot que single() : single() leve une erreur si la ligne users n'existe pas
        user_res = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
        user_data = (user_res.data or [{}])[0]

        # 2. Fetch predictions history
        pred_res = supabase.table("predictions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        predictions_data = pred_res.data or []

        # 3. Generate export ID
        export_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        export_id = f"{export_timestamp}-{user_id[:8]}"

        # 4. Generate PDF
        pdf_bytes = _generate_export_pdf(user_data, predictions_data, export_id)

        # 5. Send email (if configured)
        email_result = None
        if Config.RESEND_API_KEY:
            try:
                email_result = _send_email_via_resend(user_email, pdf_bytes, export_id)
            except Exception as e:
                print(f"Email delivery skipped: {str(e)}")
                # Continue even if email fails

        # 6. Log audit trail
        _log_rgpd_audit(
            user_id,
            "DATA_EXPORT",
            {
                "export_id": export_id,
                "email_sent": email_result is not None,
                "predictions_count": len(predictions_data),
                "pdf_size_bytes": len(pdf_bytes)
            }
        )

        # Le frontend fait res.blob() : renvoyer le PDF lui-meme, pas du JSON
        filename = f"StockPredi_Export_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        return Response(
            pdf_bytes,
            status=200,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Export-Id": export_id,
                "X-Email-Sent": "true" if email_result is not None else "false",
            },
        )

    except Exception as e:
        _log_rgpd_audit(
            request.user_id if hasattr(request, 'user_id') else "unknown",
            "DATA_EXPORT",
            {"error": str(e)},
            status="error"
        )
        print(f"routes/rgpd.py: Export impossible: {type(e).__name__}: {e}")
        return jsonify({"error": "Export impossible"}), 500

@rgpd_bp.route("/status", methods=["GET", "OPTIONS"])
@auth_required
def get_rgpd_status():
    """
    GET /api/rgpd/status — Check RGPD compliance status
    Returns: data retention info, export history, deletion options
    """
    try:
        user_id = request.user_id
        supabase = get_client()

        # Fetch user data
        user_res = supabase.table("users").select("id,email,created_at").eq("id", user_id).single().execute()
        user_data = user_res.data or {}

        # Fetch export audit logs
        try:
            audit_res = supabase.table("rgpd_audit").select("*").eq("user_id", user_id).eq("action", "DATA_EXPORT").order("timestamp", desc=True).limit(10).execute()
            audit_logs = audit_res.data or []
        except:
            audit_logs = []

        return jsonify({
            "user_id": user_id,
            "email": user_data.get("email", "—"),
            "member_since": user_data.get("created_at", "—"),
            "data_retention_policy": "Conservées pendant toute la durée du contrat + 3 ans légalement requis",
            "last_export": audit_logs[0]["timestamp"] if audit_logs else None,
            "exports_count": len(audit_logs),
            "actions": {
                "export_data": "/api/rgpd/export",
                "delete_account": "/api/rgpd/delete"
            }
        }), 200

    except Exception as e:
        print(f"routes/rgpd.py: Statut RGPD indisponible: {type(e).__name__}: {e}")
        return jsonify({"error": "Statut RGPD indisponible"}), 500

@rgpd_bp.route("/delete", methods=["DELETE", "OPTIONS"])
@auth_required
def delete_user_data():
    """
    DELETE /api/rgpd/delete — Delete all user data and account
    Requires authentication. Irreversible. Sends confirmation email.
    """
    try:
        user_id = request.user_id
        user_email = request.user_email

        supabase = get_client()

        # 1. Log the deletion request
        _log_rgpd_audit(
            user_id,
            "DATA_DELETE_REQUESTED",
            {"deletion_requested_at": datetime.utcnow().isoformat()},
            status="pending"
        )

        # 2. Delete all predictions
        pred_delete = supabase.table("predictions").delete().eq("user_id", user_id).execute()
        deleted_count = len(pred_delete.data) if pred_delete.data else 0

        # 3. Delete user profile, puis le compte Supabase Auth (pas de cascade
        # public.users -> auth.users : sans ca l'email pouvait encore se connecter)
        supabase.table("users").delete().eq("id", user_id).execute()
        supabase.auth.admin.delete_user(user_id)

        # 4. Send confirmation email
        if Config.RESEND_API_KEY:
            try:
                resend_url = "https://api.resend.com/emails"
                headers = {
                    "Authorization": f"Bearer {Config.RESEND_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "from": "noreply@stockpredi.fr",
                    "to": user_email,
                    "subject": "Suppression de compte StockPredi confirmée",
                    "html": f"""Bonjour,<br><br>Votre compte StockPredi et toutes vos données ont été supprimées conformément à votre demande (RGPD Article 17).<br><br>
                    - {deleted_count} prévisions supprimées<br>
                    - Profil utilisateur supprimé<br>
                    - Email: {user_email}<br><br>
                    Cette suppression est irréversible.<br><br>
                    ---<br>
                    StockPredi | support@stockpredi.fr"""
                }
                requests.post(resend_url, json=payload, headers=headers, timeout=10)
            except:
                pass  # Email failure is non-critical

        # 5. Log successful deletion
        _log_rgpd_audit(
            user_id,
            "DATA_DELETE",
            {"deleted_predictions": deleted_count, "account_deleted": True},
            status="success"
        )

        return jsonify({
            "message": "Compte supprimé avec succès",
            "deleted_predictions": deleted_count,
            "confirmation_sent_to": user_email
        }), 200

    except Exception as e:
        _log_rgpd_audit(
            request.user_id if hasattr(request, 'user_id') else "unknown",
            "DATA_DELETE",
            {"error": str(e)},
            status="error"
        )
        print(f"routes/rgpd.py: Suppression impossible: {type(e).__name__}: {e}")
        return jsonify({"error": "Suppression impossible"}), 500

@rgpd_bp.route("/contact", methods=["POST", "OPTIONS"])
def contact_dpo():
    """
    POST /api/rgpd/contact — Contact DPO for RGPD requests
    Can be called authenticated or unauthenticated.
    Body: {email, subject, message, type} where type = rectification|opposition|question|suppression
    """
    try:
        body = request.get_json(silent=True) or {}
        email = body.get("email", "").strip().lower()
        subject = body.get("subject", "Demande RGPD")
        message = body.get("message", "")
        request_type = body.get("type", "question")  # rectification, opposition, question, suppression

        if not email or not message:
            return jsonify({"error": "Email et message requis"}), 400

        user_id = None
        try:
            user_id = request.user_id
        except:
            pass  # Unauthenticated requests allowed

        # Send to DPO
        if Config.RESEND_API_KEY and Config.OWNER_EMAIL:
            resend_url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {Config.RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": "noreply@stockpredi.fr",
                "to": Config.OWNER_EMAIL,
                "subject": f"[RGPD-{request_type.upper()}] {subject}",
                "html": f"""<strong>Demande RGPD - {request_type.upper()}</strong><br><br>
                Email demandeur: {email}<br>
                User ID: {user_id or 'Unauthenticated'}<br>
                Type: {request_type}<br>
                Sujet: {subject}<br><br>
                <strong>Message:</strong><br>
                {message.replace(chr(10), '<br>')}"""
            }
            requests.post(resend_url, json=payload, headers=headers, timeout=10)

        # Send confirmation to user
        if Config.RESEND_API_KEY:
            resend_url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {Config.RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": "noreply@stockpredi.fr",
                "to": email,
                "subject": f"Accusé de réception - Demande RGPD {request_type.upper()}",
                "html": f"""Bonjour,<br><br>
                Nous avons bien reçu votre demande RGPD ({request_type}).<br>
                Notre DPO examinera votre demande dans un délai de 30 jours conformément au RGPD Article 12.<br><br>
                Référence: {datetime.utcnow().isoformat()}<br><br>
                ---<br>
                StockPredi | contact@stockpredi.fr"""
            }
            requests.post(resend_url, json=payload, headers=headers, timeout=10)

        # Log the request
        if user_id:
            _log_rgpd_audit(
                user_id,
                "CONTACT_REQUEST",
                {"type": request_type, "subject": subject},
                status="success"
            )

        return jsonify({
            "message": "Demande reçue",
            "type": request_type,
            "email": email,
            "sla": "Réponse dans 30 jours (RGPD Article 12)"
        }), 200

    except Exception as e:
        print(f"routes/rgpd.py: Envoi impossible: {type(e).__name__}: {e}")
        return jsonify({"error": "Envoi impossible"}), 500
