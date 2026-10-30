"""
APPS/disciplina/reportes.py

Generación de citatorios oficiales a padres de familia y actas de compromiso disciplinario
en formato PDF ejecutivo mediante ReportLab, en cumplimiento con el Acuerdo Ministerial 01-2011 del MINEDUC.
"""
import io
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from APPS.reportes.generadores.base_pdf import (
    NumberedCanvas, ReportLabHelper, COLOR_VERDE, COLOR_ROJO, COLOR_AZUL, COLOR_TEXT, COLOR_MUTED, COLOR_BG_LIGHT, COLOR_BORDER
)


def generar_pdf_citacion_padre(citacion):
    """
    Genera el documento formal de citación al padre de familia o encargado,
    incluyendo fundamentación legal del MINEDUC y talón desprendible de acuse.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = ReportLabHelper.get_styles()
    styles['info_box'] = ParagraphStyle('InfoBox', parent=styles['notes'], fontSize=8, leading=10, textColor=COLOR_TEXT, backColor=COLOR_BG_LIGHT, borderPadding=6)
    styles['table_header'] = styles['td_bold']
    styles['table_cell'] = styles['td']
    styles['small_muted'] = styles['notes']

    story = []

    story.append(ReportLabHelper.build_header(
        doc_title="CITATORIO A PADRE DE FAMILIA O ENCARGADO",
        subtitle="COMISIÓN DE DISCIPLINA Y CONVIVENCIA ESCOLAR"
    ))
    story.append(Spacer(1, 10))

    marco_legal = (
        "<b>Fundamento Legal:</b> La presente citación se emite conforme al <b>Acuerdo Ministerial No. 01-2011</b> "
        "del Ministerio de Educación de Guatemala, <i>'Normativa de Convivencia Pacífica y Disciplina para una Cultura "
        "de Paz en los Centros Educativos'</i>, en salvaguarda del derecho a la educación, la debida audiencia y el desarrollo formativo integral."
    )
    story.append(Paragraph(marco_legal, styles['info_box']))
    story.append(Spacer(1, 10))

    incidente = citacion.incidente
    estudiante = incidente.estudiante
    fecha_local = timezone.localtime(citacion.fecha_hora_citacion) if timezone.is_aware(citacion.fecha_hora_citacion) else citacion.fecha_hora_citacion
    fecha_citacion = fecha_local.strftime('%d/%m/%Y')
    hora_citacion = fecha_local.strftime('%H:%M horas')

    datos = [
        [
            Paragraph("<b>Estudiante:</b>", styles['table_header']),
            Paragraph(estudiante.persona.nombre_completo, styles['table_cell']),
            Paragraph("<b>Código MINEDUC:</b>", styles['table_header']),
            Paragraph(estudiante.codigo_mineduc or "Pendiente de registro", styles['table_cell']),
        ],
        [
            Paragraph("<b>Fecha y Hora de Comparecencia:</b>", styles['table_header']),
            Paragraph(f"<font color='#7A1C21'><b>{fecha_citacion} a las {hora_citacion}</b></font>", styles['table_cell']),
            Paragraph("<b>Lugar:</b>", styles['table_header']),
            Paragraph(citacion.lugar, styles['table_cell']),
        ],
        [
            Paragraph("<b>Clasificación de Falta:</b>", styles['table_header']),
            Paragraph(f"<b>{incidente.get_tipo_falta_display()}</b> ({incidente.get_categoria_display()})", styles['table_cell']),
            Paragraph("<b>Fecha del Suceso:</b>", styles['table_header']),
            Paragraph(incidente.fecha.strftime('%d/%m/%Y'), styles['table_cell']),
        ],
    ]

    t_datos = Table(datos, colWidths=[130, 160, 110, 140])
    t_datos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_datos)
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>MOTIVO FORMAL DE LA CITACIÓN:</b>", styles['table_header']))
    story.append(Paragraph(citacion.motivo_citacion, styles['table_cell']))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>CIRCUNSTANCIAS DE LOS HECHOS:</b>", styles['table_header']))
    story.append(Paragraph(incidente.descripcion_hechos, styles['table_cell']))
    story.append(Spacer(1, 10))

    nota_padre = (
        "Se solicita su puntual asistencia y presentación con su respectivo Documento Personal de Identificación (DPI). "
        "Su presencia es fundamental para garantizar el acompañamiento formativo de su hijo(a), escuchar las recomendaciones "
        "pedagógicas y suscribir los compromisos de convivencia mutua."
    )
    story.append(Paragraph(nota_padre, styles['table_cell']))
    story.append(Spacer(1, 25))

    story.append(ReportLabHelper.build_signature_block([
        "Docente / Comisión de Disciplina",
        "Director (a)"
    ]))
    story.append(Spacer(1, 20))

    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_MUTED, dash=[4, 4], spaceAfter=8))
    story.append(Paragraph("✂ <i>CORTE POR LA LÍNEA — TALÓN DE NOTIFICACIÓN Y ACUSE DE RECIBIDO PARA SECRETARÍA</i>", styles['small_muted']))
    story.append(Spacer(1, 8))

    anio_actual = timezone.now().year
    talon_datos = [
        [
            Paragraph("<b>Estudiante:</b> " + estudiante.persona.nombre_completo, styles['small_muted']),
            Paragraph(f"<b>Citación programada para:</b> {fecha_citacion} {hora_citacion}", styles['small_muted']),
        ],
        [
            Paragraph("<b>Nombre del Padre/Madre/Encargado:</b> ____________________________________", styles['small_muted']),
            Paragraph("<b>DPI:</b> ___________________________", styles['small_muted']),
        ],
        [
            Paragraph("<b>Firma de Recibido del Encargado:</b> __________________________________", styles['small_muted']),
            Paragraph(f"<b>Fecha en que se recibe:</b> ____/____/{anio_actual}", styles['small_muted']),
        ],
    ]
    t_talon = Table(talon_datos, colWidths=[320, 220])
    t_talon.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_talon)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def generar_pdf_acta_compromiso(citacion):
    """
    Genera el Acta Oficial de Compromiso y Convivencia Escolar
    firmada al atender la citación del estudiante y sus encargados.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = ReportLabHelper.get_styles()
    styles['table_header'] = styles['td_bold']
    styles['table_cell'] = styles['td']

    story = []

    story.append(ReportLabHelper.build_header(
        doc_title="ACTA DE COMPROMISO Y CONVIVENCIA ESCOLAR",
        subtitle="MINISTERIO DE EDUCACIÓN — ACUERDO MINISTERIAL NO. 01-2011"
    ))
    story.append(Spacer(1, 10))

    incidente = citacion.incidente
    estudiante = incidente.estudiante
    fecha_local = timezone.localtime(citacion.fecha_hora_citacion) if timezone.is_aware(citacion.fecha_hora_citacion) else citacion.fecha_hora_citacion

    texto_acta = (
        f"En las instalaciones del Instituto de Educación Básica por Cooperativa 'El Progreso', siendo las "
        f"<b>{fecha_local.strftime('%H:%M')} horas del día {fecha_local.strftime('%d/%m/%Y')}</b>, "
        f"comparecen en la Dirección del plantel el/la estudiante <b>{estudiante.persona.nombre_completo}</b>, "
        f"su padre, madre o encargado, y las autoridades educativas del establecimiento, con el objeto de dejar constancia "
        f"de los acuerdos de convivencia pacífica derivados del incidente registrado el día {incidente.fecha.strftime('%d/%m/%Y')}."
    )
    story.append(Paragraph(texto_acta, styles['table_cell']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>1. ANTECEDENTES Y DESCRIPCIÓN DE LA FALTA:</b>", styles['table_header']))
    story.append(Paragraph(incidente.descripcion_hechos, styles['table_cell']))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>2. DECLARACIÓN / DERECHO DE AUDIENCIA DEL ESTUDIANTE:</b>", styles['table_header']))
    story.append(Paragraph(incidente.descargo_estudiante or "El estudiante manifestó su compromiso de acatar las normas de conducta y convivencia pacífica.", styles['table_cell']))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>3. MEDIDA FORMATIVA Y PEDAGÓGICA APLICADA:</b>", styles['table_header']))
    story.append(Paragraph(incidente.medida_formativa or "Amonestación formativa y labor reflexiva de valores institucionales.", styles['table_cell']))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>4. COMPROMISOS ADQUIRIDOS:</b>", styles['table_header']))
    acuerdos_texto = citacion.acuerdos_alcanzados or (
        "El/la estudiante se compromete formalmente a mantener una conducta intachable, respetar a docentes y compañeros, "
        "y dar cumplimiento fiel al reglamento interno. El padre de familia o encargado se compromete a brindar supervisión "
        "directa y mantener comunicación periódica con la Comisión de Disciplina."
    )
    story.append(Paragraph(acuerdos_texto, styles['table_cell']))
    story.append(Spacer(1, 25))

    story.append(ReportLabHelper.build_signature_block([
        "Estudiante",
        "Padre de Familia o Encargado",
        "Director (a)"
    ]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
