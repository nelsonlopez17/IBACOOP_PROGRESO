"""
reportes/reportes_rrhh.py

Generación de reportes de Recursos Humanos, Planillas y Asistencia para el Instituto El Progreso:
  1. Consolidado Mensual y Anual de Planillas de Sueldos (PDF y CSV)
  2. Récord de Asistencia y Puntualidad del Personal
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
        sb = p.personal.salario_base
        bono = p.bonificaciones
        desc = p.descuentos
        liq = p.total_pagar

        total_base += sb
        total_bonos += bono
        total_descuentos += desc
        total_liquido += liq

        estado_str = "<font color='#1E6532'><b>PAGADO</b></font>" if p.pagado else "<font color='#7A1C21'><b>PENDIENTE</b></font>"

        tabla_data.append([
            Paragraph(f"<b>{p.personal.persona.nombre_completo}</b><br/><font size=6 color='#64748B'>CUI: {p.personal.persona.cui}</font>", styles['td']),
            Paragraph(p.personal.puesto.nombre_puesto if p.personal.puesto else "General", styles['td']),
            Paragraph(f"{sb:.2f}", styles['td_right']),
            Paragraph(f"{bono:.2f}", styles['td_right']),
            Paragraph(f"{desc:.2f}", styles['td_right']),
            Paragraph(f"<b>{liq:.2f}</b>", styles['td_right']),
            Paragraph(estado_str, styles['td_center']),
        ])

    tabla_data.append([
        Paragraph("<b>TOTALES CONSOLIDADOS (Q)</b>", styles['td_bold']),
        "",
        Paragraph(f"<b>Q {total_base:.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {total_bonos:.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {total_descuentos:.2f}</b>", styles['td_right']),
        Paragraph(f"<b>Q {total_liquido:.2f}</b>", styles['td_right']),
        Paragraph(f"<b>{planillas.count()} Boletas</b>", styles['td_center'])
    ])

    col_widths = [220, 130, 85, 75, 75, 85, 50]
    t_planilla = Table(tabla_data, colWidths=col_widths)
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
        "Director(a) Técnico Pedagógico",
        "Contador(a) / Recursos Humanos",
        "Presidente(a) Consejo de Administración"
    ], orientation_landscape=True))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Planilla_Consolidada_{mes}_{ciclo_escolar.anio}.pdf"'
    return response


def generar_csv_consolidado_planillas(ciclo_escolar, mes):
    """Genera exportación CSV de la planilla mensual."""
    planillas = Planilla.objects.filter(
        ciclo_escolar=ciclo_escolar,
        mes_pagado=mes,
        esta_eliminado=False
    ).select_related('personal', 'personal__persona', 'personal__puesto').order_by('personal__persona__apellidos')

    headers = ['Colaborador', 'CUI / DPI', 'Puesto / Cargo', 'Salario Base (Q)', 'Bonificaciones (Q)', 'Deducciones (Q)', 'Total Líquido (Q)', 'Estado de Pago']
    rows = []

    for p in planillas:
        rows.append([
            p.personal.persona.nombre_completo,
            p.personal.persona.cui,
            p.personal.puesto.nombre_puesto if p.personal.puesto else "General",
            f"{p.personal.salario_base:.2f}",
            f"{p.bonificaciones:.2f}",
            f"{p.descuentos:.2f}",
            f"{p.total_pagar:.2f}",
            "PAGADO" if p.pagado else "PENDIENTE"
        ])

    return IBACOOPReportCSV.generate_csv_response(f'Planilla_{mes}_{ciclo_escolar.anio}', headers, rows)
