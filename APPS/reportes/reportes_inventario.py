"""
reportes/reportes_inventario.py

Generación de reportes de Inventario y Control de Activos para el Instituto El Progreso:
  1. Inventario Físico Valorado y Estado de Existencias (PDF y CSV)
"""
import io
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from APPS.reportes.generadores.base_pdf import (
    NumberedCanvas, ReportLabHelper, COLOR_VERDE, COLOR_ROJO, COLOR_AZUL, COLOR_TEXT, COLOR_MUTED, COLOR_BG_LIGHT, COLOR_BORDER
)
from APPS.reportes.generadores.base_csv import IBACOOPReportCSV
from APPS.inventario.models import ArticuloInventario


def generar_pdf_inventario_valorado():
    """Genera informe en PDF del inventario físico institucional."""
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
    styles = ReportLabHelper.get_styles()
    articulos = ArticuloInventario.objects.filter(esta_eliminado=False).order_by('categoria', 'codigo_unico')

    story.append(ReportLabHelper.build_header(
        doc_title="INVENTARIO FÍSICO INSTITUCIONAL Y CONTROL DE ACTIVOS",
        subtitle="Registro y Existencias en Bodegas y Aulas"
    ))
    story.append(Spacer(1, 10))

    tabla_data = [
        [
            Paragraph("<b>CÓDIGO</b>", styles['th']),
            Paragraph("<b>NOMBRE / DESCRIPCIÓN</b>", styles['th']),
            Paragraph("<b>CATEGORÍA</b>", styles['th']),
            Paragraph("<b>STOCK ACTUAL</b>", styles['th']),
            Paragraph("<b>ESTADO</b>", styles['th']),
        ]
    ]

    for a in articulos:
        estado_str = "<font color='#7A1C21'><b>STOCK BAJO</b></font>" if a.alerta_stock_bajo else "<font color='#1E6532'>DISPONIBLE</font>"
        tabla_data.append([

            Paragraph(f"<b>{a.codigo_unico}</b>", styles['td']),
            Paragraph(a.nombre, styles['td']),
            Paragraph(a.get_categoria_display() if hasattr(a, 'get_categoria_display') else str(a.categoria), styles['td']),
            Paragraph(f"<b>{a.stock_actual}</b> {a.unidad_medida}", styles['td_center']),
            Paragraph(estado_str, styles['td_center']),
        ])


    col_widths = [90, 220, 100, 70, 60]
    t_inv = Table(tabla_data, colWidths=col_widths)
    t_inv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(t_inv)
    story.append(Spacer(1, 25))

    story.append(ReportLabHelper.build_signature_block([
        "Encargado(a) de Inventario",
        "Director (a)"
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Inventario_Institucional_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response


def generar_csv_inventario_valorado():
    """Genera exportación CSV del inventario físico."""
    articulos = ArticuloInventario.objects.filter(esta_eliminado=False).order_by('categoria', 'codigo_unico')
    headers = ['Código', 'Nombre del Artículo', 'Categoría', 'Stock Actual', 'Stock Mínimo', 'Unidad de Medida', 'Estado']
    rows = []

    for a in articulos:
        rows.append([
            a.codigo_unico,
            a.nombre,
            a.get_categoria_display() if hasattr(a, 'get_categoria_display') else str(a.categoria),
            a.stock_actual,
            a.stock_minimo_alerta,
            a.unidad_medida,
            "STOCK BAJO" if a.alerta_stock_bajo else "DISPONIBLE"
        ])


    return IBACOOPReportCSV.generate_csv_response('Inventario_Fisico', headers, rows)

