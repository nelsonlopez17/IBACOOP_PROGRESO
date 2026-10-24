"""
reportes/reportes_academicos.py

Generación de reportes académicos oficiales para el Instituto El Progreso:
  1. Boleta de Calificaciones Bimestral / Final oficial (PDF)
  2. Cuadro de Honor y Rendimiento Escolar (PDF y CSV)
  3. Sábana Consolidada de Calificaciones — Cuadro MED MINEDUC (PDF y CSV)
  4. Reporte de Alertas Tempranas y Recuperaciones (CSV)
"""
import io
from decimal import Decimal
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from APPS.reportes.generadores.base_pdf import (
    NumberedCanvas, ReportLabHelper, COLOR_VERDE, COLOR_ROJO, COLOR_AZUL, COLOR_TEXT, COLOR_MUTED, COLOR_BG_LIGHT, COLOR_BORDER
)
from APPS.reportes.generadores.base_csv import IBACOOPReportCSV
from APPS.academico.models import NotaBloque, Curso, AsignacionEstudiante, BloqueAcademico


def generar_pdf_boleta_calificaciones(estudiante, ciclo_escolar):
    """
    Genera la Boleta Oficial de Calificaciones del estudiante con las notas
    por bloque (1 a 4), promedio final y firmas de Dirección y Docente Guía.
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

    asignacion = AsignacionEstudiante.objects.filter(
        estudiante=estudiante,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('seccion', 'seccion__grado').first()

    seccion_nombre = f"{asignacion.seccion.grado.nombre} Sección '{asignacion.seccion.letra}'" if asignacion else "Sin Sección Asignada"

    story.append(ReportLabHelper.build_header(
        doc_title="BOLETA OFICIAL DE CALIFICACIONES",
        subtitle=f"Ciclo Lectivo {ciclo_escolar.anio} • Nivel Medio - Ciclo Básico"
    ))
    story.append(Spacer(1, 10))

    datos_estudiante = [
        [
            Paragraph(f"<b>ESTUDIANTE:</b> {estudiante.persona.nombre_completo.upper()}", styles['td']),
            Paragraph(f"<b>CÓDIGO PERSONAL MINEDUC:</b> {estudiante.codigo_mineduc}", styles['td']),
        ],
        [
            Paragraph(f"<b>GRADO Y SECCIÓN:</b> {seccion_nombre}", styles['td']),
            Paragraph(f"<b>CUI / DPI:</b> {estudiante.persona.cui}", styles['td']),
        ]
    ]
    t_estudiante = Table(datos_estudiante, colWidths=[340, 200])
    t_estudiante.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_estudiante)
    story.append(Spacer(1, 12))

    cursos = Curso.objects.filter(grado=asignacion.seccion.grado, esta_eliminado=False).order_by('nombre_curso') if asignacion else []
    bloques = BloqueAcademico.objects.filter(ciclo_escolar=ciclo_escolar, esta_eliminado=False).order_by('orden')[:4]

    tabla_data = [
        [
            Paragraph("<b>ÁREA / CURRÍCULO NACIONAL BASE</b>", styles['th']),
            Paragraph("<b>B1</b>", styles['th']),
            Paragraph("<b>B2</b>", styles['th']),
            Paragraph("<b>B3</b>", styles['th']),
            Paragraph("<b>B4</b>", styles['th']),
            Paragraph("<b>PROMEDIO</b>", styles['th']),
            Paragraph("<b>RESULTADO</b>", styles['th']),
        ]
    ]

    total_promedios = Decimal(0)
    cursos_evaluados = 0

    for curso in cursos:
        fila = [Paragraph(f"<b>{curso.nombre_curso}</b>", styles['td'])]
        suma_curso = Decimal(0)
        bloques_contados = 0

        for b in bloques:
            nota = NotaBloque.objects.filter(
                asignacion_estudiante=asignacion,
                curso=curso,
                bloque_academico=b,
                esta_eliminado=False
            ).first()

            if nota:
                pts = nota.nota_total
                suma_curso += pts
                bloques_contados += 1
                color_pts = "#7A1C21" if pts < 60 else "#0F172A"
                fila.append(Paragraph(f"<font color='{color_pts}'>{pts:.0f}</font>", styles['td_center']))
            else:
                fila.append(Paragraph("-", styles['td_center']))

        promedio_curso = (suma_curso / bloques_contados) if bloques_contados > 0 else Decimal(0)
        if bloques_contados > 0:
            total_promedios += promedio_curso
            cursos_evaluados += 1

        color_prom = "#7A1C21" if promedio_curso < 60 else "#1E6532"
        estado_curso = "<font color='#1E6532'><b>APROBADO</b></font>" if promedio_curso >= 60 else "<font color='#7A1C21'><b>REPROBADO</b></font>"

        fila.append(Paragraph(f"<font color='{color_prom}'><b>{promedio_curso:.1f}</b></font>", styles['td_center']))
        fila.append(Paragraph(estado_curso if bloques_contados > 0 else "EN CURSO", styles['td_center']))
        tabla_data.append(fila)

    promedio_general = (total_promedios / cursos_evaluados) if cursos_evaluados > 0 else Decimal(0)

    tabla_data.append([
        Paragraph("<b>PROMEDIO GENERAL ACUMULADO</b>", styles['td_bold']),
        "", "", "", "",
        Paragraph(f"<b>{promedio_general:.1f}</b>", styles['td_center']),
        Paragraph("<b>PROMOVIDO</b>" if promedio_general >= 60 else "<b>EN RIESGO</b>", styles['td_center'])
    ])

    col_widths = [240, 45, 45, 45, 45, 60, 60]
    t_notas = Table(tabla_data, colWidths=col_widths)
    t_notas.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('SPAN', (0,-1), (4,-1)),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_BG_LIGHT),
    ]))
    story.append(t_notas)
    story.append(Spacer(1, 15))

    escala_text = (
        "<b>Escala Oficial MINEDUC:</b> 90-100: Excelente • 75-89: Muy Bueno • "
        "60-74: Satisfactorio (Aprobado) • 0-59: Debe Mejorar (Reprobado, requiere Plan de Recuperación)."
    )
    story.append(Paragraph(escala_text, styles['notes']))
    story.append(Spacer(1, 30))

    story.append(ReportLabHelper.build_signature_block([
        "Director(a) Técnico Pedagógico",
        "Docente Guía de Sección",
        "Firma de Padre o Encargado"
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Boleta_{estudiante.persona.apellidos}_{estudiante.persona.nombres}_{ciclo_escolar.anio}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generar_csv_cuadro_honor(seccion, ciclo_escolar):
    """Genera exportación CSV del Cuadro de Honor / Ranking de la sección."""
    asignaciones = AsignacionEstudiante.objects.filter(
        seccion=seccion,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('estudiante', 'estudiante__persona')

    ranking = []
    for a in asignaciones:
        notas = NotaBloque.objects.filter(asignacion_estudiante=a, esta_eliminado=False)
        prom = sum(n.nota_total for n in notas) / len(notas) if notas.exists() else Decimal(0)
        ranking.append({
            'estudiante': a.estudiante.persona.nombre_completo,
            'cui': a.estudiante.persona.cui,
            'codigo_mineduc': a.estudiante.codigo_mineduc,
            'promedio': round(prom, 2),
            'cursos_evaluados': notas.count(),
        })

    ranking.sort(key=lambda x: x['promedio'], reverse=True)

    headers = ['Posición', 'Estudiante', 'Código MINEDUC', 'CUI / DPI', 'Promedio General (Pts)', 'Cursos Evaluados']
    rows = []
    for idx, r in enumerate(ranking, start=1):
        rows.append([idx, r['estudiante'], r['codigo_mineduc'], r['cui'], f"{r['promedio']:.2f}", r['cursos_evaluados']])

    filename = f"Cuadro_Honor_{seccion.grado.nombre}_{seccion.letra}_{ciclo_escolar.anio}".replace(' ', '_')
    return IBACOOPReportCSV.generate_csv_response(filename, headers, rows)


def generar_csv_sabana_notas(seccion, ciclo_escolar):
    """Genera sábana consolidada (matriz completa de notas) de la sección en CSV."""
    asignaciones = AsignacionEstudiante.objects.filter(
        seccion=seccion,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('estudiante', 'estudiante__persona').order_by('estudiante__persona__apellidos')

    cursos = Curso.objects.filter(grado=seccion.grado, esta_eliminado=False).order_by('nombre_curso')

    headers = ['No.', 'Apellidos y Nombres', 'Código MINEDUC']
    for c in cursos:
        headers.append(c.nombre_curso)
    headers.append('Promedio Final')

    rows = []
    for idx, a in enumerate(asignaciones, start=1):
        fila = [idx, a.estudiante.persona.nombre_completo, a.estudiante.codigo_mineduc]
        suma_estudiante = Decimal(0)
        cursos_cnt = 0

        for c in cursos:
            notas = NotaBloque.objects.filter(asignacion_estudiante=a, curso=c, esta_eliminado=False)
            prom_curso = sum(n.nota_total for n in notas) / len(notas) if notas.exists() else Decimal(0)
            if notas.exists():
                suma_estudiante += prom_curso
                cursos_cnt += 1
                fila.append(f"{prom_curso:.1f}")
            else:
                fila.append("-")

        promedio_gral = (suma_estudiante / cursos_cnt) if cursos_cnt > 0 else Decimal(0)
        fila.append(f"{promedio_gral:.1f}")
        rows.append(fila)

    filename = f"Sabana_Notas_MED_{seccion.grado.nombre}_{seccion.letra}_{ciclo_escolar.anio}".replace(' ', '_')
    return IBACOOPReportCSV.generate_csv_response(filename, headers, rows)
