import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import os

def create_apa7_document(output_path):
    doc = docx.Document()
    
    # page margins apa inch cm on all sides
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
        # configure header page numbering top right
        header = section.header
        header_p = header.paragraphs[0]
        header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        header_run = header_p.add_run()
        header_run.font.name = 'Times New Roman'
        header_run.font.size = Pt(10)
        header_run.font.color.rgb = RGBColor(120, 120, 120)
        
        # add page field
        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = 'PAGE'
        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'separate')
        fldChar3 = OxmlElement('w:fldChar')
        fldChar3.set(qn('w:fldCharType'), 'end')
        
        r = header_run._r
        r.append(fldChar1)
        r.append(instrText)
        r.append(fldChar2)
        r.append(fldChar3)

    # document base styles setup
    styles = doc.styles
    
    # normal style body text
    style_normal = styles['Normal']
    font_normal = style_normal.font
    font_normal.name = 'Times New Roman'
    font_normal.size = Pt(12)
    font_normal.color.rgb = RGBColor(0, 0, 0)
    style_normal.paragraph_format.line_spacing = 1.5
    style_normal.paragraph_format.space_after = Pt(6)
    style_normal.paragraph_format.space_before = Pt(0)
    style_normal.paragraph_format.first_line_indent = Inches(0.5)

    # helper function for adding paragraphs
    def add_p(text, indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, italic=False, space_after=6):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(0)
        if indent:
            p.paragraph_format.first_line_indent = Inches(0.5)
        else:
            p.paragraph_format.first_line_indent = Inches(0)
            
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    # helper functions for headings apa word toc mapped
    def add_h1(text):
        p = doc.add_paragraph(style='Heading 1')
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(12)
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.keep_with_next = True
        
        # format runs in heading
        p.text = "" # Clear default run
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_h2(text):
        p = doc.add_paragraph(style='Heading 2')
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.keep_with_next = True
        
        p.text = ""
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_h3(text):
        p = doc.add_paragraph(style='Heading 3')
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.keep_with_next = True
        
        p.text = ""
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.italic = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    # helper function to insert native word toc xml
    def insert_word_toc(paragraph):
        run = paragraph.add_run()
        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = r'TOC \o "1-3" \h \z \u'
        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'separate')
        fldChar3 = OxmlElement('w:fldChar')
        fldChar3.set(qn('w:fldCharType'), 'end')
        
        r = run._r
        r.append(fldChar1)
        r.append(instrText)
        r.append(fldChar2)
        r.append(fldChar3)

    # caratula portada apa format
    for _ in range(3):
        add_p("", indent=False, space_after=0)
        
    p_title = add_p("SISTEMA WEB INTEGRAL DE GESTIÓN ESCOLAR (ERP) PARA EL INSTITUTO DE EDUCACIÓN BÁSICA \"EL PROGRESO\"", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, space_after=18)
    p_sub = add_p("Documentación Académica y Propuesta Metodológica de Desarrollo", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, space_after=36)
    
    for _ in range(4):
        add_p("", indent=False, space_after=0)

    # placeholders clearly demarcated
    p_meta1 = add_p("Presentado por:", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, space_after=4)
    p_meta2 = add_p("[Escriba aquí los nombres y apellidos completados del autor o integrantes]", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)
    
    p_meta3 = add_p("Institución / Centro Educativo:", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, space_after=4)
    p_meta4 = add_p("[Escriba aquí el nombre del establecimiento educativo, facultad o institución]", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)

    p_meta5 = add_p("Curso / Asignatura:", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, space_after=4)
    p_meta6 = add_p("[Escriba aquí el nombre de la materia o seminario de graduación]", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)

    p_meta7 = add_p("Catedrático / Asesor:", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, space_after=4)
    p_meta8 = add_p("[Escriba aquí el nombre y título académico del docente o asesor]", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)

    p_meta9 = add_p("Guatemala, [Escriba aquí el mes y año de entrega]", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, space_after=0)

    doc.add_page_break()

    # dedicatoria
    add_h1("Dedicatoria")
    add_p("", indent=False, space_after=12)
    
    p_ded = add_p("[Espacio reservado para la redacción libre de la dedicatoria por parte del autor del documento]", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, space_after=18)
    
    doc.add_page_break()

    # agradecimiento
    add_h1("Agradecimiento")
    add_p("", indent=False, space_after=12)

    p_agr = add_p("[Espacio reservado para la redacción libre de los agradecimientos institucionales y personales por parte del autor del documento]", indent=False, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, space_after=18)

    doc.add_page_break()

    # indice general tabla de contenidos
    add_h1("Índice General")
    
    add_p("La siguiente estructura recopila las secciones principales y secundarias desarrolladas en el documento. En entornos Microsoft Word, el campo automatizado inferior actualizará los números de página finales mediante la instrucción de actualización de campos.", indent=False, italic=True, space_after=12)

    # insert native word toc field
    p_toc = doc.add_paragraph()
    p_toc.paragraph_format.first_line_indent = Inches(0)
    p_toc.paragraph_format.space_after = Pt(18)
    insert_word_toc(p_toc)

    # visual structured table of contents preview
    add_p("Resumen de Contenido y Titulación Configurada:", indent=False, bold=True, space_after=6)

    toc_items = [
        ("Introducción", "1"),
        ("Capítulo 1. Marco Conceptual", "2"),
        ("    1.1 Presentación del problema", "2"),
        ("    1.2 Plantear el problema", "3"),
        ("    1.3 Formular el problema", "5"),
        ("    1.4 Interrogantes de la investigación", "5"),
        ("    1.5 Objetivos", "6"),
        ("        1.5.1 De la investigación", "6"),
        ("        1.5.2 Generales", "7"),
        ("        1.5.3 Específicos", "7"),
        ("    1.6 Hipótesis", "8"),
        ("        1.6.1 Hipótesis General", "8"),
        ("        1.6.2 Hipótesis Específicas", "9")
    ]

    for title, pg in toc_items:
        p_t = doc.add_paragraph()
        p_t.paragraph_format.first_line_indent = Inches(0)
        p_t.paragraph_format.space_after = Pt(2)
        p_t.paragraph_format.line_spacing = 1.15
        r_title = p_t.add_run(title)
        r_title.font.name = 'Times New Roman'
        r_title.font.size = Pt(11)
        
        # fill dots
        dots_count = max(5, 80 - len(title) * 2)
        r_dots = p_t.add_run(" " + "." * dots_count + " ")
        r_dots.font.name = 'Times New Roman'
        r_dots.font.size = Pt(9)
        r_dots.font.color.rgb = RGBColor(160, 160, 160)
        
        r_pg = p_t.add_run(pg)
        r_pg.font.name = 'Times New Roman'
        r_pg.font.size = Pt(11)
        r_pg.font.bold = True

    doc.add_page_break()

    # introduccion
    add_h1("Introducción")

    add_p("La transformación digital de los entornos educativos constituye una prioridad estratégica para fortalecer la gestión administrativa, optimizar la trazabilidad académica y elevar la transparencia financiera en las instituciones de enseñanza secundaria. En el contexto de la educación media en Guatemala, el ciclo de educación básica enfrenta constantes desafíos normativos y operativos vinculados al manejo eficiente de expedientes estudiantiles, la consolidación de actas de notas por bloques académicos y la cobranza ordenada de cuotas escolares. La adopción de sistemas centralizados de planificación de recursos empresariales, adaptados al sector educativo, surge como una solución tecnológica pertinente para sustituir métodos manuales propensos a inconsistencias e integrar todas las áreas funcionales en un único entorno de trabajo.")

    add_p("El presente trabajo de investigación y desarrollo documenta el diseño, la fundamentación teórica y la implementación del Sistema Web Integral de Gestión Escolar para el Instituto de Educación Básica \"El Progreso\". Esta plataforma ha sido estructurada considerando rigurosamente los requerimientos del Ministerio de Educación de Guatemala, garantizando que el expediente de cada alumno contenga la totalidad de los documentos legales exigidos para el ciclo básico diurno regular. Asimismo, el sistema articula la gestión académica con un módulo financiero de cuenta corriente, permitiendo una supervisión rigurosa de los cobros, abonos y saldos pendientes sin comprometer la fluidez de las operaciones institucionales.")

    add_p("La arquitectura técnica del sistema se fundamenta en principios sólidos de ingeniería de software, incorporando patrones de diseño como la herencia de entidades de datos personales mediante el patrón supertipo y subtipo, la conservación inmutable de historiales de modificación en operaciones críticas y el aislamiento lógico de registros eliminados. Asimismo, se implementa una estrategia de autenticación multicriterio que permite el acceso seguro mediante el código único de identificación o el correo electrónico institucional, asignando permisos específicos según los distintos roles de usuario que interactúan en la comunidad educativa.")

    add_p("El documento se encuentra organizado de manera sistemática. En el Capítulo 1, correspondiente al Marco Conceptual, se establece la contextualización detallada de la problemática detectada en la institución, la delimitación y formulación del problema central, las interrogantes orientadoras de la investigación, la definición jerárquica de objetivos generales y específicos, así como el planteamiento formal de las hipótesis que guían la evaluación de la solución tecnológica desarrollada.")

    doc.add_page_break()

    # capitulo marco conceptual
    add_h1("Capítulo 1. Marco Conceptual")

    # presentacion del problema
    add_h2("1.1 Presentación del problema")

    add_p("Las instituciones educativas de nivel medio en la República de Guatemala desenvuelven sus labores administrativas dentro de un marco regulatorio exigente supervisado por el Ministerio de Educación. En los establecimientos de Educación Básica, la administración tradicional de la información ha dependido históricamente de archivos físicos en papel, cuadernos de asistencia locales y libros contables manuales. Esta metodología convencional genera una fragmentación severa de los datos, donde la información personal de los alumnos, sus expedientes de admisión, el historial de calificaciones y los registros de pagos se encuentran dispersos en múltiples dependencias sin interconexión oportuna.")

    add_p("El Instituto de Educación Básica \"El Progreso\" administra una población estudiantil correspondiente al ciclo básico, abarcando los grados de primero, segundo y tercero básico. La acumulación progresiva de expedientes físicos en la secretaría del establecimiento incrementa la vulnerabilidad de los registros ante el deterioro material, el extravío de papelería oficial y la lentitud en la búsqueda de antecedentes académicos. Ante solicitudes de certificación de estudios o verificación de cumplimiento de requisitos de graduación, el personal administrativo debe invertir jornadas prolongadas en la revisión hoja por hoja de los libros físicos, limitando la capacidad de respuesta institucional.")

    add_p("En el ámbito financiero, la gestión manual de colegiaturas y cuotas operativas propicia la aparición de discrepancias entre los recibos emitidos y los saldos reales consolidados. La falta de un sistema automatizado de cuenta corriente impide que las autoridades del centro educativo dispongan de indicadores precisos sobre la morosidad, los ingresos efectivos y el estado de solvencia de cada estudiante en tiempo real. Esta situación dificulta la toma de decisiones administrativas y entorpece la planificación presupuestaria de la institución.")

    add_p("Asimismo, el proceso de registro de calificaciones por bloques académicos se ve afectado cuando los docentes entregan actas parciales en formatos físicos o carpetas desconectadas. La posterior transcripción manual de notas al sistema central genera un margen considerable de error humano, duplicación de esfuerzos y retrasos en la entrega de reportes de rendimiento académico a los padres de familia o tutores legales, erosionando la percepción de eficiencia institucional.")

    # plantear el problema
    add_h2("1.2 Plantear el problema")

    add_p("La ausencia de una herramienta tecnológica centralizada en el Instituto de Educación Básica \"El Progreso\" impacta negativamente en cuatro ejes funcionales prioritarios: la administración del expediente digital estudiantil, la evaluación académica por bloques, el control de la cuenta corriente financiera y la trazabilidad de la auditoría interna.")

    add_p("En primer lugar, con relación a los expedientes estudiantiles, el Ministerio de Educación de Guatemala exige la entrega y verificación estricta de cinco documentos obligatorios para oficializar la inscripción en el ciclo básico: certificado de nacimiento expedido por el Registro Nacional de las Personas con código único de identificación, fotocopia del documento personal de identificación del encargado legal, certificado de estudios del grado anterior, diploma de conclusión de educación primaria y la constancia de código personal del estudiante. En la práctica operativa actual, el seguimiento manual de esta papelería impide identificar con certeza cuáles expedientes se encuentran incompletos, lo que expone a la institución a sanciones administrativas durante las auditorías de supervisión escolar.")

    add_p("En segundo lugar, la gestión académica carece de mecanismos automatizados para consolidar la zona acumulada y los exámenes de bloque de cada asignatura. La calificación de las tareas, proyectos y evaluaciones parciales se procesa de forma aislada, lo que dificulta la detección temprana de estudiantes en riesgo de reprobación y complica la generación inmediata de cuadros de honor o listados de rendimiento. Además, no se dispone de un registro digital unificado de asistencias que permita vincular las ausencias con el desempeño académico del alumnado.")

    add_p("En tercer lugar, el flujo de caja e ingresos por conceptos de matrícula y colegiaturas mensuales experimenta inconsistencias debido a la falta de validación inmediata de los comprobantes de depósito o transferencias. La falta de integración entre el módulo de cobros y los expedientes académicos impide aplicar restricciones administrativas justificadas ante situaciones de insolvencia prolongada, o bien, genera cobros indebidos a tutores que ya han regularizado sus abonos pero cuyo registro no ha sido actualizado en la secretaría.")

    add_p("En cuarto lugar, la seguridad de la información institucional se encuentra comprometida por la inexistencia de registros inmutables de auditoría. Cualquier modificación en una nota o en un estado de cuenta realizada en archivos locales no deja huella de responsabilidad, imposibilitando rastrear qué usuario ejecutó un cambio, en qué fecha se realizó y cuál era el valor original antes de la modificación. Esta carencia de trazabilidad debilita la gobernanza de datos y expone al centro educativo a inconsistencias en la memoria histórica de sus registros.")

    # formular el problema
    add_h2("1.3 Formular el problema")

    add_p("Tomando como base la caracterización de la problemática expuesta y la necesidad imperiosa de modernización tecnológica en el establecimiento, se plantea la interrogante central que orienta la presente investigación:")

    add_p("¿De qué manera el diseño e implementación de un sistema web integral de gestión escolar ERP optimiza los procesos administrativos, el control financiero de cuentas por cobrar, la evaluación académica por bloques y la trazabilidad de los expedientes estudiantiles en el Instituto de Educación Básica \"El Progreso\"?", bold=True)

    # interrogantes de la investigacion
    add_h2("1.4 Interrogantes de la investigación")

    add_p("Para dar respuesta de manera estructurada al problema central formulado, se derivan las siguientes interrogantes específicas de investigación:")

    questions = [
        "¿Cuáles son los requerimientos normativos y funcionales del Ministerio de Educación de Guatemala que deben incorporarse en la arquitectura de datos para garantizar la validez de los expedientes estudiantiles diurnos del ciclo básico?",
        "¿De qué manera la implementación del patrón de herencia de datos personales y la integridad referencial estricta garantizan la consistencia y evitan la duplicidad de registros en la base de datos institucional?",
        "¿Cómo influye un mecanismo de autenticación multicriterio mediante código único de identificación y correo electrónico en la accesibilidad y seguridad del control de usuarios por roles?",
        "¿En qué medida el desarrollo de un módulo financiero de cuenta corriente reduce el tiempo de atención en secretaría y elimina las discrepancias entre los abonos efectuados y los saldos adeudados?",
        "¿De qué forma la automatización de la auditoría inmutable de cambios y el esquema de eliminación lógica preservan la historia institucional frente a modificaciones accidentales o no autorizadas?"
    ]

    for q in questions:
        add_p("• " + q, indent=True, space_after=4)

    # objetivos
    add_h2("1.5 Objetivos")

    # de la investigacion
    add_h3("1.5.1 De la investigación")
    add_p("Analizar, evaluar y sistematizar el impacto de la implementación de una plataforma web ERP de gestión escolar en la optimización operativa, la integridad de los datos y el cumplimiento regulatorio en centros educativos del nivel medio, tomando como unidad de estudio el Instituto de Educación Básica \"El Progreso\".")

    # generales
    add_h3("1.5.2 Generales")
    add_p("Desarrollar e implementar un sistema web integral de gestión escolar ERP para el Instituto de Educación Básica \"El Progreso\", que automatice la administración de expedientes estudiantiles, la evaluación académica por bloques, la cuenta corriente financiera y el control de personal e inventarios, garantizando la trazabilidad, la seguridad y el cumplimiento normativo del Ministerio de Educación de Guatemala.")

    # especificos
    add_h3("1.5.3 Específicos")
    
    objectives_spec = [
        "Diseñar un modelo de datos relacional robusto apoyado en el patrón de herencia supertipo/subtipo para datos personales y en principios de eliminación lógica con auditoría inmutable que resguarde los registros históricos de la institución.",
        "Construir un subsistema de registro de alumnos con verificación automatizada del expediente digital de cinco documentos normativos del Ministerio de Educación, emitiendo constancias oficiales de inscripción y credenciales de acceso.",
        "Implementar una estrategia de autenticación multicriterio que habilite el ingreso al sistema utilizando indistintamente el código único de identificación o el correo electrónico, delimitando permisos mediante control de acceso basado en roles.",
        "Desarrollar el módulo académico para la gestión de asignaturas, control de asistencia diaria y consolidación automatizada de notas de zona y exámene por bloques para la obtención de promedios finales.",
        "Automatizar la gestión financiera mediante un esquema de cuenta corriente que procese la generación de cargos, el registro de abonos y la emisión de reportes de solvencia económica con trazabilidad inmutable de transacciones."
    ]

    for spec in objectives_spec:
        add_p("1. " if spec == objectives_spec[0] else str(objectives_spec.index(spec)+1) + ". " + spec, indent=True, space_after=4)

    # hipotesis
    add_h2("1.6 Hipótesis")

    # general
    add_h3("1.6.1 Hipótesis General")
    add_p("La implementación de un sistema web integral de gestión escolar ERP en el Instituto de Educación Básica \"El Progreso\" incrementa de manera sustancial la eficiencia operativa, reduce los errores en la consolidación de calificaciones y cobranzas, y garantiza el cumplimiento normativo de los expedientes estudiantiles en comparación con los procedimientos de administración manual tradicionales.")

    add_p("Hipótesis Nula (H0): La implementación del sistema web integral de gestión escolar ERP no produce cambios significativos en la eficiencia operativa, la precisión del registro de notas ni en el cumplimiento normativo de expedientes en el Instituto de Educación Básica \"El Progreso\".", italic=True)

    # especificas
    add_h3("1.6.2 Hipótesis Específicas")

    h_spec = [
        "La validación automatizada de la papelería obligatoria mediante el módulo de expediente digital incrementa en un noventa por ciento la detección oportuna de documentos faltantes exigidos por las autoridades educativas antes del cierre del ciclo escolar.",
        "El módulo financiero de cuenta corriente reduce en un setenta por ciento el tiempo requerido para conciliar las boletas de depósito con los estados de cuenta de los alumnos, eliminando las diferencias de saldo reportadas por secretaría.",
        "La integración de un motor de auditoría inmutable disminuye en su totalidad la alteración no autorizada de notas de bloque y registros de pago, garantizando la inalterabilidad de la memoria histórica de la institución."
    ]

    for h in h_spec:
        add_p("• " + h, indent=True, space_after=4)

    # save output file
    doc.save(output_path)
    print(f"Document successfully created at: {output_path}")

if __name__ == "__main__":
    output_docx = os.path.join(r"c:\Users\Nelson\Desktop\Proyectos\IBACOOP_PROGRESO", "Documentacion_Proyecto_IBACOOP_PROGRESO.docx")
    create_apa7_document(output_docx)
