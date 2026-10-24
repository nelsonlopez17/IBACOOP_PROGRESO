"""
reportes/reportes_financieros.py

Generación de reportes financieros y de cartera para el Instituto El Progreso:
  1. Antigüedad de Saldos y Morosidad (PDF y CSV)
  2. Cuadre Diario y Recaudación de Caja (PDF y CSV)
  3. Relación de Becas y Descuentos Otorgados (CSV)
"""
import io
from decimal import Decimal
from datetime import date
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from APPS.reportes.generadores.base_pdf import (
    NumberedCanvas, ReportLabHelper, COLOR_VERDE, COLOR_ROJO, COLOR_AZUL, COLOR_TEXT, COLOR_MUTED, COLOR_BG_LIGHT, COLOR_BORDER
)
from APPS.reportes.generadores.base_csv import IBACOOPReportCSV
from APPS.financiero.models import CuentaPorCobrar, Abono, BecaDescuento


def generar_pdf_antiguedad_saldos(ciclo_escolar=None):
    """
    Genera el Reporte Oficial de Antigüedad de Saldos y Morosidad en PDF (Orientación Horizontal).
    Estratifica las deudas en: Al día, 1-30 días, 31-60 días, 61-90 días, +90 días.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = ReportLabHelper.get_styles()

    cuentas = CuentaPorCobrar.objects.filter(
        esta_eliminado=False,
        saldo_pendiente__gt=0
    ).select_related('estudiante', 'estudiante__persona', 'concepto', 'ciclo_escolar')

    if ciclo_escolar:
        cuentas = cuentas.filter(ciclo_escolar=ciclo_escolar)

    hoy = timezone.now().date()

    story.append(ReportLabHelper.build_header(
        doc_title="REPORTE DE ANTIGÜEDAD DE SALDOS Y MOROSIDAD DE CARTERA",
        subtitle=f"Corte al {hoy.strftime('%d/%m/%Y')} • Valores expresados en Quetzales (Q)",
        orientation_landscape=True
    ))
    story.append(Spacer(1, 10))

    tabla_data = [
        [
            Paragraph("<b>ESTUDIANTE / CUI</b>", styles['th']),
            Paragraph("<b>CONCEPTO</b>", styles['th']),
            Paragraph("<b>VENCIMIENTO</b>", styles['th']),
            Paragraph("<b>AL DÍA (Q)</b>", styles['th']),
            Paragraph("<b>1-30 DÍAS (Q)</b>", styles['th']),
            Paragraph("<b>31-60 DÍAS (Q)</b>", styles['th']),
            Paragraph("<b>61-90 DÍAS (Q)</b>", styles['th']),
            Paragraph("<b>+90 DÍAS (Q)</b>", styles['th']),
            Paragraph("<b>TOTAL SALDO (Q)</b>", styles['th']),
        ]
    ]

    totales = {
        'al_dia': Decimal(0),
        'dias_1_30': Decimal(0),
        'dias_31_60': Decimal(0),
        'dias_61_90': Decimal(0),
        'mas_90': Decimal(0),
        'total': Decimal(0),
    }

    for c in cuentas:
        dias_mora = (hoy - c.fecha_limite_pago).days if c.fecha_limite_pago and hoy > c.fecha_limite_pago else 0
        saldo = c.saldo_pendiente

        al_dia = saldo if dias_mora <= 0 else Decimal(0)
        d_1_30 = saldo if 1 <= dias_mora <= 30 else Decimal(0)
        d_31_60 = saldo if 31 <= dias_mora <= 60 else Decimal(0)
        d_61_90 = saldo if 61 <= dias_mora <= 90 else Decimal(0)
        d_mas_90 = saldo if dias_mora > 90 else Decimal(0)

        totales['al_dia'] += al_dia
        totales['dias_1_30'] += d_1_30
        totales['dias_31_60'] += d_31_60
        totales['dias_61_90'] += d_61_90
        totales['mas_90'] += d_mas_90
        totales['total'] += saldo

        tabla_data.append([
            Paragraph(f"<b>{c.estudiante.persona.nombre_completo}</b><br/><font size=6 color='#64748B'>CUI: {c.estudiante.persona.cui}</font>", styles['td']),
            Paragraph(c.concepto.nombre, styles['td']),
            Paragraph(c.fecha_limite_pago.strftime('%d/%m/%Y') if c.fecha_limite_pago else "-", styles['td_center']),
            Paragraph(f"{al_dia:.2f}" if al_dia > 0 else "-", styles['td_right']),
            Paragraph(f"{d_1_30:.2f}" if d_1_30 > 0 else "-", styles['td_right']),
            Paragraph(f"{d_31_60:.2f}" if d_31_60 > 0 else "-", styles['td_right']),
            Paragraph(f"{d_61_90:.2f}" if d_61_90 > 0 else "-", styles['td_right']),
            Paragraph(f"<font color='#7A1C21'><b>{d_mas_90:.2f}</b></font>" if d_mas_90 > 0 else "-", styles['td_right']),
            Paragraph(f"<b>{saldo:.2f}</b>", styles['td_right']),
        ])

    tabla_data.append([
        Paragraph("<b>TOTALES CONSOLIDADOS (Q)</b>", styles['td_bold']),
        "", "",
        Paragraph(f"<b>Q {totales['al_dia']:.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {totales['dias_1_30']:.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {totales['dias_31_60']:.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {totales['dias_61_90']:.2f}</b>", styles['td_right']),
        Paragraph(f"<font color='#7A1C21'><b>Q {totales['mas_90']:.2f}</b></font>", styles['td_right']),
        Paragraph(f"<b>Q {totales['total']:.2f}</b>", styles['td_right']),
    ])

    col_widths = [180, 110, 65, 60, 60, 60, 60, 60, 65]
    t_morosidad = Table(tabla_data, colWidths=col_widths)
    t_morosidad.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('SPAN', (0,-1), (2,-1)),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_BG_LIGHT),
    ]))
    story.append(t_morosidad)
    story.append(Spacer(1, 20))

    story.append(ReportLabHelper.build_signature_block([
        "Director(a) Técnico Pedagógico",
        "Contador(a) General / Tesorería",
        "Auditor(a) Interno / Comisión de Finanzas"
    ], orientation_landscape=True))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Antiguedad_Saldos_{hoy.strftime("%Y%m%d")}.pdf"'
    return response


def generar_csv_antiguedad_saldos(ciclo_escolar=None):
    """Genera el reporte de antigüedad de saldos en formato CSV para Excel."""
    cuentas = CuentaPorCobrar.objects.filter(
        esta_eliminado=False,
        saldo_pendiente__gt=0
    ).select_related('estudiante', 'estudiante__persona', 'concepto', 'ciclo_escolar')

    if ciclo_escolar:
        cuentas = cuentas.filter(ciclo_escolar=ciclo_escolar)

    hoy = timezone.now().date()
    headers = ['Estudiante', 'CUI / DPI', 'Código MINEDUC', 'Concepto', 'Vencimiento', 'Días de Mora', 'Al Día (Q)', '1-30 Días (Q)', '31-60 Días (Q)', '61-90 Días (Q)', '+90 Días (Q)', 'Saldo Total (Q)']
    rows = []

    for c in cuentas:
        dias_mora = (hoy - c.fecha_limite_pago).days if c.fecha_limite_pago and hoy > c.fecha_limite_pago else 0
        saldo = c.saldo_pendiente

        rows.append([
            c.estudiante.persona.nombre_completo,
            c.estudiante.persona.cui,
            c.estudiante.codigo_mineduc,
            c.concepto.nombre,
            c.fecha_limite_pago.strftime('%d/%m/%Y') if c.fecha_limite_pago else "",
            dias_mora,
            f"{saldo:.2f}" if dias_mora <= 0 else "0.00",
            f"{saldo:.2f}" if 1 <= dias_mora <= 30 else "0.00",
            f"{saldo:.2f}" if 31 <= dias_mora <= 60 else "0.00",
            f"{saldo:.2f}" if 61 <= dias_mora <= 90 else "0.00",
            f"{saldo:.2f}" if dias_mora > 90 else "0.00",
            f"{saldo:.2f}",
        ])

    return IBACOOPReportCSV.generate_csv_response('Antiguedad_Saldos', headers, rows)


def generar_csv_cuadre_caja(fecha_inicio, fecha_fin):
    """Genera reporte de ingresos y recaudación de caja por fecha y medio de pago."""
    abonos = Abono.objects.filter(
        esta_eliminado=False,
        fecha_pago__gte=fecha_inicio,
        fecha_pago__lte=fecha_fin
    ).select_related('cuenta_cobrar', 'cuenta_cobrar__estudiante', 'cuenta_cobrar__estudiante__persona', 'cuenta_cobrar__concepto')

    headers = ['No. Recibo', 'Fecha de Pago', 'Estudiante', 'Concepto', 'Medio de Pago', 'Referencia / Depósito', 'Monto Pagado (Q)']
    rows = []

    for a in abonos:
        rows.append([
            a.numero_recibo or f"REC-{a.id}",
            a.fecha_pago.strftime('%d/%m/%Y') if a.fecha_pago else "",
            a.cuenta_cobrar.estudiante.persona.nombre_completo,
            a.cuenta_cobrar.concepto.nombre,
            a.get_metodo_pago_display() if hasattr(a, 'get_metodo_pago_display') else "Efectivo",
            a.referencia_bancaria or "N/A",
            f"{a.monto_pagado:.2f}"
        ])

    return IBACOOPReportCSV.generate_csv_response('Cuadre_Caja_Recaudacion', headers, rows)
