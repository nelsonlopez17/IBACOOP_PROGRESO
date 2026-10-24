"""
APPS/estudiantes/reports.py

Generación de reportes oficiales en PDF con ReportLab para el Instituto El Progreso.
Incluye:
  1. Ficha Única del Expediente del Estudiante (Secretaría / Archivo Físico)
  2. Constancia de Credenciales de Acceso al Sistema (Encargado / Estudiante)
"""
import io
import random
import string
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
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


def generar_pdf_expediente_estudiante(estudiante):
    """
    Genera la Ficha Única de Registro y Expediente Oficial del Estudiante en PDF.
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

    COLOR_VERDE = colors.HexColor('#1E6532')
    COLOR_ROJO = colors.HexColor('#7A1C21')
    COLOR_AZUL = colors.HexColor('#3C7DA8')
    COLOR_GRIS = colors.HexColor('#64748B')
    COLOR_BG_SLATE = colors.HexColor('#F8FAFC')

    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=COLOR_VERDE,
        alignment=0
    )
    style_subtitle = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=COLOR_ROJO,
        alignment=0
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

    header_data = [
        [
            Paragraph("INSTITUTO DE EDUCACIÓN BÁSICA<br/><font color='#7A1C21'>'EL PROGRESO'</font>", style_title),
            Paragraph("<b>FICHA ÚNICA DE EXPEDIENTE</b><br/>Código MINEDUC: <b>" + estudiante.codigo_mineduc + "</b><br/>Ciclo Escolar 2026", style_header_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[320, 220])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_VERDE, spaceBefore=4, spaceAfter=12))

    story.append(Paragraph("1. DATOS PERSONALES DEL ESTUDIANTE", style_sec_header))
    story.append(Spacer(1, 4))

    persona = estudiante.persona
    datos_personales = [
        [Paragraph("Nombre Completo:", style_label), Paragraph(persona.nombre_completo, style_val_bold),
         Paragraph("CUI / DPI:", style_label), Paragraph(persona.cui, style_val)],
        [Paragraph("Fecha Nacimiento:", style_label), Paragraph(persona.fecha_nacimiento.strftime("%d/%m/%Y") if persona.fecha_nacimiento else "No registrada", style_val),
         Paragraph("Género:", style_label), Paragraph(persona.get_genero_display() or "N/A", style_val)],
        [Paragraph("Teléfono Principal:", style_label), Paragraph(persona.telefono_principal or "N/A", style_val),
         Paragraph("Correo Electrónico:", style_label), Paragraph(persona.correo or "N/A", style_val)],
        [Paragraph("Dirección Domiciliar:", style_label), Paragraph(persona.direccion or "No registrada", style_val),
         Paragraph("Estado Académico:", style_label), Paragraph(estudiante.get_estado_estudiante_display(), style_val_bold)]
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

    story.append(Paragraph("2. PADRE DE FAMILIA O ENCARGADO Y NÚCLEO FAMILIAR (SIRE MINEDUC)", style_sec_header))
    story.append(Spacer(1, 4))

    encargado = estudiante.encargado
    enc_nombre = encargado.persona.nombre_completo if encargado else "No asignado"
    enc_cui = encargado.persona.cui if encargado else "N/A"
    enc_tel = encargado.persona.telefono_principal if encargado else "N/A"
    enc_trabajo = encargado.lugar_de_trabajo if encargado else "N/A"

    datos_familia = [
        [Paragraph("Padre de Familia o Encargado:", style_label), Paragraph(enc_nombre, style_val_bold),
         Paragraph("CUI Encargado:", style_label), Paragraph(enc_cui, style_val)],
        [Paragraph("Teléfono Encargado:", style_label), Paragraph(enc_tel, style_val),
         Paragraph("Lugar de Trabajo:", style_label), Paragraph(enc_trabajo, style_val)],
        [Paragraph("Nombre del Padre:", style_label), Paragraph(estudiante.nombre_padre or "No registrado", style_val),
         Paragraph("Teléfono del Padre:", style_label), Paragraph(estudiante.telefono_padre or "N/A", style_val)],
        [Paragraph("Nombre de la Madre:", style_label), Paragraph(estudiante.nombre_madre or "No registrada", style_val),
         Paragraph("Teléfono de la Madre:", style_label), Paragraph(estudiante.telefono_madre or "N/A", style_val)]
    ]
    t_fam = Table(datos_familia, colWidths=[130, 140, 110, 160])
    t_fam.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_fam)
    story.append(Spacer(1, 12))

    story.append(Paragraph("3. CHECKLIST DE EXPEDIENTE FÍSICO (REQUISITOS OBLIGATORIOS MINEDUC)", style_sec_header))
    story.append(Spacer(1, 4))

    doc_renap = "[ X ] Entregado" if estudiante.doc_cert_nacimiento_renap else "[   ] PENDIENTE"
    doc_dpi = "[ X ] Entregado" if estudiante.doc_dpi_encargado else "[   ] PENDIENTE"
    doc_certificado = "[ X ] Entregado" if estudiante.doc_certificado_grado_anterior else "[   ] PENDIENTE"
    doc_diploma = "[ X ] Entregado" if estudiante.doc_diploma_primaria else "[   ] PENDIENTE"
    doc_codigo = "[ X ] Entregado" if estudiante.doc_codigo_mineduc else "[   ] PENDIENTE"

    datos_papeleria = [
        [Paragraph("1. Certificado de Nacimiento RENAP (con CUI)", style_label), Paragraph(doc_renap, style_val_bold)],
        [Paragraph("2. Fotocopia de DPI del Padre / Encargado", style_label), Paragraph(doc_dpi, style_val_bold)],
        [Paragraph("3. Certificado de Estudios del Grado Anterior", style_label), Paragraph(doc_certificado, style_val_bold)],
        [Paragraph("4. Diploma de Educación Primaria (para 1ro Básico)", style_label), Paragraph(doc_diploma, style_val_bold)],
        [Paragraph("5. Constancia de Código Personal MINEDUC (SIRE)", style_label), Paragraph(doc_codigo, style_val_bold)],
        [Paragraph("ESTADO GLOBAL DEL EXPEDIENTE:", style_sec_header),
         Paragraph("<b>EXPEDIENTE COMPLETO</b>" if estudiante.expediente_completo else "<font color='#7A1C21'><b>INCOMPLETO (" + str(estudiante.documentos_entregados_count) + "/5)</b></font>", style_val_bold)]
    ]
    t_doc = Table(datos_papeleria, colWidths=[360, 180])
    t_doc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_doc)
    story.append(Spacer(1, 12))

    if estudiante.historial_medico:
        story.append(Paragraph("4. HISTORIAL MÉDICO Y ANTECEDENTES DE SALUD", style_sec_header))
        story.append(Spacer(1, 4))
        t_med = Table([[Paragraph(estudiante.historial_medico, style_val)]], colWidths=[540])
        t_med.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFF1F2')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FECDD3')),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t_med)
        story.append(Spacer(1, 20))

    story.append(Spacer(1, 30))
    datos_firmas = [
        [Paragraph("_______________________________________<br/>Firma y Sello de Secretaría", style_header_right),
         Paragraph("_______________________________________<br/>Firma de Conformidad del Padre de Familia o Encargado", style_header_right)]
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
    response['Content-Disposition'] = f'inline; filename="Expediente_{estudiante.codigo_mineduc}.pdf"'
    return response


def generar_pdf_credenciales_acceso(estudiante, clave_temporal_estudiante=None, clave_temporal_tutor=None):
    """
    Genera el Comprobante Oficial de Apertura de Cuenta y Credenciales de Acceso.
    Constancia entregable al Padre de Familia o Encargado / Estudiante.
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

    header_data = [
        [
            Paragraph("INSTITUTO DE EDUCACIÓN BÁSICA 'EL PROGRESO'<br/><font size=8 color='#7A1C21'>SISTEMA DE GESTIÓN ESCOLAR (ERP)</font>", style_title),
            Paragraph("<b>COMPROBANTE DE CREDENCIALES</b><br/>Fecha: <b>2026</b>", style_subtitle)
        ]
    ]
    t_header = Table(header_data, colWidths=[340, 200])
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_AZUL, spaceBefore=6, spaceAfter=14))

    story.append(Paragraph(
        "El presente documento contiene las credenciales iniciales de acceso a la plataforma digital del Instituto El Progreso. "
        "Por políticas de seguridad, <b>deberá cambiar su contraseña temporal en su primer inicio de sesión</b>.",
        style_body
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>CREDENCIALES DE ACCESO DEL ESTUDIANTE</b>", style_subtitle))
    story.append(Spacer(1, 4))
    
    pwd_estudiante = clave_temporal_estudiante or "(Generada en registro)"
    cred_estudiante = [
        [Paragraph("Nombre del Estudiante:", style_label), Paragraph(estudiante.persona.nombre_completo, style_body)],
        [Paragraph("CUI / DPI (Usuario):", style_label), Paragraph(f"<b>{estudiante.persona.cui}</b>", style_val_bold)],
        [Paragraph("Código MINEDUC:", style_label), Paragraph(f"<b>{estudiante.codigo_mineduc}</b>", style_body)],
        [Paragraph("Contraseña Temporal:", style_label), Paragraph(f"<font color='#7A1C21'><b>{pwd_estudiante}</b></font>", style_val_bold)],
        [Paragraph("Rol asignado:", style_label), Paragraph("Estudiante", style_body)]
    ]
    t_est = Table(cred_estudiante, colWidths=[150, 390])
    t_est.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_est)
    story.append(Spacer(1, 16))

    story.append(Paragraph("<b>INSTRUCCIONES PARA EL PRIMER ACCESO:</b>", style_label))
    story.append(Paragraph("1. Ingrese a la plataforma web del Instituto El Progreso.", style_body))
    story.append(Paragraph("2. Ingrese su Nombre de Usuario (DPI / CUI de 13 dígitos del estudiante).", style_body))
    story.append(Paragraph("3. Ingrese la contraseña temporal proporcionada arriba.", style_body))
    story.append(Paragraph("4. El sistema le solicitará automáticamente definir una nueva contraseña personal y privada.", style_body))
    story.append(Spacer(1, 30))

    datos_firma = [
        [Paragraph("_______________________________________<br/>Firma de Recepción del Estudiante / Padre de Familia o Encargado", style_subtitle)]
    ]
    t_f = Table(datos_firma, colWidths=[540])
    t_f.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(t_f)

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Credenciales_Estudiante_{estudiante.persona.cui}.pdf"'
    return response


def generar_pdf_credenciales_encargado(encargado, clave_temporal=None):
    """
    Genera un comprobante en PDF con las credenciales temporales de un Padre de Familia o Encargado.
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

    COLOR_VERDE = colors.HexColor('#1E6532')
    COLOR_AZUL = colors.HexColor('#3C7DA8')
    COLOR_GRIS = colors.HexColor('#64748B')
    COLOR_BG_SLATE = colors.HexColor('#F8FAFC')

    styles = getSampleStyleSheet()
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

    header_data = [
        [
            Paragraph("INSTITUTO DE EDUCACIÓN BÁSICA 'EL PROGRESO'<br/><font size=8 color='#7A1C21'>SISTEMA DE GESTIÓN ESCOLAR (ERP)</font>", style_title),
            Paragraph("<b>CREDENCIALES DE ENCARGADO</b><br/>Fecha: <b>2026</b>", style_subtitle)
        ]
    ]
    t_header = Table(header_data, colWidths=[340, 200])
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_AZUL, spaceBefore=6, spaceAfter=14))

    story.append(Paragraph(
        "El presente documento contiene las credenciales de acceso para el Padre de Familia o Encargado. "
        "Permite el seguimiento de expedientes, estados de cuenta y rendimiento de los estudiantes bajo su cuidado. "
        "Por políticas de seguridad, <b>deberá cambiar su contraseña temporal en su primer inicio de sesión</b>.",
        style_body
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>CREDENCIALES DE ACCESO DEL PADRE DE FAMILIA O ENCARGADO</b>", style_subtitle))
    story.append(Spacer(1, 4))
    
    pwd_encargado = clave_temporal or "(Generada en registro)"
    cred_encargado = [
        [Paragraph("Nombre del Encargado:", style_label), Paragraph(encargado.persona.nombre_completo, style_body)],
        [Paragraph("DPI / CUI (Usuario):", style_label), Paragraph(f"<b>{encargado.persona.cui}</b>", style_val_bold)],
        [Paragraph("Teléfono de Contacto:", style_label), Paragraph(encargado.persona.telefono_principal or "N/A", style_body)],
        [Paragraph("Contraseña Temporal:", style_label), Paragraph(f"<font color='#7A1C21'><b>{pwd_encargado}</b></font>", style_val_bold)],
        [Paragraph("Rol asignado:", style_label), Paragraph("Encargado (Acceso Multihijos)", style_body)]
    ]
    t_enc = Table(cred_encargado, colWidths=[150, 390])
    t_enc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_enc)
    story.append(Spacer(1, 16))

    story.append(Paragraph("<b>INSTRUCCIONES PARA EL PRIMER ACCESO:</b>", style_label))
    story.append(Paragraph("1. Ingrese a la plataforma web del Instituto El Progreso.", style_body))
    story.append(Paragraph("2. Ingrese su DPI / CUI (13 dígitos) como Nombre de Usuario.", style_body))
    story.append(Paragraph("3. Ingrese la contraseña temporal proporcionada arriba.", style_body))
    story.append(Paragraph("4. Defina su contraseña personal y privada al ingresar por primera vez.", style_body))
    story.append(Spacer(1, 30))

    datos_firma = [
        [Paragraph("_______________________________________<br/>Firma de Recepción del Padre de Familia o Encargado", style_subtitle)]
    ]
    t_f = Table(datos_firma, colWidths=[540])
    t_f.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(t_f)

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Credenciales_Encargado_{encargado.persona.cui}.pdf"'
    return response

