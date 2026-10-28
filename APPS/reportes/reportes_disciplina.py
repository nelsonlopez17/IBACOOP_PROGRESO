"""
reportes/reportes_disciplina.py

Generación de reportes de Disciplina y Convivencia Escolar para el Instituto Básico por Cooperativa El Progreso:
  1. Historial de Incidentes Disciplinarios y Convivencia Escolar (PDF y CSV/Excel)
  2. Registro de Citaciones a Padres de Familia o Encargados
"""
import io
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from APPS.reportes.generadores.base_pdf import (
    NumberedCanvas, ReportLabHelper, COLOR_VERDE, COLOR_ROJO, COLOR_AZUL, COLOR_TEXT, COLOR_MUTED, COLOR_BG_LIGHT, COLOR_BORDER
)
from APPS.reportes.generadores.base_csv import IBACOOPReportCSV
from APPS.disciplina.models import IncidenteDisciplinario, CitacionPadre


def generar_pdf_reporte_disciplina(ciclo_escolar, seccion=None):
    """
    Genera el informe ejecutivo en PDF de Incidentes Disciplinarios y Convivencia Escolar.
    Documento oficial para la Comisión de Disciplina según normativa MINEDUC.
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

    incidentes = IncidenteDisciplinario.objects.filter(
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related(
        'estudiante__persona',
        'reportado_por__persona'
    ).order_by('-fecha', '-hora')

    subtitulo = f"Ciclo Lectivo {ciclo_escolar.anio} • Normativa MINEDUC Acuerdo Ministerial 01-2011"
    if seccion:
        # Filtrar por seccion a traves de la asignacion del estudiante
        estudiantes_seccion = seccion.asignaciones.filter(ciclo_escolar=ciclo_escolar, esta_eliminado=False).values_list('estudiante_id', flat=True)
        incidentes = incidentes.filter(estudiante_id__in=estudiantes_seccion)
        subtitulo += f" • {seccion.grado.nombre} Sección '{seccion.letra}'"

    story.append(ReportLabHelper.build_header(
        doc_title="HISTORIAL DE INCIDENTES DISCIPLINARIOS Y CONVIVENCIA",
        subtitle=subtitulo,
        orientation_landscape=True
    ))
    story.append(Spacer(1, 10))

    tabla_data = [
        [
            Paragraph("<b>FECHA</b>", styles['th']),
            Paragraph("<b>ESTUDIANTE</b>", styles['th']),
            Paragraph("<b>TIPO DE FALTA</b>", styles['th']),
            Paragraph("<b>DESCRIPCIÓN DE LOS HECHOS</b>", styles['th']),
            Paragraph("<b>MEDIDA FORMATIVA</b>", styles['th']),
            Paragraph("<b>CITACIÓN</b>", styles['th']),
            Paragraph("<b>ESTADO</b>", styles['th']),
        ]
    ]

    for inc in incidentes:
        tipo_falta_str = inc.get_tipo_falta_display() if hasattr(inc, 'get_tipo_falta_display') else str(inc.tipo_falta)
        citacion_str = "REQUERIDA" if inc.requiere_citacion else "NO"
        estado_str = "<font color='#1E6532'>RESUELTO</font>" if inc.esta_resuelto else "<font color='#7A1C21'>EN PROCESO</font>"

        desc_txt = inc.descripcion_hechos or ''
        medida_txt = inc.medida_formativa or 'No asignada'
        tabla_data.append([
            Paragraph(inc.fecha.strftime('%d/%m/%Y') if inc.fecha else "-", styles['td_center']),
            Paragraph(f"<b>{inc.estudiante.persona.nombre_completo}</b>", styles['td']),
            Paragraph(tipo_falta_str, styles['td']),
            Paragraph(desc_txt[:80] + ('...' if len(desc_txt) > 80 else ''), styles['td']),
            Paragraph(medida_txt[:60] + ('...' if len(medida_txt) > 60 else ''), styles['td']),
            Paragraph(citacion_str, styles['td_center']),
            Paragraph(estado_str, styles['td_center']),
        ])

    if not incidentes.exists():
        tabla_data.append([
            Paragraph("No se registraron incidentes disciplinarios en el período seleccionado.", styles['td_center']),
            "", "", "", "", "", ""
        ])

    col_widths = [65, 170, 95, 180, 110, 60, 60]
    t_disc = Table(tabla_data, colWidths=col_widths, repeatRows=1)
    t_disc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    if not incidentes.exists():
        t_disc.setStyle(TableStyle([
            ('SPAN', (0,1), (-1,1)),
            ('BACKGROUND', (0,1), (-1,1), COLOR_BG_LIGHT),
        ]))

    story.append(t_disc)
    story.append(Spacer(1, 25))

    story.append(ReportLabHelper.build_signature_block([
        "Comisión de Disciplina y Convivencia",
        "Docente Guía",
        "Director(a) Técnico Pedagógico"
    ], orientation_landscape=True))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Reporte_Disciplina_{ciclo_escolar.anio}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generar_csv_reporte_disciplina(ciclo_escolar, seccion=None):
    """Genera la exportación CSV del historial de disciplina."""
    incidentes = IncidenteDisciplinario.objects.filter(
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('estudiante__persona', 'reportado_por__persona').order_by('-fecha')

    if seccion:
        estudiantes_seccion = seccion.asignaciones.filter(ciclo_escolar=ciclo_escolar, esta_eliminado=False).values_list('estudiante_id', flat=True)
        incidentes = incidentes.filter(estudiante_id__in=estudiantes_seccion)

    headers = [
        'Fecha', 'Hora', 'Estudiante', 'CUI / DPI', 'Código MINEDUC',
        'Tipo de Falta', 'Categoría', 'Descripción', 'Medida Formativa', 'Citación Requerida', 'Estado'
    ]
    rows = []

    for inc in incidentes:
        rows.append([
            inc.fecha.strftime('%d/%m/%Y') if inc.fecha else "",
            str(inc.hora) if inc.hora else "",
            inc.estudiante.persona.nombre_completo,
            inc.estudiante.persona.cui or "",
            inc.estudiante.codigo_mineduc or "",
            inc.get_tipo_falta_display() if hasattr(inc, 'get_tipo_falta_display') else str(inc.tipo_falta),
            inc.get_categoria_display() if hasattr(inc, 'get_categoria_display') else str(inc.categoria),
            inc.descripcion_hechos,
            inc.medida_formativa,
            "Sí" if inc.requiere_citacion else "No",
            "Resuelto" if inc.esta_resuelto else "En Proceso"
        ])

    filename = f"Reporte_Disciplina_{ciclo_escolar.anio}"
    return IBACOOPReportCSV.generate_csv_response(filename, headers, rows)
