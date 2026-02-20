"""
PDF Generator for Quotes — New flow
"""
import io
import os
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def generate_quote_pdf(quote, logo_path=None):
    """Generate a professional PDF for a quote.
    
    Args:
        quote: The quote object containing all quote data.
        logo_path: Optional path to a logo image file (PNG, JPG, etc.).
                   Can also be set on the user object as quote.user.logo.path
    """
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=6,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#334155')
    )
    
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#64748b')
    )
    
    content = []
    
    # --- Header with Logo ---
    # Try to resolve logo path: explicit param > user.logo field
    resolved_logo = logo_path
    if not resolved_logo:
        try:
            if hasattr(quote.user, 'logo') and quote.user.logo:
                resolved_logo = quote.user.logo.path
        except Exception:
            resolved_logo = None

    if resolved_logo and os.path.exists(resolved_logo):
        # Build a header table: Logo on the left, Title on the right
        logo = Image(resolved_logo)
        # Scale logo to fit nicely (max 3cm tall, preserve aspect ratio)
        max_logo_height = 4 * cm
        max_logo_width = 4 * cm
        iw, ih = logo.imageWidth, logo.imageHeight
        ratio = min(max_logo_width / iw, max_logo_height / ih)
        logo.drawWidth = iw * ratio
        logo.drawHeight = ih * ratio

        # title_block = Paragraph("DEVIS", title_style)
        subtitle_block = Paragraph(f"N° {quote.quote_number}", subtitle_style)

        # Nest title + subtitle in a small table so they stack vertically
        title_cell = Table(
            [[subtitle_block]],
            colWidths=[11 * cm]
        )
        title_cell.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        header_table = Table(
            [[logo, title_cell]],
            colWidths=[6 * cm, 11 * cm]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        content.append(header_table)
        content.append(Spacer(1, 6 * mm))
    else:
        # No logo — keep original plain header
        content.append(Paragraph("DEVIS", title_style))
        content.append(Paragraph(f"N° {quote.quote_number}", subtitle_style))
    
    # Company & Client info
    user = quote.user
    company_info = f"""
    <b>{user.company_name or user.username}</b><br/>
    {user.first_name} {user.last_name}<br/>
    {user.phone or ''}<br/>
    {user.city or ''}<br/>
    {user.email}
    """
    
    client_info = f"""
    <b>Client:</b><br/>
    {quote.client_name or 'Non spécifié'}<br/>
    {quote.client_phone or ''}<br/>
    {quote.client_address or ''}
    """
    
    info_table = Table([
        [ Paragraph(client_info, normal_style)]
    ], colWidths=[9*cm, 8*cm])
    
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    content.append(info_table)
    content.append(Spacer(1, 10*mm))
    
    # Quote details
    details_data = [
        ['Date:', quote.created_at.strftime('%d/%m/%Y'), 'Validité:', quote.valid_until.strftime('%d/%m/%Y') if quote.valid_until else '30 jours'],
        ['Type:', quote.get_summary_text(), 'Surface:', f'{quote.surface} m²'],
    ]
    
    details_table = Table(details_data, colWidths=[3*cm, 5.5*cm, 3*cm, 5.5*cm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#334155')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    
    content.append(details_table)
    content.append(Spacer(1, 8*mm))
    
    # System steps
    if quote.system_steps.exists():
        content.append(Paragraph("SYSTÈME DE TRAVAUX", heading_style))
        
        steps_data = [['N°', 'Opération', 'Prix/m²', 'Total']]
        for step in quote.system_steps.all():
            steps_data.append([
                str(step.order),
                step.name,
                f'{step.unit_price:.2f} DH',
                f'{step.total_price:.2f} DH'
            ])
        
        steps_table = Table(steps_data, colWidths=[1.5*cm, 9*cm, 3*cm, 3.5*cm])
        steps_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ]))
        
        content.append(steps_table)
        content.append(Spacer(1, 8*mm))
    
    # Materials
    content.append(Paragraph("FOURNITURES", heading_style))
    
    materials_data = [['Article', 'Qté', 'Unité', 'P.U. (DH)', 'Total (DH)']]
    for mat in quote.materials.all():
        line_total = mat.quantity * mat.unit_price
        materials_data.append([
            mat.name,
            str(mat.quantity),
            mat.unit,
            f'{mat.unit_price:.2f}',
            f'{line_total:.2f}'
        ])
    
    materials_table = Table(materials_data, colWidths=[8*cm, 1.5*cm, 2*cm, 2.5*cm, 3*cm])
    materials_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
    ]))
    
    content.append(materials_table)
    content.append(Spacer(1, 8*mm))
    
    # Cost breakdown
    content.append(Paragraph("RÉCAPITULATIF FINANCIER", heading_style))
    
    cost_data = [
        ["Main d'œuvre", f'{quote.labor_cost:.2f} DH'],
        ['Fournitures', f'{quote.material_cost:.2f} DH'],
        ['', ''],
        ['SOUS-TOTAL HT', f'{quote.subtotal:.2f} DH'],
        ['TVA (20%)', f'{quote.tax:.2f} DH'],
    ]
    
    cost_table = Table(cost_data, colWidths=[13*cm, 4*cm])
    cost_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#334155')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEBELOW', (0, -3), (-1, -3), 1, colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    content.append(cost_table)
    content.append(Spacer(1, 3*mm))
    
    # Total
    total_data = [['TOTAL TTC', f'{quote.total:.2f} DH']]
    total_table = Table(total_data, colWidths=[13*cm, 4*cm])
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    
    content.append(total_table)
    content.append(Spacer(1, 10*mm))
    
    # Signature section
    sig_data = [
        ['Signature du prestataire:', 'Bon pour accord - Signature client:'],
    ]
    
    doc.build(content)
    buffer.seek(0)
    return buffer