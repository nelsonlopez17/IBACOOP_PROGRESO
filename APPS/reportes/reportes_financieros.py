"""
reportes/reportes_financieros.py

Generación de reportes financieros y de tesorería para el Instituto Básico por Cooperativa El Progreso:
  1. Antigüedad de Saldos y Morosidad (PDF y CSV/Excel)
  2. Arqueo y Cuadre Diario de Caja (PDF y CSV/Excel)
  3. Estado de Cuenta y Solvencia por Estudiante (PDF y CSV/Excel)
  4. Padrón de Becas y Descuentos Otorgados (CSV/Excel)
"""
import io
from collections import defaultdict
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
        Paragraph("<b>TOTALES GENERALES EN MORA (Q)</b>", styles['td_bold']),
        "", "",
        Paragraph(f"<b>Q {totales['al_dia']:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {totales['dias_1_30']:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {totales['dias_31_60']:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {totales['dias_61_90']:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {totales['mas_90']:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {totales['total']:,.2f}</b>", styles['td_right']),
    ])

    col_widths = [190, 110, 65, 55, 55, 55, 55, 55, 80]
    t_ant = Table(tabla_data, colWidths=col_widths, repeatRows=1)
    t_ant.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('SPAN', (0,-1), (2,-1)),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_BG_LIGHT),
    ]))
    story.append(t_ant)
    story.append(Spacer(1, 25))

    story.append(ReportLabHelper.build_signature_block([
        "Encargado(a) de Cartera y Cobros",
        "Contador(a) General",
        "Director(a) Técnico Pedagógico"
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
            c.estudiante.codigo_mineduc or 'PENDIENTE',
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


def generar_pdf_cuadre_caja(fecha_inicio, fecha_fin):
    """
    Genera el Reporte Oficial de Arqueo y Cuadre de Caja en PDF.
    Consolida todos los cobros efectuados entre las fechas indicadas, con desglose y firmas.
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
    styles = ReportLabHelper.get_styles()

    abonos = Abono.objects.filter(
        esta_eliminado=False,
        fecha_pago__gte=fecha_inicio,
        fecha_pago__lte=fecha_fin
    ).select_related(
        'cuenta_por_cobrar__estudiante__persona',
        'cuenta_por_cobrar__concepto'
    ).order_by('fecha_pago', 'id')

    subtitulo = f"Período del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"
    if fecha_inicio == fecha_fin:
        subtitulo = f"Corte Diario del {fecha_inicio.strftime('%d/%m/%Y')}"

    story.append(ReportLabHelper.build_header(
        doc_title="ARQUEO Y CUADRE DIARIO DE CAJA",
        subtitle=f"{subtitulo} • Moneda: Quetzales (Q)"
    ))
    story.append(Spacer(1, 10))

    tabla_data = [
        [
            Paragraph("<b>RECIBO</b>", styles['th']),
            Paragraph("<b>FECHA</b>", styles['th']),
            Paragraph("<b>ESTUDIANTE</b>", styles['th']),
            Paragraph("<b>CONCEPTO DE COBRO</b>", styles['th']),
            Paragraph("<b>MÉTODO PAGO</b>", styles['th']),
            Paragraph("<b>MONTO (Q)</b>", styles['th']),
        ]
    ]

    total_recaudado = Decimal(0)
    totales_por_metodo = defaultdict(Decimal)

    for a in abonos:
        monto = a.monto_pagado
        total_recaudado += monto
        metodo = a.get_metodo_pago_display() if hasattr(a, 'get_metodo_pago_display') else "Efectivo"
        totales_por_metodo[metodo] += monto

        no_recibo = getattr(a, 'numero_recibo', None) or a.numero_boleta or f"REC-{a.id}"
        est_nombre = a.cuenta_por_cobrar.estudiante.persona.nombre_completo if a.cuenta_por_cobrar and a.cuenta_por_cobrar.estudiante else "General"
        concepto_nombre = a.cuenta_por_cobrar.concepto.nombre if a.cuenta_por_cobrar and a.cuenta_por_cobrar.concepto else "Cuota"

        tabla_data.append([
            Paragraph(f"<b>{no_recibo}</b>", styles['td']),
            Paragraph(a.fecha_pago.strftime('%d/%m/%Y') if a.fecha_pago else "-", styles['td_center']),
            Paragraph(est_nombre, styles['td']),
            Paragraph(concepto_nombre, styles['td']),
            Paragraph(metodo, styles['td_center']),
            Paragraph(f"<b>{monto:,.2f}</b>", styles['td_right']),
        ])

    tabla_data.append([
        Paragraph("<b>TOTAL RECAUDADO EN EL PERÍODO (Q)</b>", styles['td_bold']),
        "", "", "", "",
        Paragraph(f"<b>Q {total_recaudado:,.2f}</b>", styles['td_right']),
    ])

    col_widths = [75, 60, 165, 115, 65, 60]
    t_cuadre = Table(tabla_data, colWidths=col_widths, repeatRows=1)
    t_cuadre.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('SPAN', (0,-1), (4,-1)),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_BG_LIGHT),
    ]))
    story.append(t_cuadre)
    story.append(Spacer(1, 15))

    # Resumen por método de pago
    resumen_data = [
        [Paragraph("<b>FORMA DE PAGO</b>", styles['th']), Paragraph("<b>TOTAL INGRESADO (Q)</b>", styles['th'])]
    ]
    for met, total_met in totales_por_metodo.items():
        resumen_data.append([
            Paragraph(met, styles['td']),
            Paragraph(f"Q {total_met:,.2f}", styles['td_right'])
        ])

    t_resumen = Table(resumen_data, colWidths=[200, 120])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_AZUL),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 30))

    story.append(ReportLabHelper.build_signature_block([
        "Cajero(a) Receptor(a)",
        "Contador(a) General"
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Cuadre_Caja_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generar_csv_cuadre_caja(fecha_inicio, fecha_fin):
    """Genera reporte de ingresos y recaudación de caja por fecha y medio de pago."""
    abonos = Abono.objects.filter(
        esta_eliminado=False,
        fecha_pago__gte=fecha_inicio,
        fecha_pago__lte=fecha_fin
    ).select_related('cuenta_por_cobrar', 'cuenta_por_cobrar__estudiante', 'cuenta_por_cobrar__estudiante__persona', 'cuenta_por_cobrar__concepto')

    headers = ['No. Recibo', 'Fecha de Pago', 'Estudiante', 'Concepto', 'Medio de Pago', 'Referencia / Depósito', 'Monto Pagado (Q)']
    rows = []

    for a in abonos:
        rows.append([
            getattr(a, 'numero_recibo', None) or a.numero_boleta or f"REC-{a.id}",
            a.fecha_pago.strftime('%d/%m/%Y') if a.fecha_pago else "",
            a.cuenta_por_cobrar.estudiante.persona.nombre_completo if a.cuenta_por_cobrar and a.cuenta_por_cobrar.estudiante else "General",
            a.cuenta_por_cobrar.concepto.nombre if a.cuenta_por_cobrar and a.cuenta_por_cobrar.concepto else "Cuota",
            a.get_metodo_pago_display() if hasattr(a, 'get_metodo_pago_display') else "Efectivo",
            getattr(a, 'referencia_bancaria', None) or a.numero_boleta or "N/A",
            f"{a.monto_pagado:.2f}"
        ])

    return IBACOOPReportCSV.generate_csv_response('Cuadre_Caja_Recaudacion', headers, rows)


def generar_pdf_estado_cuenta_estudiante(estudiante, ciclo_escolar):
    """
    Genera el Estado de Cuenta y Registro de Pagos por Estudiante en PDF.
    Detalla todas las cuotas asignadas, los abonos y el estado de solvencia institucional.
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
    styles = ReportLabHelper.get_styles()

    cuentas = CuentaPorCobrar.objects.filter(
        estudiante=estudiante,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('concepto').order_by('fecha_limite_pago', 'id')

    p = estudiante.persona
    total_cobrado = sum(c.monto_total for c in cuentas)
    total_pendiente = sum(c.saldo_pendiente for c in cuentas)
    total_pagado = total_cobrado - total_pendiente
    es_solvente = (total_pendiente == 0)

    story.append(ReportLabHelper.build_header(
        doc_title="ESTADO DE CUENTA Y REGISTRO DE PAGOS",
        subtitle=f"Ciclo Lectivo {ciclo_escolar.anio} • Moneda: Quetzales (Q)"
    ))
    story.append(Spacer(1, 10))

    # Cuadro datos del estudiante
    datos_est = [
        [
            Paragraph(f"<b>ESTUDIANTE:</b> {p.nombre_completo.upper()}", styles['td']),
            Paragraph(f"<b>CÓDIGO MINEDUC:</b> {estudiante.codigo_mineduc or 'PENDIENTE'}", styles['td']),
        ],
        [
            Paragraph(f"<b>CUI / DPI:</b> {p.cui or 'Sin registro'}", styles['td']),
            Paragraph(f"<b>ESTADO DE SOLVENCIA:</b> {'<font color=\"#1E6532\"><b>SOLVENTE</b></font>' if es_solvente else '<font color=\"#7A1C21\"><b>CON SALDO PENDIENTE</b></font>'}", styles['td']),
        ]
    ]
    t_est = Table(datos_est, colWidths=[340, 200])
    t_est.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_est)
    story.append(Spacer(1, 12))

    tabla_data = [
        [
            Paragraph("<b>CONCEPTO / CUOTA ESCOLAR</b>", styles['th']),
            Paragraph("<b>VENCIMIENTO</b>", styles['th']),
            Paragraph("<b>MONTO (Q)</b>", styles['th']),
            Paragraph("<b>PAGADO (Q)</b>", styles['th']),
            Paragraph("<b>SALDO (Q)</b>", styles['th']),
            Paragraph("<b>ESTADO</b>", styles['th']),
        ]
    ]

    for c in cuentas:
        pagado_cuota = c.monto_total - c.saldo_pendiente
        color_est = "#1E6532" if c.saldo_pendiente == 0 else "#7A1C21"

        tabla_data.append([
            Paragraph(f"<b>{c.concepto.nombre}</b>", styles['td']),
            Paragraph(c.fecha_limite_pago.strftime('%d/%m/%Y') if c.fecha_limite_pago else "-", styles['td_center']),
            Paragraph(f"{c.monto_total:.2f}", styles['td_right']),
            Paragraph(f"{pagado_cuota:.2f}", styles['td_right']),
            Paragraph(f"<font color='{color_est}'><b>{c.saldo_pendiente:.2f}</b></font>", styles['td_right']),
            Paragraph(f"<font color='{color_est}'><b>{c.get_estado_pago_display()}</b></font>", styles['td_center']),
        ])

    tabla_data.append([
        Paragraph("<b>TOTALES ACUMULADOS (Q)</b>", styles['td_bold']),
        "",
        Paragraph(f"<b>Q {total_cobrado:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {total_pagado:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {total_pendiente:,.2f}</b>", styles['td_right']),
        Paragraph("<b>SOLVENTE</b>" if es_solvente else "<b>PENDIENTE</b>", styles['td_center']),
    ])

    col_widths = [200, 70, 65, 65, 70, 70]
    t_cuentas = Table(tabla_data, colWidths=col_widths)
    t_cuentas.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('SPAN', (0,-1), (1,-1)),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_BG_LIGHT),
    ]))
    story.append(t_cuentas)
    story.append(Spacer(1, 35))

    story.append(ReportLabHelper.build_signature_block([
        "Encargado(a) de Caja y Cobros",
        "Contador(a) General"
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Estado_Cuenta_{p.apellidos}_{p.nombres}_{ciclo_escolar.anio}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
