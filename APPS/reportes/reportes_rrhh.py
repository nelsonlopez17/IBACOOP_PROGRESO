"""
reportes/reportes_rrhh.py

Generación de reportes de Recursos Humanos, Planilla de Sueldos y Personal para el Instituto Básico por Cooperativa El Progreso:
  1. Consolidado Mensual de Planilla de Sueldos (PDF y CSV/Excel)
  2. Boleta Oficial de Pago por Colaborador (PDF)
  3. Directorio y Listado Oficial de Personal Institucional (PDF y CSV/Excel)
"""
import io
from decimal import Decimal
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from APPS.reportes.generadores.base_pdf import (
    NumberedCanvas, ReportLabHelper, COLOR_VERDE, COLOR_ROJO, COLOR_AZUL, COLOR_TEXT, COLOR_MUTED, COLOR_BG_LIGHT, COLOR_BORDER
)
from APPS.reportes.generadores.base_csv import IBACOOPReportCSV
from APPS.rrhh.models import Planilla, Personal


def generar_pdf_consolidado_planillas(ciclo_escolar, mes):
    """
    Genera el informe ejecutivo en PDF de la Planilla Mensual del Instituto.
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

    planillas = Planilla.objects.filter(
        ciclo_escolar=ciclo_escolar,
        mes_pagado=mes,
        esta_eliminado=False
    ).select_related('personal', 'personal__persona', 'personal__puesto').order_by('personal__persona__apellidos')

    mes_nombre = planillas.first().get_mes_pagado_display() if planillas.exists() else f"Mes {mes}"

    story.append(ReportLabHelper.build_header(
        doc_title=f"CONSOLIDADO DE PLANILLA GENERAL — {mes_nombre.upper()} {ciclo_escolar.anio}",
        subtitle="Decreto 37-2001 (Bonificación Incentivo) y Cuota Laboral IGSS (4.83%)",
        orientation_landscape=True
    ))
    story.append(Spacer(1, 10))

    tabla_data = [
        [
            Paragraph("<b>COLABORADOR / EMPLEADO</b>", styles['th']),
            Paragraph("<b>PUESTO / CARGO</b>", styles['th']),
            Paragraph("<b>SALARIO BASE (Q)</b>", styles['th']),
            Paragraph("<b>BONIF. LEY (Q)</b>", styles['th']),
            Paragraph("<b>DEDUCCIONES (Q)</b>", styles['th']),
            Paragraph("<b>LÍQUIDO A PAGAR (Q)</b>", styles['th']),
            Paragraph("<b>ESTADO</b>", styles['th']),
        ]
    ]

    total_base = Decimal(0)
    total_bonos = Decimal(0)
    total_descuentos = Decimal(0)
    total_liquido = Decimal(0)

    for p in planillas:
        sb = p.salario_base or getattr(p.personal, 'salario_base_asignado', Decimal('0.00')) or Decimal('0.00')
        bono = p.bonificacion_incentivo + p.bonificaciones
        desc = p.total_descuentos
        liq = p.total_pagar

        total_base += sb
        total_bonos += bono
        total_descuentos += desc
        total_liquido += liq

        estado_str = "<font color='#1E6532'><b>PAGADO</b></font>" if p.pagado else "<font color='#7A1C21'><b>PENDIENTE</b></font>"

        tabla_data.append([
            Paragraph(f"<b>{p.personal.persona.nombre_completo}</b><br/><font size=6 color='#64748B'>CUI: {p.personal.persona.cui}</font>", styles['td']),
            Paragraph(p.personal.puesto.nombre_puesto if p.personal.puesto else "General", styles['td']),
            Paragraph(f"{sb:,.2f}", styles['td_right']),
            Paragraph(f"{bono:,.2f}", styles['td_right']),
            Paragraph(f"{desc:,.2f}", styles['td_right']),
            Paragraph(f"<b>{liq:,.2f}</b>", styles['td_right']),
            Paragraph(estado_str, styles['td_center']),
        ])

    tabla_data.append([
        Paragraph("<b>TOTALES CONSOLIDADOS (Q)</b>", styles['td_bold']),
        "",
        Paragraph(f"<b>Q {total_base:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {total_bonos:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {total_descuentos:,.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {total_liquido:,.2f}</b>", styles['td_right']),
        "",
    ])

    col_widths = [220, 140, 80, 80, 80, 80, 60]
    t_planilla = Table(tabla_data, colWidths=col_widths, repeatRows=1)
    t_planilla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('SPAN', (0,-1), (1,-1)),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_BG_LIGHT),
    ]))
    story.append(t_planilla)
    story.append(Spacer(1, 25))

    story.append(ReportLabHelper.build_signature_block([
        "Elaborado por (Recursos Humanos)",
        "Revisado por (Contabilidad)",
        "Autorizado por (Dirección)"
    ], orientation_landscape=True))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Planilla_{ciclo_escolar.anio}_{mes:02d}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generar_csv_consolidado_planillas(ciclo_escolar, mes):
    """Genera la exportación CSV para contabilidad de la Planilla Mensual."""
    planillas = Planilla.objects.filter(
        ciclo_escolar=ciclo_escolar,
        mes_pagado=mes,
        esta_eliminado=False
    ).select_related('personal', 'personal__persona', 'personal__puesto').order_by('personal__persona__apellidos')

    headers = [
        'Empleado', 'CUI / DPI', 'Puesto', 'Salario Base (Q)', 'Días Laborados',
        'Salario Ordinario (Q)', 'Bonificación Incentivo (Q)', 'Otras Bonificaciones (Q)',
        'Descuento IGSS 4.83% (Q)', 'Retención ISR (Q)', 'Otros Descuentos (Q)',
        'Líquido a Pagar (Q)', 'Cuota Patronal IGSS 10.67% (Q)', 'Estado'
    ]
    rows = []

    for p in planillas:
        rows.append([
            p.personal.persona.nombre_completo,
            p.personal.persona.cui,
            p.personal.puesto.nombre_puesto if p.personal.puesto else "General",
            f"{p.salario_base:.2f}",
            p.dias_laborados,
            f"{p.salario_ordinario:.2f}",
            f"{p.bonificacion_incentivo:.2f}",
            f"{p.bonificaciones:.2f}",
            f"{p.descuento_igss:.2f}",
            f"{p.retencion_isr:.2f}",
            f"{p.descuentos:.2f}",
            f"{p.total_pagar:.2f}",
            f"{p.cuota_patronal_igss:.2f}",
            "PAGADO" if p.pagado else "PENDIENTE"
        ])

    filename = f"Planilla_Consolidada_{ciclo_escolar.anio}_Mes_{mes:02d}"
    return IBACOOPReportCSV.generate_csv_response(filename, headers, rows)


def generar_pdf_boleta_pago_individual(planilla):
    """
    Genera la Boleta Oficial de Pago individual de salario por colaborador en PDF.
    Cumple con el Decreto 37-2001, desglose de IGSS y espacio para firma de recibido del empleado.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    story = []
    styles = ReportLabHelper.get_styles()

    p = planilla.personal.persona
    puesto_str = planilla.personal.puesto.nombre_puesto if planilla.personal.puesto else "Personal"
    mes_str = planilla.get_mes_pagado_display()

    story.append(ReportLabHelper.build_header(
        doc_title="BOLETA OFICIAL DE PAGO DE SUELDOS",
        subtitle=f"Período de Liquidación: {mes_str.upper()} {planilla.ciclo_escolar.anio}"
    ))
    story.append(Spacer(1, 15))

    # Datos del Empleado
    datos_emp = [
        [
            Paragraph(f"<b>COLABORADOR:</b> {p.nombre_completo.upper()}", styles['td']),
            Paragraph(f"<b>CUI / DPI:</b> {p.cui or 'N/A'}", styles['td']),
        ],
        [
            Paragraph(f"<b>PUESTO INSTITUCIONAL:</b> {puesto_str}", styles['td']),
            Paragraph(f"<b>FECHA DE PAGO:</b> {planilla.fecha_pago.strftime('%d/%m/%Y') if planilla.fecha_pago else 'PENDIENTE'}", styles['td']),
        ]
    ]
    t_emp = Table(datos_emp, colWidths=[320, 200])
    t_emp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_emp)
    story.append(Spacer(1, 15))

    # Detalle de Devengados y Descuentos
    tabla_rubros = [
        [
            Paragraph("<b>INGRESOS Y DEVENGADOS</b>", styles['th']),
            Paragraph("<b>MONTO (Q)</b>", styles['th']),
            Paragraph("<b>DEDUCCIONES Y DESCUENTOS</b>", styles['th']),
            Paragraph("<b>MONTO (Q)</b>", styles['th']),
        ],
        [
            Paragraph("Salario Ordinario Base", styles['td']),
            Paragraph(f"Q {planilla.salario_ordinario:,.2f}", styles['td_right']),
            Paragraph("Cuota Laboral IGSS (4.83%)", styles['td']),
            Paragraph(f"Q {planilla.descuento_igss:,.2f}", styles['td_right']),
        ],
        [
            Paragraph("Bonificación Incentivo (Dto. 37-2001)", styles['td']),
            Paragraph(f"Q {planilla.bonificacion_incentivo:,.2f}", styles['td_right']),
            Paragraph("Retención ISR Laboral", styles['td']),
            Paragraph(f"Q {planilla.retencion_isr:,.2f}", styles['td_right']),
        ],
        [
            Paragraph("Otras Bonificaciones / Ajustes", styles['td']),
            Paragraph(f"Q {planilla.bonificaciones:,.2f}", styles['td_right']),
            Paragraph("Otros Descuentos / Anticipos", styles['td']),
            Paragraph(f"Q {(planilla.descuento_anticipo + planilla.descuento_judicial + planilla.descuento_otros):,.2f}", styles['td_right']),
        ],
        [
            Paragraph("<b>TOTAL DEVENGADO</b>", styles['td_bold']),
            Paragraph(f"<b>Q {planilla.total_ingresos:,.2f}</b>", styles['td_right']),
            Paragraph("<b>TOTAL DESCUENTOS</b>", styles['td_bold']),
            Paragraph(f"<b>Q {planilla.total_descuentos:,.2f}</b>", styles['td_right']),
        ],
    ]

    t_rubros = Table(tabla_rubros, colWidths=[180, 80, 180, 80])
    t_rubros.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), COLOR_VERDE),
        ('BACKGROUND', (2,0), (3,0), COLOR_ROJO),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('PADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_BG_LIGHT),
    ]))
    story.append(t_rubros)
    story.append(Spacer(1, 15))

    # Líquido a percibir
    liquido_data = [
        [
            Paragraph("<font size=10><b>LÍQUIDO A PERCIBIR EN PLANILLA:</b></font>", styles['td']),
            Paragraph(f"<font size=12 color='#1E6532'><b>Q {planilla.total_pagar:,.2f}</b></font>", styles['td_right']),
        ]
    ]
    t_liq = Table(liquido_data, colWidths=[360, 160])
    t_liq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, COLOR_VERDE),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_liq)
    story.append(Spacer(1, 40))

    story.append(ReportLabHelper.build_signature_block([
        "Firma del Empleado (Recibí Conforme)",
        "Contador(a) / Pagador(a) Autorizado"
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Boleta_Pago_{p.apellidos}_{p.nombres}_{planilla.ciclo_escolar.anio}_{planilla.mes_pagado:02d}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generar_pdf_directorio_personal():
    """Genera el Directorio y Nómina Oficial de Personal Docente y Administrativo en PDF."""
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

    personal_qs = Personal.objects.filter(esta_eliminado=False).select_related('persona', 'puesto').order_by('persona__apellidos', 'persona__nombres')

    story.append(ReportLabHelper.build_header(
        doc_title="DIRECTORIO INSTITUCIONAL DE PERSONAL",
        subtitle="Registro Oficial de Catedráticos, Personal Docente y Administrativo",
        orientation_landscape=True
    ))
    story.append(Spacer(1, 10))

    tabla_data = [
        [
            Paragraph("<b>No.</b>", styles['th']),
            Paragraph("<b>APELLIDOS Y NOMBRES</b>", styles['th']),
            Paragraph("<b>PUESTO / CARGO</b>", styles['th']),
            Paragraph("<b>CUI / DPI</b>", styles['th']),
            Paragraph("<b>TELÉFONO</b>", styles['th']),
            Paragraph("<b>CORREO ELECTRÓNICO</b>", styles['th']),
            Paragraph("<b>ESTADO</b>", styles['th']),
        ]
    ]

    for idx, per in enumerate(personal_qs, start=1):
        p = per.persona
        puesto_str = per.puesto.nombre_puesto if per.puesto else "General"
        es_activo = (per.estado_laboral == 'ACTIVO')
        estado_label = per.get_estado_laboral_display() if hasattr(per, 'get_estado_laboral_display') else per.estado_laboral
        estado_str = f"<font color='#1E6532'>{estado_label}</font>" if es_activo else f"<font color='#7A1C21'>{estado_label}</font>"

        tabla_data.append([
            Paragraph(str(idx), styles['td_center']),
            Paragraph(f"<b>{p.apellidos},</b> {p.nombres}", styles['td']),
            Paragraph(puesto_str, styles['td']),
            Paragraph(p.cui or 'N/A', styles['td_center']),
            Paragraph(p.telefono_principal or 'N/A', styles['td_center']),
            Paragraph(p.correo or 'Sin correo', styles['td']),
            Paragraph(estado_str, styles['td_center']),
        ])

    col_widths = [26, 180, 140, 80, 75, 155, 64]
    t_dir = Table(tabla_data, colWidths=col_widths, repeatRows=1)
    t_dir.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_dir)
    story.append(Spacer(1, 25))

    story.append(ReportLabHelper.build_signature_block([
        "Recursos Humanos",
        "Director(a) Técnico Pedagógico"
    ], orientation_landscape=True))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Directorio_Personal_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response


def generar_csv_directorio_personal():
    """Genera exportación CSV del Directorio Institucional de Personal."""
    personal_qs = Personal.objects.filter(esta_eliminado=False).select_related('persona', 'puesto').order_by('persona__apellidos')

    headers = ['No.', 'Apellidos', 'Nombres', 'Puesto Institucional', 'CUI / DPI', 'Teléfono', 'Correo', 'Estado']
    rows = []

    for idx, per in enumerate(personal_qs, start=1):
        p = per.persona
        estado_label = per.get_estado_laboral_display() if hasattr(per, 'get_estado_laboral_display') else per.estado_laboral
        rows.append([
            idx,
            p.apellidos,
            p.nombres,
            per.puesto.nombre_puesto if per.puesto else "General",
            p.cui or 'N/A',
            p.telefono_principal or 'N/A',
            p.correo or '',
            estado_label
        ])

    return IBACOOPReportCSV.generate_csv_response('Directorio_Personal', headers, rows)
