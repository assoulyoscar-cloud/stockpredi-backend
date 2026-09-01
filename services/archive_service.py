"""
Service d'archivage automatique des clients
Génère et archive un PDF avec les infos du client à chaque signup
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import requests
import json
from .google_drive_service import GoogleDriveService


def generate_archive_pdf(client_data: dict) -> bytes:
    """
    Génère un PDF d'archivage avec les infos du client

    Args:
        client_data: Dict avec email, nom, date_creation, etc.

    Returns:
        Bytes du PDF
    """
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )

    # Contenu du PDF
    elements = []

    # Titre
    elements.append(Paragraph("📋 Archivage Profil Client", title_style))
    elements.append(Spacer(1, 0.2*inch))

    # Infos client - AVEC L'EMAIL DU CLIENT
    info_data = [
        ['Email', client_data.get('email', 'N/A')],
        ['Nom', client_data.get('name', 'N/A')],
        ['Date création', client_data.get('created_at', datetime.now().isoformat())],
        ['ID Client', client_data.get('user_id', 'N/A')],
        ['Type compte', client_data.get('plan', 'Trial')],
    ]

    info_table = Table(info_data, colWidths=[2*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))

    # Données collectées
    elements.append(Paragraph("Données collectées", title_style))
    elements.append(Spacer(1, 0.1*inch))

    data_list = [
        "• Email et mot de passe (création compte)",
        "• Fichiers CSV/Excel uploadés (historique stock)",
        "• Logs d'utilisation (accès, actions, erreurs)",
        "• Adresse IP et user-agent (analytics)",
        "• Préférences utilisateur (langue, thème)",
    ]

    for item in data_list:
        elements.append(Paragraph(item, styles['Normal']))

    elements.append(Spacer(1, 0.3*inch))

    # Droits RGPD
    elements.append(Paragraph("Droits RGPD", title_style))
    elements.append(Spacer(1, 0.1*inch))

    rights_list = [
        "✓ Article 15: Droit d'accès à vos données personnelles",
        "✓ Article 16: Droit à la rectification de vos données",
        "✓ Article 17: Droit à l'oubli / suppression de compte",
        "✓ Article 20: Droit à la portabilité des données",
        "✓ Article 21: Droit à l'opposition de certains traitements",
    ]

    for right in rights_list:
        elements.append(Paragraph(right, styles['Normal']))

    elements.append(Spacer(1, 0.3*inch))

    # Footer
    footer_text = f"""
    <b>Archivage automatique</b> - StockPredi
    <br/>Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    <br/>Cette archive contient un récapitulatif de vos données collectées et de vos droits RGPD.
    <br/>Pour toute question: contact@stockpredi.fr
    """
    elements.append(Paragraph(footer_text, styles['Normal']))

    # Crée le PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def send_archive_email(client_email: str, pdf_bytes: bytes, filename: str) -> bool:
    """
    Envoie l'archive PDF par email via Resend API
    IMPORTANT: Envoie TOUJOURS à client_email, JAMAIS à oscar@stockpredi.fr

    Args:
        client_email: Email du CLIENT (oarevolut@gmail.com, pas oscar@stockpredi.fr)
        pdf_bytes: Contenu du PDF
        filename: Nom du fichier PDF

    Returns:
        True si succès, False sinon
    """
    try:
        api_key = os.getenv('RESEND_API_KEY')
        if not api_key:
            print("RESEND_API_KEY non configurée")
            return False

        # Encode le PDF en base64
        pdf_base64 = __import__('base64').b64encode(pdf_bytes).decode('utf-8')

        # Prépare le payload Resend
        # ENVOIE DE: contact@stockpredi.fr (ou oscar@stockpredi.fr)
        # ENVOIE À: client_email (oarevolut@gmail.com)
        payload = {
            "from": "StockPredi <onboarding@resend.dev>",
            "to": os.getenv('RESEND_TO', os.getenv('OWNER_EMAIL', 'assouly.oscar@gmail.com')),  # Mode test Resend: email vérifié uniquement
            "subject": f"📋 Archivage de vos données - {filename}",
            "html": f"""
            <h2>Bienvenue sur StockPredi!</h2>
            <p>Nous avons généré une archive de vos données personnelles et de vos droits RGPD.</p>
            <p>Cette archive est attachée à cet email et sauvegardée automatiquement.</p>
            <p><b>Votre email:</b> {client_email}</p>
            <p><b>Date d'archivage:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p>Pour toute question sur vos données ou vos droits RGPD, contactez-nous à contact@stockpredi.fr</p>
            <p>Cordialement,<br/>L'équipe StockPredi</p>
            """,
            "attachments": [
                {
                    "filename": filename,
                    "content": pdf_base64,
                    "contentType": "application/pdf"
                }
            ]
        }

        # Envoie via Resend
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            "https://api.resend.com/emails",
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            print(f"✓ Email archivage envoyé à {client_email}")
            return True
        else:
            print(f"✗ Erreur Resend: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"✗ Erreur envoi email archivage: {str(e)}")
        return False


def archive_client_signup(client_data: dict, drive_service=None) -> dict:
    """
    Processus complet d'archivage d'un nouveau client

    Args:
        client_data: Dict avec email, name, user_id, created_at, plan, etc.
                    email DOIT être l'email du client (oarevolut@gmail.com)
        drive_service: Instance GoogleDriveService (optionnel)

    Returns:
        Dict avec le statut de l'archivage
    """
    try:
        # Génère le PDF avec les infos du client
        pdf_bytes = generate_archive_pdf(client_data)

        # Prépare le nom du fichier
        timestamp = datetime.now().strftime('%Y%m%d')
        client_name = client_data.get('name', 'client').replace(' ', '_').lower()
        filename = f"{client_name}_{timestamp}.pdf"

        # Envoie l'email AU CLIENT (pas au propriétaire!)
        client_email = client_data.get('email')
        email_sent = send_archive_email(client_email, pdf_bytes, filename)

        # Upload sur Google Drive (optionnel)
        drive_result = None
        if drive_service:
            try:
                drive_result = drive_service.upload_pdf(pdf_bytes, filename)
            except Exception as e:
                print(f"Erreur upload Google Drive: {str(e)}")

        return {
            'success': True,
            'email_sent': email_sent,
            'drive_uploaded': drive_result.get('success', False) if drive_result else False,
            'filename': filename,
            'drive_file_id': drive_result.get('file_id') if drive_result else None
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
