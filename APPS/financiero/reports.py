"""
APPS/financiero/reports.py

Generación de reportes financieros en PDF con ReportLab para el Instituto El Progreso.
Incluye:
  1. Recibo Oficial de Pago / Comprobante de Abono en PDF.
  2. Constancia Oficial de Solvencia Financiera del Estudiante en PDF.
"""
import io
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)


def generar_pdf_recibo_pago(abono):
    """
    Genera el Recibo Oficial de Pago / Comprobante de Abono en PDF.
    Documento entregable al estudiante o encargado como comprobante contable.
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
    style_header_right = ParagraphStyle(
        'HeaderRight',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=COLOR_ROJO,
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
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0F172A')
    )
    style_monto = ParagraphStyle(
        'MontoDestacado',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=COLOR_VERDE,
        alignment=2
    )

    cuenta = abono.cuenta_por_cobrar
    estudiante = cuenta.estudiante
    persona = estudiante.persona

    header_data = [
        [
            Paragraph("INSTITUTO DE EDUCACIÓN BÁSICA<br/><font color='#7A1C21'>'EL PROGRESO'</font><br/><font size=8 color='#64748B'>SISTEMA DE GESTIÓN ESCOLAR (ERP)</font>", style_title),
            Paragraph(f"<b>RECIBO OFICIAL DE PAGO</b><br/>No. Recibo: <b>REC-{abono.pk:06d}</b><br/>Fecha: {abono.fecha_pago.strftime('%d/%m/%Y')}", style_header_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[330, 210])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_VERDE, spaceBefore=4, spaceAfter=12))

    story.append(Paragraph("1. DATOS DEL ESTUDIANTE", style_sec_header))
    story.append(Spacer(1, 4))

    datos_estudiante = [
        [Paragraph("Nombre Completo:", style_label), Paragraph(persona.nombre_completo, style_val_bold),
         Paragraph("CUI / DPI:", style_label), Paragraph(persona.cui, style_val)],
        [Paragraph("Código MINEDUC:", style_label), Paragraph(estudiante.codigo_mineduc, style_val_bold),
         Paragraph("Ciclo Escolar:", style_label), Paragraph(str(cuenta.ciclo_escolar.anio), style_val)]
    ]
    t_est = Table(datos_estudiante, colWidths=[110, 160, 110, 160])
    t_est.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_est)
    story.append(Spacer(1, 12))

    story.append(Paragraph("2. DETALLE DE LA TRANSACCIÓN FINANCIERA", style_sec_header))
    story.append(Spacer(1, 4))

    tipo_comprobante_label = "No. de Boleta Bancaria:" if abono.metodo_pago in ['DEPOSITO', 'TRANSFERENCIA'] else "No. de Recibo / Comprobante:"
    datos_pago = [
        [Paragraph("Concepto de Cobro:", style_label), Paragraph(cuenta.concepto.nombre, style_val_bold)],
        [Paragraph("Método de Pago:", style_label), Paragraph(f"<b>{abono.get_metodo_pago_display()}</b>", style_val_bold)],
        [Paragraph(tipo_comprobante_label, style_label), Paragraph(f"<b>{abono.numero_boleta}</b>", style_val_bold)],
        [Paragraph("Monto Original de la Cuota:", style_label), Paragraph(f"Q{cuenta.monto_total:,.2f}", style_val)],
        [Paragraph("MONTO ABONADO EN ESTE RECIBO:", style_label), Paragraph(f"<b>Q{abono.monto_pagado:,.2f}</b>", style_monto)],
        [Paragraph("Saldo Pendiente Restante:", style_label), Paragraph(f"Q{cuenta.saldo_pendiente:,.2f}", style_val_bold)],
        [Paragraph("Estado Actual de la Cuota:", style_label), Paragraph(f"<b>{cuenta.get_estado_pago_display().upper()}</b>", style_val_bold)],
        [Paragraph("Observaciones / Receptoría:", style_label), Paragraph(abono.observaciones or "Sin observaciones", style_val)]
    ]
    t_pago = Table(datos_pago, colWidths=[180, 360])
    t_pago.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_pago)
    story.append(Spacer(1, 24))

    style_nota = ParagraphStyle(
        'NotaContable',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=COLOR_GRIS
    )
    story.append(Paragraph(
        "<i>Nota: Este comprobante impreso acredita el recibo del abono o pago indicado arriba. "
        "Conserve esta boleta para cualquier consulta o trámite administrativo posterior.</i>",
        style_nota
    ))
    story.append(Spacer(1, 36))

    datos_firmas = [
        [Paragraph("_______________________________________<br/>Firma y Sello de Receptoría / Caja", ParagraphStyle('Ctr', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1)),
         Paragraph("_______________________________________<br/>Firma de Conformidad del Estudiante / Encargado", ParagraphStyle('Ctr2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1))]
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
    response['Content-Disposition'] = f'inline; filename="Recibo_{abono.numero_boleta}.pdf"'
    return response


def generar_pdf_solvencia_estudiante(estudiante, ciclo_escolar):
    """
    Genera la Constancia Oficial de Solvencia Financiera del Estudiante en PDF.
    Acredita oficialmente que el estudiante no posee pagos ni saldos pendientes en el ciclo escolar.
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
        alignment=1
    )
    style_subtitle = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=COLOR_ROJO,
        alignment=1
    )
    style_body = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        alignment=4  # Justified
    )
    style_val_bold = ParagraphStyle(
        'ValBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )

    persona = estudiante.persona

    story.append(Paragraph("INSTITUTO DE EDUCACIÓN BÁSICA 'EL PROGRESO'", style_title))
    story.append(Spacer(1, 4))
    story.append(Paragraph("DEPARTAMENTO DE CONTABILIDAD Y FINANZAS", style_subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_VERDE, spaceBefore=8, spaceAfter=20))

    style_doc_header = ParagraphStyle(
        'HeaderSolvencia',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=COLOR_AZUL,
        alignment=1
    )
    story.append(Paragraph("<b>CONSTANCIA DE SOLVENCIA FINANCIERA</b>", style_doc_header))
    story.append(Spacer(1, 20))

    texto_constancia = (
        f"La Dirección General y el Departamento de Contabilidad del <b>Instituto de Educación Básica 'El Progreso'</b>, "
        f"hacen constar por este medio que el/la estudiante: "
    )
    story.append(Paragraph(texto_constancia, style_body))
    story.append(Spacer(1, 10))

    datos_estudiante = [
        [Paragraph("Nombre Completo:", ParagraphStyle('L1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_GRIS)),
         Paragraph(persona.nombre_completo, style_val_bold)],
        [Paragraph("CUI / DPI:", ParagraphStyle('L2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_GRIS)),
         Paragraph(persona.cui, style_val_bold)],
        [Paragraph("Código MINEDUC:", ParagraphStyle('L3', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_GRIS)),
         Paragraph(estudiante.codigo_mineduc, style_val_bold)],
        [Paragraph("Ciclo Escolar:", ParagraphStyle('L4', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_GRIS)),
         Paragraph(f"<b>{ciclo_escolar.anio}</b>", style_val_bold)],
        [Paragraph("Estado Financiero:", ParagraphStyle('L5', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_GRIS)),
         Paragraph("<font color='#1E6532'><b>SOLVENTE (SIN DEUDAS PENDIENTES)</b></font>", style_val_bold)]
    ]
    t_sol = Table(datos_estudiante, colWidths=[140, 400])
    t_sol.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_sol)
    story.append(Spacer(1, 16))

    texto_cierre = (
        f"Se extiende la presente constancia de solvencia a solicitud del interesado para los trámites académicos "
        f"y administrativos correspondientes al Ciclo Lectivo <b>{ciclo_escolar.anio}</b>, haciendo constar que el "
        f"estudiante ha cumplido a cabalidad con la totalidad de sus obligaciones financieras institucionales."
    )
    story.append(Paragraph(texto_cierre, style_body))
    story.append(Spacer(1, 40))

    datos_firmas = [
        [Paragraph("_______________________________________<br/><b>Licda. Receptoría y Contabilidad</b><br/>Instituto El Progreso", ParagraphStyle('Ctr', parent=styles['Normal'], fontName='Helvetica', fontSize=9, alignment=1)),
         Paragraph("_______________________________________<br/><b>Director General</b><br/>Instituto El Progreso", ParagraphStyle('Ctr2', parent=styles['Normal'], fontName='Helvetica', fontSize=9, alignment=1))]
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
    response['Content-Disposition'] = f'inline; filename="Solvencia_{estudiante.persona.cui}.pdf"'
    return response
