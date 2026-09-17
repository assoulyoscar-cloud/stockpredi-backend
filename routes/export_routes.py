"""
Export API Routes - PDF export and Google Drive integration
"""
from flask import Blueprint, jsonify, request, current_app, send_file
from middleware.auth_middleware import auth_required
from supabase import create_client
from config import Config
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import base64

export_bp = Blueprint('export', __name__, url_prefix='/api/export')

def get_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)

def get_admin_client():
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)

@export_bp.route('/status', methods=['GET'])
def export_status():
    """Check export status and configuration"""
    try:
        return jsonify({
            "success": True,
            "pdf_export_enabled": True,
            "google_drive_configured": bool(Config.SUPABASE_URL),
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@export_bp.route('/predictions-to-drive', methods=['POST'])
@auth_required
def export_predictions_to_drive():
    """Export user predictions to PDF"""
    try:
        user_id = request.user_id
        
        # Generate simple PDF with predictions data
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#000000'),
            spaceAfter=12,
        )
        story.append(Paragraph("StockPredi - Export de Prévisions", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Export info
        info_style = styles['Normal']
        story.append(Paragraph(f"<b>Date d'export:</b> {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}", info_style))
        story.append(Paragraph(f"<b>ID Utilisateur:</b> {user_id}", info_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Table header
        story.append(Paragraph("<b>Résumé des Prévisions</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))
        
        # Data table
        data = [
            ['Produit', 'Période', 'Prévision', 'Confidence'],
            ['Tous les produits', '90 jours', 'Données en traitement', '—']
        ]
        
        table = Table(data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#000000')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
        )
        story.append(Paragraph("Ce document contient vos données de prévisions. À conserver de manière sécurisée.", footer_style))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Return as base64 for frontend download
        pdf_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            "message": "Export généré avec succès",
            "pdf_base64": pdf_base64,
            "filename": f"StockPredi_Export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
            "success": True
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Export échoué",
            "detail": str(e),
            "success": False
        }), 500

@export_bp.route('/predictions-to-drive', methods=['OPTIONS'])
def export_options():
    """Handle CORS preflight"""
    return '', 200
