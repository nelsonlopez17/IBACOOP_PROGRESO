"""
APPS/academico/reports.py

Generación de reportes académicos en PDF con ReportLab para el Instituto El Progreso.
Incluye:
  1. Tarjeta / Boleta Oficial de Calificaciones del Ciclo Escolar.
  2. Certificación Acumulada de Estudios (Kardex Histórico).
"""
import io
from decimal import Decimal
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from APPS.academico.models import (
    Curso, NotaBloque, NotaFinalCurso, BloqueAcademico, AsignacionEstudiante
)


def generar_pdf_boleta_notas(asignacion_estudiante):
    """
    Genera la Tarjeta / Boleta Oficial de Calificaciones del Alumno en PDF.
    Desglosa las notas por Bimestre (B1, B2, B3, B4), Promedio Ordinario, Recuperaciones y Estado Final.
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
        fontSize=9,
        leading=12,
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
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F172A')
    )
    style_table_header = ParagraphStyle(
        'TblHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )
    style_cell = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )
    style_cell_bold = ParagraphStyle(
        'TblCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A'),
        alignment=1
    )

    estudiante = asignacion_estudiante.estudiante
    persona = estudiante.persona
    seccion = asignacion_estudiante.seccion
    ciclo = asignacion_estudiante.ciclo_escolar

    # 1. Encabezado Oficial
    header_data = [
        [
            Paragraph("INSTITUTO DE EDUCACIÓN BÁSICA<br/><font color='#7A1C21'>'EL PROGRESO'</font><br/><font size=8 color='#64748B'>SISTEMA DE GESTIÓN ESCOLAR (ERP)</font>", style_title),
            Paragraph(f"<b>BOLETA DE CALIFICACIONES</b><br/>Código MINEDUC: <b>{estudiante.codigo_mineduc}</b><br/>Ciclo Escolar <b>{ciclo.anio}</b>", style_header_right)
        ]
    ]
    t_header = Table(header_data, colWidths=[330, 210])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_VERDE, spaceBefore=4, spaceAfter=10))

    # 2. Datos del Estudiante
    datos_est = [
        [Paragraph("Nombre del Alumno:", style_label), Paragraph(persona.nombre_completo, style_val_bold),
         Paragraph("CUI / DPI:", style_label), Paragraph(persona.cui, style_val)],
        [Paragraph("Grado y Sección:", style_label), Paragraph(f"<b>{seccion.grado.nombre} — Sección {seccion.letra}</b>", style_val_bold),
         Paragraph("Ciclo Escolar:", style_label), Paragraph(str(ciclo.anio), style_val)]
    ]
    t_est = Table(datos_est, colWidths=[110, 160, 110, 160])
    t_est.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_est)
    story.append(Spacer(1, 10))

    # 3. Matriz de Calificaciones por Asignatura
    story.append(Paragraph("EVALUACIÓN DE ASIGNATURAS (PENSUM MINEDUC)", style_sec_header))
    story.append(Spacer(1, 4))

    # Bloques del ciclo
    bloques = BloqueAcademico.objects.filter(ciclo_escolar=ciclo, esta_eliminado=False).order_by('orden')
    cursos = Curso.objects.filter(grado=seccion.grado, esta_eliminado=False).order_by('nombre_curso')

    # Encabezado de la tabla de notas
    table_data = [
        [
            Paragraph("Asignatura / Curso", style_table_header),
            Paragraph("B1", style_table_header),
            Paragraph("B2", style_table_header),
            Paragraph("B3", style_table_header),
            Paragraph("B4", style_table_header),
            Paragraph("Prom. Ord.", style_table_header),
            Paragraph("Recup.", style_table_header),
            Paragraph("Nota Def.", style_table_header),
            Paragraph("Estado", style_table_header),
        ]
    ]

    sum_promedios = Decimal('0.00')
    count_cursos = 0

    for curso in cursos:
        # Notas por bloque
        n_b1 = NotaBloque.objects.filter(asignacion_estudiante=asignacion_estudiante, curso=curso, bloque_academico__orden=1, esta_eliminado=False).first()
        n_b2 = NotaBloque.objects.filter(asignacion_estudiante=asignacion_estudiante, curso=curso, bloque_academico__orden=2, esta_eliminado=False).first()
        n_b3 = NotaBloque.objects.filter(asignacion_estudiante=asignacion_estudiante, curso=curso, bloque_academico__orden=3, esta_eliminado=False).first()
        n_b4 = NotaBloque.objects.filter(asignacion_estudiante=asignacion_estudiante, curso=curso, bloque_academico__orden=4, esta_eliminado=False).first()

        v_b1 = f"{n_b1.nota_total:.1f}" if n_b1 else "-"
        v_b2 = f"{n_b2.nota_total:.1f}" if n_b2 else "-"
        v_b3 = f"{n_b3.nota_total:.1f}" if n_b3 else "-"
        v_b4 = f"{n_b4.nota_total:.1f}" if n_b4 else "-"

        # Nota final de curso
        n_final = NotaFinalCurso.objects.filter(asignacion_estudiante=asignacion_estudiante, curso=curso, esta_eliminado=False).first()
        if n_final:
            n_final.calcular_nota_final()
            p_ord = f"{n_final.nota_promedio:.1f}"
            recup = f"{max(n_final.nota_recuperacion_1 or 0, n_final.nota_recuperacion_2 or 0):.1f}" if n_final.aplica_recuperacion else "-"
            n_def = f"{n_final.nota_definitiva or n_final.nota_promedio:.1f}"
            estado_txt = "APROBADA" if n_final.esta_promocionado else "REPROBADA"
            sum_promedios += (n_final.nota_definitiva or n_final.nota_promedio)
        else:
            p_ord = "-"
            recup = "-"
            n_def = "-"
            estado_txt = "PENDIENTE"

        count_cursos += 1

        color_estado = "<font color='#1E6532'><b>APROBADA</b></font>" if estado_txt == "APROBADA" else (
            "<font color='#7A1C21'><b>REPROBADA</b></font>" if estado_txt == "REPROBADA" else "<font color='#64748B'>PENDIENTE</font>"
        )

        table_data.append([
            Paragraph(curso.nombre_curso, style_cell),
            Paragraph(v_b1, style_cell_bold),
            Paragraph(v_b2, style_cell_bold),
            Paragraph(v_b3, style_cell_bold),
            Paragraph(v_b4, style_cell_bold),
            Paragraph(p_ord, style_cell_bold),
            Paragraph(recup, style_cell),
            Paragraph(f"<b>{n_def}</b>", style_cell_bold),
            Paragraph(color_estado, style_cell_bold),
        ])

    # Fila de promedio general
    promedio_general = round(sum_promedios / count_cursos, 2) if count_cursos > 0 else Decimal('0.00')
    table_data.append([
        Paragraph("<b>PROMEDIO GENERAL DEL CICLO</b>", ParagraphStyle('TotLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_VERDE)),
        Paragraph("", style_cell), Paragraph("", style_cell), Paragraph("", style_cell), Paragraph("", style_cell), Paragraph("", style_cell), Paragraph("", style_cell),
        Paragraph(f"<b>{promedio_general:.2f} pts</b>", ParagraphStyle('TotVal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=COLOR_VERDE, alignment=1)),
        Paragraph("<b>FINAL</b>", ParagraphStyle('TotEst', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, alignment=1)),
    ])

    t_notas = Table(table_data, colWidths=[180, 40, 40, 40, 40, 50, 45, 55, 50])
    t_notas.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_VERDE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_BG_SLATE),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_notas)
    story.append(Spacer(1, 16))

    # 4. Leyenda de Escala de Evaluación MINEDUC
    style_leyenda = ParagraphStyle(
        'Leyenda',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=COLOR_GRIS
    )
    story.append(Paragraph(
        "Escala de Evaluación Oficial MINEDUC: Zona Máxima (60 pts) + Examen Bimestral (40 pts) = Total Bloque (100 pts). "
        "Nota mínima de aprobación por asignatura: <b>60.00 puntos</b>.",
        style_leyenda
    ))
    story.append(Spacer(1, 30))

    # 5. Firmas Oficiales
    datos_firmas = [
        [
            Paragraph("_______________________________________<br/>Firma del Docente Tutor de Sección", ParagraphStyle('Ctr1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1)),
            Paragraph("_______________________________________<br/>Firma y Sello de Dirección General", ParagraphStyle('Ctr2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1))
        ]
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
    response['Content-Disposition'] = f'inline; filename="Boleta_Notas_{persona.cui}_{ciclo.anio}.pdf"'
    return response


def generar_pdf_certificacion_estudios(estudiante):
    """
    Genera la Certificación Acumulada de Estudios (Kardex Histórico).
    Muestra la totalidad de grados y ciclos cursados por el alumno en el instituto.
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
        textColor=COLOR_VERDE,
        alignment=1
    )
    style_subtitle = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=COLOR_ROJO,
        alignment=1
    )
    style_sec = ParagraphStyle(
        'SecHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=COLOR_AZUL
    )
    style_cell = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11
    )
    style_cell_bold = ParagraphStyle(
        'CellB',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11
    )

    persona = estudiante.persona

    # 1. Encabezado
    story.append(Paragraph("INSTITUTO DE EDUCACIÓN BÁSICA 'EL PROGRESO'", style_title))
    story.append(Spacer(1, 2))
    story.append(Paragraph("CERTIFICACIÓN GENERAL DE ESTUDIOS (KARDEX ACUMULADO)", style_subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_VERDE, spaceBefore=6, spaceAfter=14))

    # 2. Datos Alumno
    datos_est = [
        [Paragraph("Nombre del Alumno:", style_cell_bold), Paragraph(persona.nombre_completo, style_cell_bold),
         Paragraph("CUI / DPI:", style_cell_bold), Paragraph(persona.cui, style_cell)],
        [Paragraph("Código MINEDUC:", style_cell_bold), Paragraph(estudiante.codigo_mineduc, style_cell_bold),
         Paragraph("Estado Académico:", style_cell_bold), Paragraph(estudiante.get_estado_estudiante_display(), style_cell_bold)]
    ]
    t_e = Table(datos_est, colWidths=[110, 160, 110, 160])
    t_e.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_SLATE),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_e)
    story.append(Spacer(1, 14))

    # 3. Recorrer Asignaciones Históricas por Ciclo
    asignaciones = AsignacionEstudiante.objects.filter(
        estudiante=estudiante,
        esta_eliminado=False
    ).select_related('seccion__grado', 'ciclo_escolar').order_by('ciclo_escolar__anio')

    if not asignaciones.exists():
        story.append(Paragraph("<i>El estudiante no posee asignaciones académicas registradas.</i>", style_cell))
    else:
        for asig in asignaciones:
            story.append(Paragraph(
                f"<b>GRADO: {asig.seccion.grado.nombre.upper()} — SECCIÓN {asig.seccion.letra} (CICLO LECTIVO {asig.ciclo_escolar.anio})</b>",
                style_sec
            ))
            story.append(Spacer(1, 4))

            notas_finales = NotaFinalCurso.objects.filter(
                asignacion_estudiante=asig,
                esta_eliminado=False
            ).select_related('curso').order_by('curso__nombre_curso')

            tbl_kardex = [
                [
                    Paragraph("Código", ParagraphStyle('Th1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)),
                    Paragraph("Asignatura / Curso", ParagraphStyle('Th2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)),
                    Paragraph("Promedio Final", ParagraphStyle('Th3', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=1)),
                    Paragraph("Resultado Final", ParagraphStyle('Th4', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=1)),
                ]
            ]

            sum_nota = Decimal('0.00')
            count_n = 0

            for nf in notas_finales:
                nf.calcular_nota_final()
                definitiva = nf.nota_definitiva or nf.nota_promedio
                sum_nota += definitiva
                count_n += 1
                est_txt = "APROBADA" if nf.esta_promocionado else "REPROBADA"

                tbl_kardex.append([
                    Paragraph(nf.curso.codigo_curso, style_cell),
                    Paragraph(nf.curso.nombre_curso, style_cell),
                    Paragraph(f"<b>{definitiva:.2f} pts</b>", ParagraphStyle('Ctn', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, alignment=1)),
                    Paragraph(f"<b>{est_txt}</b>", ParagraphStyle('Cte', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, alignment=1)),
                ])

            prom_grado = round(sum_nota / count_n, 2) if count_n > 0 else Decimal('0.00')
            tbl_kardex.append([
                Paragraph("<b>PROMEDIO GENERAL DE GRADO:</b>", style_cell_bold),
                Paragraph("", style_cell),
                Paragraph(f"<b>{prom_grado:.2f} pts</b>", ParagraphStyle('Ctn2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=COLOR_VERDE)),
                Paragraph("<b>PROMOVIDO</b>" if prom_grado >= 60 else "<b>RETENIDO</b>", ParagraphStyle('Cte2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=COLOR_VERDE if prom_grado >= 60 else COLOR_ROJO)),
            ])

            t_k = Table(tbl_kardex, colWidths=[80, 260, 100, 100])
            t_k.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), COLOR_AZUL),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('BACKGROUND', (0,-1), (-1,-1), COLOR_BG_SLATE),
                ('PADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(t_k)
            story.append(Spacer(1, 14))

    # 4. Firmas
    story.append(Spacer(1, 20))
    datos_firmas = [
        [
            Paragraph("_______________________________________<br/>Firma y Sello de Secretaría", ParagraphStyle('Ctr1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1)),
            Paragraph("_______________________________________<br/>Firma de Dirección General", ParagraphStyle('Ctr2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1))
        ]
    ]
    t_f = Table(datos_firmas, colWidths=[270, 270])
    t_f.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(t_f)

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Certificacion_Estudios_{persona.cui}.pdf"'
    return response
