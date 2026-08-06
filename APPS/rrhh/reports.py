"""
APPS/rrhh/reports.py

Generación de reportes oficiales en PDF con ReportLab para el Módulo de Recursos Humanos de IBACOOP EL PROGRESO.
Incluye:
  1. Ficha Única del Expediente Físico del Colaborador / Empleado
  2. Comprobante de Credenciales de Acceso a la Plataforma ERP (con Usuario CUI/DPI y Clave Temporal)
"""
import io
import random
import string
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)


def generar_password_temporal(longitud=10):
    """Genera una contraseña temporal aleatoria y segura."""
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        pwd = ''.join(random.choice(caracteres) for _ in range(longitud))
        if (any(c.islower() for c in pwd) and
            any(c.isupper() for c in pwd) and
            any(c.isdigit() for c in pwd) and
            any(c in "!@#$%&*" for c in pwd)):
            return pwd


def generar_pdf_expediente_empleado(personal):
    """
    Genera la Ficha Única de Registro y Expediente Físico del Empleado en PDF.
    Documento oficial para folder físico en Secretaría.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Estilos Corporativos IBACOOP EL PROGRESO
    COLOR_VERDE = colors.HexColor('#1E6532')
    COLOR_ROJO = colors.HexColor('#7A1C21')
    COLOR_AZUL = colors.HexColor('#3C7DA8')
    COLOR_GRIS = colors.HexColor('#64748B')
    COLOR_BG_SLATE = colors.HexColor('#F8FAFC')

    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=COLOR_VERDE
    )
    style_header_right = ParagraphStyle(
        'HeaderRight',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=COLOR_GRIS,
        alignment=2
    )
    style_sec_header = ParagraphStyle(
        'SecHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=COLOR_VERDE
    )
    style_label = ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=COLOR_GRIS
    )
    style_val = ParagraphStyle(
        'FieldValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A')
    )
    style_val_bold = ParagraphStyle(
        'FieldValueBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A')
    )

    persona = personal.persona

    # 1. Encabezado Oficial Institucional
    header_data = [
        [
            Paragraph("INSTITUTO DE EDUCACIÓN BÁSICA<br/><font color='#7A1C21'>'EL PROGRESO'</font>", style_title),
            Paragraph("<b>FICHA DE EXPEDIENTE DE PERSONAL</b><br/>DPI / CUI: <b>" + persona.cui + "</b><br/>Fecha: <b>2026</b>", style_header_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[320, 220])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_VERDE, spaceBefore=4, spaceAfter=12))

    # 2. Datos Personales del Colaborador
    story.append(Paragraph("1. INFORMACIÓN PERSONAL DEL COLABORADOR", style_sec_header))
    story.append(Spacer(1, 4))

    datos_personales = [
        [Paragraph("Nombre Completo:", style_label), Paragraph(persona.nombre_completo, style_val_bold),
         Paragraph("DPI / CUI (RENAP):", style_label), Paragraph(persona.cui, style_val_bold)],
        [Paragraph("Fecha Nacimiento:", style_label), Paragraph(persona.fecha_nacimiento.strftime("%d/%m/%Y") if persona.fecha_nacimiento else "No registrada", style_val),
         Paragraph("Género:", style_label), Paragraph(persona.get_genero_display() or "N/A", style_val)],
        [Paragraph("Teléfono Principal:", style_label), Paragraph(persona.telefono_principal or "N/A", style_val),
         Paragraph("Correo Electrónico:", style_label), Paragraph(persona.correo or "N/A", style_val)],
        [Paragraph("Dirección Domiciliar:", style_label), Paragraph(persona.direccion or "No registrada", style_val),
         Paragraph("Contacto Emergencia:", style_label), Paragraph(f"{personal.contacto_emergencia_nombre or 'N/A'} ({personal.contacto_emergencia_telefono or 'N/A'})", style_val)]
    ]
    t_pers = Table(datos_personales, colWidths=[110, 160, 110, 160])
    t_pers.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_pers)
    story.append(Spacer(1, 12))

    # 3. Detalles Laborales y Resguardo de Contrato Físico
    story.append(Paragraph("2. DETALLES LABORALES Y RESGUARDO DE CONTRATO FÍSICO", style_sec_header))
    story.append(Spacer(1, 4))

    datos_laborales = [
        [Paragraph("Puesto / Cargo:", style_label), Paragraph(personal.puesto.nombre_puesto, style_val_bold),
         Paragraph("Estado Laboral:", style_label), Paragraph(personal.get_estado_laboral_display(), style_val_bold)],
        [Paragraph("NIT (SAT):", style_label), Paragraph(personal.nit or "No registrado", style_val),
         Paragraph("Fecha Contratación:", style_label), Paragraph(personal.fecha_contratacion.strftime("%d/%m/%Y") if personal.fecha_contratacion else "N/A", style_val)],
        [Paragraph("Salario Base (Q):", style_label), Paragraph(f"Q{personal.salario_base_asignado}", style_val_bold),
         Paragraph("No. Contrato Físico:", style_label), Paragraph(personal.numero_contrato_fisico or "Pendiente de asignar", style_val)],
        [Paragraph("Ubicación Físico:", style_label), Paragraph(personal.ubicacion_expediente_fisico or "Archivador general", style_val_bold),
         Paragraph("Usuario Acceso:", style_label), Paragraph(persona.usuario.username if persona.usuario else "Sin cuenta", style_val)]
    ]
    t_lab = Table(datos_laborales, colWidths=[110, 160, 110, 160])
    t_lab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_lab)
    story.append(Spacer(1, 12))

    # 4. Checklist Papelería Obligatoria Nivel Medio (Guatemala)
    story.append(Paragraph("3. CHECKLIST DE PAPELERÍA OBLIGATORIA (EXPEDIENTE FÍSICO EN SECRETARÍA)", style_sec_header))
    story.append(Spacer(1, 4))

    doc_dpi = "[ X ] Entregado" if personal.doc_dpi_personal else "[   ] PENDIENTE"
    doc_nit = "[ X ] Entregado" if personal.doc_nit_sat else "[   ] PENDIENTE"
    doc_titulo = "[ X ] Entregado" if personal.doc_titulo_academico else "[   ] PENDIENTE"
    doc_col = "[ X ] Entregado" if personal.doc_colegiado_activo else "[   ] PENDIENTE"
    doc_pen = "[ X ] Entregado" if personal.doc_antecedentes_penales else "[   ] PENDIENTE"
    doc_pol = "[ X ] Entregado" if personal.doc_antecedentes_policiales else "[   ] PENDIENTE"
    doc_con = "[ X ] Entregado" if personal.doc_contrato_fisico else "[   ] PENDIENTE"
    doc_salud = "[ X ] Entregado" if personal.doc_tarjeta_salud else "[   ] PENDIENTE"

    datos_papeleria = [
        [Paragraph("1. Fotocopia de DPI / CUI (RENAP)", style_label), Paragraph(doc_dpi, style_val_bold)],
        [Paragraph("2. Constancia de NIT (RTU SAT)", style_label), Paragraph(doc_nit, style_val_bold)],
        [Paragraph("3. Fotocopia de Título Académico / Cédula Docente", style_label), Paragraph(doc_titulo, style_val_bold)],
        [Paragraph("4. Constancia Colegiado Activo / Acreditación MINEDUC", style_label), Paragraph(doc_col, style_val_bold)],
        [Paragraph("5. Antecedentes Penales (Vigentes)", style_label), Paragraph(doc_pen, style_val_bold)],
        [Paragraph("6. Antecedentes Policiales (Vigentes)", style_label), Paragraph(doc_pol, style_val_bold)],
        [Paragraph("7. Contrato Físico de Trabajo Firmado", style_label), Paragraph(doc_con, style_val_bold)],
        [Paragraph("8. Tarjeta de Salud / Sanidad", style_label), Paragraph(doc_salud, style_val_bold)],
        [Paragraph("ESTADO GLOBAL DEL EXPEDIENTE FÍSICO:", style_sec_header),
         Paragraph(f"<b>{personal.porcentaje_expediente}% COMPLETADO ({personal.documentos_entregados_count}/8)</b>", style_val_bold)]
    ]
    t_doc = Table(datos_papeleria, colWidths=[360, 180])
    t_doc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_doc)
    story.append(Spacer(1, 25))

    # 5. Firmas de Resguardo
    datos_firmas = [
        [Paragraph("_______________________________________<br/>Firma y Sello de Secretaría", style_header_right),
         Paragraph("_______________________________________<br/>Firma del Colaborador / Empleado", style_header_right)]
    ]
    t_firmas = Table(datos_firmas, colWidths=[270, 270])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
    ]))
    story.append(t_firmas)

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Expediente_Empleado_{persona.cui}.pdf"'
    return response


def generar_pdf_credenciales_empleado(personal, clave_temporal=None):
    """
    Genera el Comprobante Oficial de Apertura de Cuenta de Acceso para el Empleado.
    Constancia entregable física con Usuario (DPI) y Clave Temporal.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    COLOR_VERDE = colors.HexColor('#1E6532')
    COLOR_ROJO = colors.HexColor('#7A1C21')
    COLOR_AZUL = colors.HexColor('#3C7DA8')
    COLOR_GRIS = colors.HexColor('#64748B')
    COLOR_BG_SLATE = colors.HexColor('#F8FAFC')

    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=COLOR_VERDE
    )
    style_subtitle = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=COLOR_AZUL
    )
    style_label = ParagraphStyle(
        'FieldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=COLOR_GRIS
    )
    style_val_bold = ParagraphStyle(
        'FieldValueBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )
    style_body = ParagraphStyle(
        'BodyTxt',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    persona = personal.persona
    usuario = persona.usuario

    # 1. Encabezado
    header_data = [
        [
            Paragraph("INSTITUTO DE EDUCACIÓN BÁSICA 'EL PROGRESO'<br/><font size=8 color='#7A1C21'>SISTEMA ERP INSTITUCIONAL</font>", style_title),
            Paragraph("<b>CREDENCIALES DE ACCESO</b><br/>Fecha: <b>2026</b>", style_subtitle)
        ]
    ]
    t_header = Table(header_data, colWidths=[340, 200])
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_AZUL, spaceBefore=6, spaceAfter=14))

    # 2. Aviso Informativo
    story.append(Paragraph(
        "El presente documento otorga las credenciales de acceso a la plataforma ERP del Instituto El Progreso. "
        "Por políticas de seguridad de la institución, <b>deberá cambiar su contraseña temporal en su primer inicio de sesión</b>.",
        style_body
    ))
    story.append(Spacer(1, 12))

    # 3. Credenciales del Empleado
    pwd_mostrar = clave_temporal or "(Contraseña previamente asignada)"
    rol_nombre = usuario.get_rol_display() if usuario else personal.puesto.nombre_puesto

    cred_data = [
        [Paragraph("Nombre del Colaborador:", style_label), Paragraph(persona.nombre_completo, style_body)],
        [Paragraph("Puesto Asignado:", style_label), Paragraph(personal.puesto.nombre_puesto, style_body)],
        [Paragraph("DPI / CUI (Usuario):", style_label), Paragraph(f"<b>{persona.cui}</b>", style_val_bold)],
        [Paragraph("Contraseña Temporal:", style_label), Paragraph(f"<font color='#7A1C21'><b>{pwd_mostrar}</b></font>", style_val_bold)],
        [Paragraph("Rol en el Sistema:", style_label), Paragraph(rol_nombre, style_body)]
    ]
    t_cred = Table(cred_data, colWidths=[150, 390])
    t_cred.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_cred)
    story.append(Spacer(1, 16))

    # 4. Instrucciones de Acceso
    story.append(Paragraph("<b>INSTRUCCIONES PARA EL PRIMER ACCESO:</b>", style_label))
    story.append(Spacer(1, 4))
    story.append(Paragraph("1. Ingrese a la plataforma web del Instituto El Progreso.", style_body))
    story.append(Paragraph("2. En la pantalla de inicio de sesión, ingrese su <b>DPI / CUI de 13 dígitos</b> (o su Correo Electrónico).", style_body))
    story.append(Paragraph("3. Ingrese la contraseña temporal indicada en este comprobante.", style_body))
    story.append(Paragraph("4. El sistema le desplegará automáticamente la pantalla para establecer su nueva contraseña privada.", style_body))
    story.append(Spacer(1, 35))

    # 5. Firma de Recepción
    datos_firma = [
        [Paragraph("_______________________________________<br/>Firma de Recepción del Colaborador", style_subtitle)]
    ]
    t_f = Table(datos_firma, colWidths=[540])
    t_f.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(t_f)

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Credenciales_Empleado_{persona.cui}.pdf"'
    return response
