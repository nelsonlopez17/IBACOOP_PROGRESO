"""
APPS/inventario/reports.py

Generación de reportes oficiales en PDF con ReportLab para el Módulo de Inventario y Control de Activos.
Incluye:
  1. Catálogo de Artículos e Reporte de Stock Institucional
  2. Comprobante / Acta de Resguardo y Movimiento de Inventario
"""
import io
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)


def generar_pdf_reporte_inventario(articulos, titulo="Reporte General de Inventario"):
    """
    Genera un informe PDF con el catálogo completo de inventario y estado de existencias.
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
    COLOR_BG = colors.HexColor('#F8FAFC')

    style_header = ParagraphStyle('HeaderTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, leading=16, textColor=COLOR_VERDE)
    style_sub = ParagraphStyle('HeaderSub', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=COLOR_GRIS)
    style_table_head = ParagraphStyle('THead', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white)
    style_table_cell = ParagraphStyle('TCell', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#0F172A'))
    style_table_bold = ParagraphStyle('TCellB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#0F172A'))

    header_data = [
        [
            Paragraph("<b>INSTITUTO DE EDUCACIÓN BÁSICA 'EL PROGRESO'</b><br/>"
                      "<font size=9 color='#64748B'>Guatemala, C.A. — Sistema ERP Scholar</font>", style_header),
            Paragraph(f"<b>FECHA DE IMPRESIÓN:</b><br/>{timezone.now().strftime('%d/%m/%Y %H:%M')}", style_sub)
        ]
    ]
    t_header = Table(header_data, colWidths=[380, 160])
    t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(t_header)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_VERDE, spaceAfter=12))

    story.append(Paragraph(f"<b>{titulo.upper()}</b>", ParagraphStyle('SubT', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=COLOR_VERDE)))
    story.append(Spacer(1, 8))

    rows = [[
        Paragraph('Código', style_table_head),
        Paragraph('Artículo', style_table_head),
        Paragraph('Categoría', style_table_head),
        Paragraph('Stock Actual', style_table_head),
        Paragraph('Stock Mín.', style_table_head),
        Paragraph('Estado', style_table_head),
    ]]

    total_items = 0
    total_unidades = 0
    alertas_count = 0

    for item in articulos:
        total_items += 1
        total_unidades += item.stock_actual
        if item.alerta_stock_bajo:
            alertas_count += 1
            estado_html = "<font color='#B91C1C'><b>⚠️ Stock Bajo</b></font>"
        else:
            estado_html = "<font color='#15803D'>Normal</font>"

        rows.append([
            Paragraph(item.codigo_unico, style_table_bold),
            Paragraph(f"<b>{item.nombre}</b><br/><font size=7 color='#64748B'>{item.unidad_medida}</font>", style_table_cell),
            Paragraph(item.get_categoria_display(), style_table_cell),
            Paragraph(f"{item.stock_actual}", style_table_bold),
            Paragraph(f"{item.stock_minimo_alerta}", style_table_cell),
            Paragraph(estado_html, style_table_cell),
        ])

    t_articulos = Table(rows, colWidths=[90, 160, 110, 60, 60, 60])
    t_articulos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG]),
    ]))
    story.append(t_articulos)
    story.append(Spacer(1, 14))

    summary_text = f"<b>Total de Artículos Distintos:</b> {total_items} | <b>Total de Unidades/Bienes Registrados:</b> {total_unidades} | <b>Alertas de Stock Bajo:</b> {alertas_count}"
    story.append(Paragraph(summary_text, ParagraphStyle('Summ', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=COLOR_AZUL)))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_pdf_comprobante_movimiento(movimiento):
    """
    Genera el Vale o Comprobante de Resguardo/Movimiento de Inventario en PDF.
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

    story = []
    styles = getSampleStyleSheet()

    COLOR_VERDE = colors.HexColor('#1E6532')
    COLOR_AZUL = colors.HexColor('#3C7DA8')
    COLOR_GRIS = colors.HexColor('#64748B')
    COLOR_BG = colors.HexColor('#F8FAFC')

    style_header = ParagraphStyle('HeaderTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, leading=15, textColor=COLOR_VERDE)
    style_sub = ParagraphStyle('HeaderSub', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=COLOR_GRIS)
    style_label = ParagraphStyle('Lbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_VERDE)
    style_val = ParagraphStyle('Val', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#0F172A'))

    story.append(Paragraph("<b>INSTITUTO DE EDUCACIÓN BÁSICA 'EL PROGRESO'</b>", style_header))
    story.append(Paragraph("Comprobante de Resguardo y Movimiento de Inventario Institucional", style_sub))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_VERDE, spaceAfter=12))

    story.append(Paragraph(f"<b>TRANSACCIÓN NO. #{movimiento.id:06d}</b>", ParagraphStyle('Code', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=COLOR_AZUL)))
    story.append(Spacer(1, 10))

    data = [
        [Paragraph("FECHA Y HORA:", style_label), Paragraph(movimiento.fecha.strftime("%d/%m/%Y %H:%M hrs"), style_val)],
        [Paragraph("TIPO DE MOVIMIENTO:", style_label), Paragraph(f"<b>{movimiento.get_tipo_movimiento_display()}</b>", style_val)],
        [Paragraph("ARTÍCULO AFECTADO:", style_label), Paragraph(f"[{movimiento.articulo.codigo_unico}] {movimiento.articulo.nombre}", style_val)],
        [Paragraph("CANTIDAD TRANSACTADA:", style_label), Paragraph(f"<b>{movimiento.cantidad} {movimiento.articulo.unidad_medida}</b>", style_val)],
        [Paragraph("PERSONAL RESPONSABLE:", style_label), Paragraph(f"{movimiento.personal_responsable.persona.nombre_completo} ({movimiento.personal_responsable.puesto.nombre_puesto})", style_val)],
        [Paragraph("DOCUMENTO DE REFERENCIA:", style_label), Paragraph(movimiento.documento_referencia or 'N/A', style_val)],
        [Paragraph("MOTIVO / DESTINO:", style_label), Paragraph(movimiento.motivo, style_val)],
    ]
    t_details = Table(data, colWidths=[160, 370])
    t_details.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t_details)
    story.append(Spacer(1, 50))

    t_firmas = Table([
        [
            Paragraph("___________________________________<br/><b>Entregado por / Dirección</b>", ParagraphStyle('F1', parent=styles['Normal'], fontName='Helvetica', fontSize=9, alignment=1)),
            Paragraph("___________________________________<br/><b>Firma de Recibido / Responsable</b><br/>"
                      f"<font size=8 color='#64748B'>{movimiento.personal_responsable.persona.nombre_completo}</font>", ParagraphStyle('F2', parent=styles['Normal'], fontName='Helvetica', fontSize=9, alignment=1))
        ]
    ], colWidths=[265, 265])
    story.append(t_firmas)

    doc.build(story)
    buffer.seek(0)
    return buffer
