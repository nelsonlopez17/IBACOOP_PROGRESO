"""
reportes/reportes_academicos.py

Generación de reportes académicos oficiales para el Instituto Básico por Cooperativa El Progreso (IBACOOP):
  1. Boleta Oficial de Calificaciones Bimestral / Final (PDF)
  2. Cuadro General de Calificaciones por Sección (PDF y CSV/Excel)
  3. Cuadro de Honor y Rendimiento Escolar (PDF y CSV/Excel)
  4. Listado Oficial de Estudiantes Inscritos por Sección (PDF y CSV/Excel)
  5. Constancia Oficial de Inscripción Escolar (PDF)
  6. Reporte de Alertas Tempranas de Reprobación (CSV/Excel)
"""
import io
from collections import defaultdict
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
        subtitle=f"{ciclo_escolar.anio} • Nivel Medio - Ciclo Básico"
    ))
    story.append(Spacer(1, 10))

    datos_estudiante = [
        [
            Paragraph(f"<b>ESTUDIANTE:</b> {estudiante.persona.nombre_completo.upper()}", styles['td']),
            Paragraph(f"<b>CÓDIGO PERSONAL MINEDUC:</b> {estudiante.codigo_mineduc or 'PENDIENTE'}", styles['td']),
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
        "Director (a)",
        "Docente Guía",
        "Padre de Familia o Encargado"
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Boleta_{estudiante.persona.apellidos}_{estudiante.persona.nombres}_{ciclo_escolar.anio}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generar_pdf_cuadro_calificaciones(seccion, ciclo_escolar):
    """
    Genera el Cuadro General de Calificaciones por Sección en PDF horizontal.
    Presenta la matriz de notas finales acumuladas de todos los estudiantes y cursos.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=28,
        leftMargin=28,
        topMargin=28,
        bottomMargin=28
    )

    story = []
    styles = ReportLabHelper.get_styles()

    asignaciones = AsignacionEstudiante.objects.filter(
        seccion=seccion,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('estudiante__persona').order_by('estudiante__persona__apellidos', 'estudiante__persona__nombres')

    cursos = list(Curso.objects.filter(grado=seccion.grado, esta_eliminado=False).order_by('nombre_curso'))
    num_cursos = len(cursos)

    # optimizacion sql: obtener todas las notas en una sola consulta
    notas_qs = NotaBloque.objects.filter(
        asignacion_estudiante__in=asignaciones,
        esta_eliminado=False
    ).values('asignacion_estudiante_id', 'curso_id', 'nota_zona', 'nota_examen')

    notas_map = defaultdict(list)
    for n in notas_qs:
        total = (n['nota_zona'] or Decimal(0)) + (n['nota_examen'] or Decimal(0))
        notas_map[(n['asignacion_estudiante_id'], n['curso_id'])].append(total)

    story.append(ReportLabHelper.build_header(
        doc_title="CUADRO GENERAL DE CALIFICACIONES POR SECCIÓN",
        subtitle=f"{seccion.grado.nombre} • Sección '{seccion.letra}' • {ciclo_escolar.anio}",
        orientation_landscape=True
    ))
    story.append(Spacer(1, 8))

    # ancho disponible: 736 pt
    col_w_no = 24
    col_w_est = 180
    col_w_prom = 45
    col_w_estatus = 55
    ancho_restante = 736 - (col_w_no + col_w_est + col_w_prom + col_w_estatus)
    col_w_curso = max(32, ancho_restante / max(1, num_cursos))

    headers = [
        Paragraph("<b>No.</b>", styles['th']),
        Paragraph("<b>APELLIDOS Y NOMBRES</b>", styles['th']),
    ]
    for c in cursos:
        # abreviar si el nombre es extenso
        nombre_c = c.nombre_curso[:14] + '...' if len(c.nombre_curso) > 16 else c.nombre_curso
        headers.append(Paragraph(f"<b>{nombre_c}</b>", styles['th']))
    headers.append(Paragraph("<b>PROM.</b>", styles['th']))
    headers.append(Paragraph("<b>ESTADO</b>", styles['th']))

    tabla_data = [headers]

    for idx, a in enumerate(asignaciones, start=1):
        fila = [
            Paragraph(str(idx), styles['td_center']),
            Paragraph(f"<b>{a.estudiante.persona.apellidos},</b> {a.estudiante.persona.nombres}", styles['td']),
        ]
        suma_gral = Decimal(0)
        cursos_eval = 0

        for c in cursos:
            pts_lista = notas_map.get((a.id, c.id), [])
            if pts_lista:
                prom_c = sum(pts_lista) / len(pts_lista)
                suma_gral += prom_c
                cursos_eval += 1
                color_p = "#7A1C21" if prom_c < 60 else "#0F172A"
                fila.append(Paragraph(f"<font color='{color_p}'>{prom_c:.0f}</font>", styles['td_center']))
            else:
                fila.append(Paragraph("-", styles['td_center']))

        prom_final = (suma_gral / cursos_eval) if cursos_eval > 0 else Decimal(0)
        color_pf = "#7A1C21" if prom_final < 60 else "#1E6532"
        estado_txt = "PROMOVIDO" if prom_final >= 60 else ("EN RIESGO" if cursos_eval > 0 else "S/N")

        fila.append(Paragraph(f"<font color='{color_pf}'><b>{prom_final:.1f}</b></font>", styles['td_center']))
        fila.append(Paragraph(f"<b>{estado_txt}</b>", styles['td_center']))
        tabla_data.append(fila)

    col_widths = [col_w_no, col_w_est] + [col_w_curso] * num_cursos + [col_w_prom, col_w_estatus]
    t_cuadro = Table(tabla_data, colWidths=col_widths, repeatRows=1)
    t_cuadro.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_cuadro)
    story.append(Spacer(1, 20))

    story.append(ReportLabHelper.build_signature_block([
        "Director (a)",
        "Docente Guía",
        "Comisión de Evaluación"
    ], orientation_landscape=True))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Cuadro_Calificaciones_{seccion.grado.nombre}_{seccion.letra}_{ciclo_escolar.anio}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generar_csv_cuadro_calificaciones(seccion, ciclo_escolar):
    """
    Genera exportación CSV/Excel del Cuadro General de Calificaciones por Sección.
    Optimizado para resolver en una sola consulta SQL la totalidad de las calificaciones.
    """
    asignaciones = AsignacionEstudiante.objects.filter(
        seccion=seccion,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('estudiante__persona').order_by('estudiante__persona__apellidos', 'estudiante__persona__nombres')

    cursos = list(Curso.objects.filter(grado=seccion.grado, esta_eliminado=False).order_by('nombre_curso'))

    notas_qs = NotaBloque.objects.filter(
        asignacion_estudiante__in=asignaciones,
        esta_eliminado=False
    ).values('asignacion_estudiante_id', 'curso_id', 'nota_zona', 'nota_examen')

    notas_map = defaultdict(list)
    for n in notas_qs:
        total = (n['nota_zona'] or Decimal(0)) + (n['nota_examen'] or Decimal(0))
        notas_map[(n['asignacion_estudiante_id'], n['curso_id'])].append(total)

    headers = ['No.', 'Apellidos y Nombres', 'Código MINEDUC', 'CUI / DPI']
    for c in cursos:
        headers.append(c.nombre_curso)
    headers.extend(['Promedio Final (Pts)', 'Resultado'])

    rows = []
    for idx, a in enumerate(asignaciones, start=1):
        fila = [
            idx,
            a.estudiante.persona.nombre_completo,
            a.estudiante.codigo_mineduc or 'PENDIENTE',
            a.estudiante.persona.cui or 'N/A'
        ]
        suma_estudiante = Decimal(0)
        cursos_cnt = 0

        for c in cursos:
            pts_lista = notas_map.get((a.id, c.id), [])
            if pts_lista:
                prom_c = sum(pts_lista) / len(pts_lista)
                suma_estudiante += prom_c
                cursos_cnt += 1
                fila.append(f"{prom_c:.1f}")
            else:
                fila.append("-")

        promedio_gral = (suma_estudiante / cursos_cnt) if cursos_cnt > 0 else Decimal(0)
        fila.append(f"{promedio_gral:.1f}")
        fila.append("PROMOVIDO" if promedio_gral >= 60 else ("EN RIESGO" if cursos_cnt > 0 else "SIN NOTAS"))
        rows.append(fila)

    filename = f"Cuadro_Calificaciones_{seccion.grado.nombre}_{seccion.letra}_{ciclo_escolar.anio}".replace(' ', '_')
    return IBACOOPReportCSV.generate_csv_response(filename, headers, rows)


# alias para retrocompatibilidad
generar_csv_sabana_notas = generar_csv_cuadro_calificaciones


def generar_pdf_cuadro_honor(seccion, ciclo_escolar):
    """Genera el informe formal en PDF del Cuadro de Honor y Rendimiento de la Sección."""
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

    asignaciones = AsignacionEstudiante.objects.filter(
        seccion=seccion,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('estudiante__persona')

    notas_qs = NotaBloque.objects.filter(
        asignacion_estudiante__in=asignaciones,
        esta_eliminado=False
    ).values('asignacion_estudiante_id', 'nota_zona', 'nota_examen')

    notas_map = defaultdict(list)
    for n in notas_qs:
        total = (n['nota_zona'] or Decimal(0)) + (n['nota_examen'] or Decimal(0))
        notas_map[n['asignacion_estudiante_id']].append(total)

    ranking = []
    for a in asignaciones:
        pts = notas_map.get(a.id, [])
        prom = (sum(pts) / len(pts)) if pts else Decimal(0)
        ranking.append({
            'estudiante': a.estudiante.persona.nombre_completo,
            'cui': a.estudiante.persona.cui,
            'codigo_mineduc': a.estudiante.codigo_mineduc or 'PENDIENTE',
            'promedio': round(prom, 2),
            'cursos_evaluados': len(pts),
        })

    ranking.sort(key=lambda x: x['promedio'], reverse=True)

    story.append(ReportLabHelper.build_header(
        doc_title="CUADRO DE HONOR Y EXCELENCIA ACADÉMICA",
        subtitle=f"{seccion.grado.nombre} • Sección '{seccion.letra}' • {ciclo_escolar.anio}"
    ))
    story.append(Spacer(1, 12))

    tabla_data = [
        [
            Paragraph("<b>PUESTO</b>", styles['th']),
            Paragraph("<b>ESTUDIANTE DESTACADO</b>", styles['th']),
            Paragraph("<b>CÓDIGO MINEDUC</b>", styles['th']),
            Paragraph("<b>CUI / DPI</b>", styles['th']),
            Paragraph("<b>PROMEDIO (PTS)</b>", styles['th']),
            Paragraph("<b>MENCIÓN</b>", styles['th']),
        ]
    ]

    for idx, r in enumerate(ranking, start=1):
        puesto_str = f"<b>{idx}° Lugar</b>" if idx <= 3 else f"{idx}°"
        mencion = "PRIMER LUGAR" if idx == 1 else ("SEGUNDO LUGAR" if idx == 2 else ("TERCER LUGAR" if idx == 3 else "DESTACADO"))
        color_fondo = COLOR_BG_LIGHT if idx % 2 == 0 else colors.white

        tabla_data.append([
            Paragraph(puesto_str, styles['td_center']),
            Paragraph(f"<b>{r['estudiante']}</b>", styles['td']),
            Paragraph(r['codigo_mineduc'], styles['td_center']),
            Paragraph(r['cui'], styles['td_center']),
            Paragraph(f"<b>{r['promedio']:.2f}</b>", styles['td_center']),
            Paragraph(f"<font color='{'#1E6532' if idx <= 3 else '#64748B'}'><b>{mencion}</b></font>", styles['td_center']),
        ])

    col_widths = [65, 200, 95, 80, 55, 45]
    t_honor = Table(tabla_data, colWidths=col_widths)
    t_honor.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_honor)
    story.append(Spacer(1, 35))

    story.append(ReportLabHelper.build_signature_block([
        "Director (a)",
        "Docente Guía"
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Cuadro_Honor_{seccion.grado.nombre}_{seccion.letra}_{ciclo_escolar.anio}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generar_csv_cuadro_honor(seccion, ciclo_escolar):
    """Genera exportación CSV del Cuadro de Honor / Ranking de la sección."""
    asignaciones = AsignacionEstudiante.objects.filter(
        seccion=seccion,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('estudiante', 'estudiante__persona')

    notas_qs = NotaBloque.objects.filter(
        asignacion_estudiante__in=asignaciones,
        esta_eliminado=False
    ).values('asignacion_estudiante_id', 'nota_zona', 'nota_examen')

    notas_map = defaultdict(list)
    for n in notas_qs:
        total = (n['nota_zona'] or Decimal(0)) + (n['nota_examen'] or Decimal(0))
        notas_map[n['asignacion_estudiante_id']].append(total)

    ranking = []
    for a in asignaciones:
        pts = notas_map.get(a.id, [])
        prom = (sum(pts) / len(pts)) if pts else Decimal(0)
        ranking.append({
            'estudiante': a.estudiante.persona.nombre_completo,
            'cui': a.estudiante.persona.cui,
            'codigo_mineduc': a.estudiante.codigo_mineduc or 'PENDIENTE',
            'promedio': round(prom, 2),
            'cursos_evaluados': len(pts),
        })

    ranking.sort(key=lambda x: x['promedio'], reverse=True)

    headers = ['Posición', 'Estudiante', 'Código MINEDUC', 'CUI / DPI', 'Promedio General (Pts)', 'Cursos Evaluados']
    rows = []
    for idx, r in enumerate(ranking, start=1):
        rows.append([idx, r['estudiante'], r['codigo_mineduc'], r['cui'], f"{r['promedio']:.2f}", r['cursos_evaluados']])

    filename = f"Cuadro_Honor_{seccion.grado.nombre}_{seccion.letra}_{ciclo_escolar.anio}".replace(' ', '_')
    return IBACOOPReportCSV.generate_csv_response(filename, headers, rows)


def generar_pdf_listado_estudiantes(seccion, ciclo_escolar):
    """
    Genera el Listado Oficial de Estudiantes Inscritos por Grado y Sección en PDF.
    Formato indispensable para Secretaría, Dirección y control del Docente Guía.
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

    asignaciones = AsignacionEstudiante.objects.filter(
        seccion=seccion,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related(
        'estudiante__persona',
        'estudiante__encargado__persona'
    ).order_by('estudiante__persona__apellidos', 'estudiante__persona__nombres')

    story.append(ReportLabHelper.build_header(
        doc_title="LISTADO OFICIAL DE ESTUDIANTES INSCRITOS",
        subtitle=f"{seccion.grado.nombre} • Sección '{seccion.letra}' • {ciclo_escolar.anio}",
        orientation_landscape=True
    ))
    story.append(Spacer(1, 10))

    tabla_data = [
        [
            Paragraph("<b>No.</b>", styles['th']),
            Paragraph("<b>APELLIDOS Y NOMBRES DEL ESTUDIANTE</b>", styles['th']),
            Paragraph("<b>CÓDIGO MINEDUC</b>", styles['th']),
            Paragraph("<b>CUI / DPI</b>", styles['th']),
            Paragraph("<b>GÉNERO</b>", styles['th']),
            Paragraph("<b>FECHA NAC.</b>", styles['th']),
            Paragraph("<b>PADRE DE FAMILIA O ENCARGADO</b>", styles['th']),
            Paragraph("<b>TELÉFONO</b>", styles['th']),
        ]
    ]

    for idx, a in enumerate(asignaciones, start=1):
        p = a.estudiante.persona
        enc = a.estudiante.encargado.persona if a.estudiante.encargado else None
        nombre_enc = enc.nombre_completo if enc else (a.estudiante.nombre_padre or a.estudiante.nombre_madre or "No registrado")
        tel_enc = enc.telefono_principal if enc and enc.telefono_principal else (a.estudiante.telefono_padre or a.estudiante.telefono_madre or "Sin registro")
        fnac = p.fecha_nacimiento.strftime('%d/%m/%Y') if p.fecha_nacimiento else "N/A"

        tabla_data.append([
            Paragraph(str(idx), styles['td_center']),
            Paragraph(f"<b>{p.apellidos},</b> {p.nombres}", styles['td']),
            Paragraph(a.estudiante.codigo_mineduc or 'PENDIENTE', styles['td_center']),
            Paragraph(p.cui or 'N/A', styles['td_center']),
            Paragraph(p.get_genero_display()[:1] if hasattr(p, 'get_genero_display') and p.genero else "N/A", styles['td_center']),
            Paragraph(fnac, styles['td_center']),
            Paragraph(nombre_enc, styles['td']),
            Paragraph(tel_enc, styles['td_center']),
        ])

    col_widths = [26, 210, 85, 80, 45, 60, 150, 80]
    t_lista = Table(tabla_data, colWidths=col_widths, repeatRows=1)
    t_lista.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_lista)
    story.append(Spacer(1, 25))

    story.append(ReportLabHelper.build_signature_block([
        "Secretaría",
        "Docente Guía",
        "Director (a)"
    ], orientation_landscape=True))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Listado_Estudiantes_{seccion.grado.nombre}_{seccion.letra}_{ciclo_escolar.anio}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def generar_csv_listado_estudiantes(seccion, ciclo_escolar):
    """Genera exportación CSV/Excel del listado oficial de estudiantes de la sección."""
    asignaciones = AsignacionEstudiante.objects.filter(
        seccion=seccion,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('estudiante__persona', 'estudiante__encargado__persona').order_by('estudiante__persona__apellidos', 'estudiante__persona__nombres')

    headers = [
        'No.', 'Apellidos', 'Nombres', 'Código MINEDUC', 'CUI / DPI',
        'Género', 'Fecha de Nacimiento', 'Padre de Familia o Encargado', 'Teléfono de Contacto'
    ]
    rows = []
    for idx, a in enumerate(asignaciones, start=1):
        p = a.estudiante.persona
        enc = a.estudiante.encargado.persona if a.estudiante.encargado else None
        nombre_enc = enc.nombre_completo if enc else (a.estudiante.nombre_padre or a.estudiante.nombre_madre or "No registrado")
        tel_enc = enc.telefono_principal if enc and enc.telefono_principal else (a.estudiante.telefono_padre or a.estudiante.telefono_madre or "Sin registro")
        fnac = p.fecha_nacimiento.strftime('%d/%m/%Y') if p.fecha_nacimiento else "N/A"

        rows.append([
            idx,
            p.apellidos,
            p.nombres,
            a.estudiante.codigo_mineduc or 'PENDIENTE',
            p.cui or 'N/A',
            p.get_genero_display() if hasattr(p, 'get_genero_display') and p.genero else "N/A",
            fnac,
            nombre_enc,
            tel_enc
        ])

    filename = f"Listado_Estudiantes_{seccion.grado.nombre}_{seccion.letra}_{ciclo_escolar.anio}".replace(' ', '_')
    return IBACOOPReportCSV.generate_csv_response(filename, headers, rows)


def generar_pdf_constancia_inscripcion(estudiante, ciclo_escolar):
    """
    Genera la Constancia Oficial de Inscripción Escolar en PDF.
    Acredita oficialmente que el estudiante se encuentra legalmente inscrito en el ciclo.
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

    asignacion = AsignacionEstudiante.objects.filter(
        estudiante=estudiante,
        ciclo_escolar=ciclo_escolar,
        esta_eliminado=False
    ).select_related('seccion__grado').first()

    seccion_txt = f"{asignacion.seccion.grado.nombre}, Sección '{asignacion.seccion.letra}'" if asignacion else "Grado por asignar"

    story.append(ReportLabHelper.build_header(
        doc_title="CONSTANCIA OFICIAL DE INSCRIPCIÓN ESCOLAR",
        subtitle=f"{ciclo_escolar.anio} • Nivel Medio - Ciclo de Educación Básica"
    ))
    story.append(Spacer(1, 25))

    p = estudiante.persona
    texto_constancia = (
        f"La Dirección y Secretaría del <b>INSTITUTO DE EDUCACIÓN BÁSICA POR COOPERATIVA DE ENSEÑANZA "
        f"'EL PROGRESO' (IBACOOP)</b>, por este medio:"
    )
    story.append(Paragraph(texto_constancia, styles['td']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>HACE CONSTAR QUE:</b>", styles['section_heading']))
    story.append(Spacer(1, 15))

    cuerpo = (
        f"El (la) estudiante <b>{p.nombre_completo.upper()}</b>, quien se identifica con Código Personal "
        f"MINEDUC No. <b>{estudiante.codigo_mineduc or 'En trámite'}</b> y Código Único de Identificación (CUI) "
        f"No. <b>{p.cui or 'Sin registro'}</b>, se encuentra formal y legalmente <b>INSCRITO(A)</b> en esta "
        f"institución educativa para cursar los estudios correspondientes a <b>{seccion_txt.upper()}</b> "
        f"durante el año <b>{ciclo_escolar.anio}</b>."
    )
    story.append(Paragraph(cuerpo, styles['td']))
    story.append(Spacer(1, 15))

    fecha_hoy = timezone.now()
    meses_es = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    cierre = (
        f"Y para los usos legales y administrativos que al (a la) interesado(a) convengan, se extiende la "
        f"presente constancia con los timbres y sellos oficiales de la institución, en el municipio de El Progreso, "
        f"a los {fecha_hoy.day} días del mes de {meses_es[fecha_hoy.month]} del año {fecha_hoy.year}."
    )
    story.append(Paragraph(cierre, styles['td']))
    story.append(Spacer(1, 60))

    story.append(ReportLabHelper.build_signature_block([
        "Secretario(a) Contador(a)",
        "Director (a)"
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"Constancia_Inscripcion_{p.apellidos}_{p.nombres}_{ciclo_escolar.anio}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
