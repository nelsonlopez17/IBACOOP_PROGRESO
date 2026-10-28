"""
APPS/usuarios/utils.py

Generación de comprobantes y utilidades para la gestión de usuarios e identidades.
"""
import io
import secrets
import string
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def generar_clave_temporal(longitud=12) -> str:
    """Genera una clave temporal criptográficamente segura e impredecible."""
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    # garantizar inclusion de diferentes tipos de caracteres
    clave = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    clave += [secrets.choice(caracteres) for _ in range(longitud - 4)]
    secrets.SystemRandom().shuffle(clave)
    return "".join(clave)


def generar_pdf_credenciales_bytes(usuario, clave_temporal: str) -> bytes:
    """
    Genera un archivo PDF elegante con las credenciales de acceso del usuario
    listas para imprimir o descargar.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    header_title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E6532'),
        alignment=0
    )

    header_subtitle_style = ParagraphStyle(
        'HeaderSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=0
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )

    label_style = ParagraphStyle(
        'CustomLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1E293B')
    )

    cred_title_style = ParagraphStyle(
        'CredTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E6532'),
        alignment=1
    )

    cred_value_style = ParagraphStyle(
        'CredValue',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A'),
        alignment=1
    )

    elements = []

    elements.append(Paragraph("INSTITUTO BÁSICO POR COOPERATIVA EL PROGRESO", header_title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("HOJA OFICIAL DE CREDENCIALES Y CONSTANCIA DE ACCESO AL SISTEMA", header_subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1E6532'), spaceAfter=15))

    persona_nombre = "N/A"
    cui_val = "N/A"

    if hasattr(usuario, 'persona') and usuario.persona:
        persona_nombre = usuario.persona.nombre_completo
        cui_val = usuario.persona.cui or "N/A"
    else:
        persona_nombre = usuario.get_full_name() or usuario.username

    datos_tabla = [
        [Paragraph("Titular de la Cuenta:", label_style), Paragraph(persona_nombre, body_style)],
        [Paragraph("CUI / Identificación:", label_style), Paragraph(cui_val, body_style)],
        [Paragraph("Rol en la Institución:", label_style), Paragraph(usuario.get_rol_display() or "Usuario del Sistema", body_style)],
        [Paragraph("Correo de Contacto:", label_style), Paragraph(usuario.email or "Sin correo registrado", body_style)],
    ]

    t_datos = Table(datos_tabla, colWidths=[150, 380])
    t_datos.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))

    elements.append(t_datos)
    elements.append(Spacer(1, 20))

    cred_data = [
        [Paragraph("CREDENCIALES TEMPORALES ASIGNADAS", cred_title_style)],
        [Spacer(1, 6)],
        [Paragraph(f"<b>USUARIO (USERNAME):</b> &nbsp; {usuario.username}", ParagraphStyle('CredUser', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=16, alignment=1))],
        [Spacer(1, 6)],
        [Paragraph(f"<b>CONTRASEÑA TEMPORAL:</b>", ParagraphStyle('CredPassLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#7A1C21'), alignment=1))],
        [Spacer(1, 4)],
        [Paragraph(clave_temporal, cred_value_style)],
        [Spacer(1, 8)],
    ]

    t_cred = Table(cred_data, colWidths=[530])
    t_cred.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1E6532')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))

    elements.append(t_cred)
    elements.append(Spacer(1, 25))

    elements.append(Paragraph("<b>INSTRUCCIONES E INFORMACIÓN IMPORTANTE DE SEGURIDAD:</b>", label_style))
    elements.append(Spacer(1, 6))

    instrucciones = [
        "1. Ingrese a la plataforma ERP Escolar en su navegador web.",
        "2. Introduzca su <b>Nombre de Usuario</b> y la <b>Contraseña Temporal</b> exactamente como aparecen escritas arriba.",
        "3. Al iniciar sesión por primera vez con esta clave, el sistema le solicitará cambiar su contraseña por una personal y confidencial.",
        "4. Guarde este documento en un lugar seguro y no comparta sus credenciales con terceros.",
    ]

    for inst in instrucciones:
        elements.append(Paragraph(inst, body_style))
        elements.append(Spacer(1, 4))

    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=20))

    pie_tabla = [
        [Paragraph("__________________________________________", ParagraphStyle('FirmaLine', alignment=1)), Paragraph("__________________________________________", ParagraphStyle('FirmaLine2', alignment=1))],
        [Paragraph("Firma / Sello de Dirección / Administración", ParagraphStyle('FirmaLbl', fontName='Helvetica', fontSize=9, alignment=1, textColor=colors.HexColor('#64748B'))),
         Paragraph("Firma de Conformidad del Usuario", ParagraphStyle('FirmaLbl2', fontName='Helvetica', fontSize=9, alignment=1, textColor=colors.HexColor('#64748B')))]
    ]

    t_pie = Table(pie_tabla, colWidths=[265, 265])
    elements.append(t_pie)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
