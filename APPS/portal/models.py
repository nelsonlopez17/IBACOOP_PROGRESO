"""
portal/models.py

Portal Web Institucional del Instituto "El Progreso" (IBACOOP).
Permite gestionar la publicación de contenidos, parámetros globales del portal,
fotografías vía URLs externas (Google Drive, Cloudinary u otros) y solicitudes de contacto.
"""
import re
from decimal import Decimal
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords
from APPS.core.models import ModeloAuditable
from APPS.core.validadores import validador_telefono_guatemala


class ConfiguracionPortal(ModeloAuditable):
    """
    Parámetros globales y de contacto del portal web institucional (Patrón Singleton).
    Permite al personal de Dirección y Secretaría controlar datos del instituto sin tocar código.
    """
    nombre_instituto = models.CharField(
        max_length=200,
        default='Instituto Básico por Cooperativa de Enseñanza "El Progreso"',
        verbose_name='Nombre oficial de la institución'
    )
    hero_titulo = models.CharField(
        max_length=200,
        default='Instituto Básico por Cooperativa de Enseñanza\nColonia El Progreso • Escuintla',
        verbose_name='Título principal de la portada (Hero)'
    )
    hero_descripcion = models.TextField(
        default='Formación integral para el Ciclo de Educación Básica en Escuintla, Guatemala. Impartimos educación de excelencia bajo el Currículo Nacional Base (CNB), valores éticos y principios cooperativos al alcance de las familias.',
        verbose_name='Descripción principal de la portada (Hero)'
    )
    mision = models.TextField(
        default='Formar integralmente a las y los estudiantes del Ciclo de Educación Básica mediante un modelo pedagógico de alta calidad científica, tecnológica y humanística, fundamentado en los valores cooperativos, para que egresen con capacidades que les permitan continuar con éxito su educación diversificada y aportar positivamente a la sociedad.',
        verbose_name='Misión institucional'
    )
    vision = models.TextField(
        default='Ser el instituto de educación básica por cooperativa referente en el departamento y a nivel nacional, reconocido por su excelencia académica, su permanente innovación tecnológica en las aulas y su sólida formación en principios éticos, ciudadanos y de liderazgo cooperativo.',
        verbose_name='Visión institucional'
    )

    # --- PLAN DE ESTUDIOS — CICLO BÁSICO ---
    plan_estudios_subtitulo = models.CharField(
        max_length=255,
        default='Enseñanza integral orientada al desarrollo de competencias cognitivas, humanísticas y tecnológicas.',
        verbose_name='Subtítulo de la sección Plan de Estudios'
    )
    descripcion_primero_basico = models.TextField(
        default='Etapa de transición y adaptación pedagógica. Nivelación en habilidades cuantitativas y de comprensión verbal.',
        verbose_name='Descripción de Primero Básico'
    )
    puntos_primero_basico = models.TextField(
        default='Matemáticas y Razonamiento Lógico\nComunicación y Lenguaje (L1 e Idioma Inglés)\nIniciación en Laboratorio Digital de Cómputo',
        verbose_name='Aspectos o materias clave de Primero Básico (un elemento por línea)'
    )
    descripcion_segundo_basico = models.TextField(
        default='Desarrollo del pensamiento crítico y experimental. Fortalecimiento del trabajo colaborativo y cooperativo.',
        verbose_name='Descripción de Segundo Básico'
    )
    puntos_segundo_basico = models.TextField(
        default='Ciencias Naturales y Experimentación\nCiencias Sociales y Ciudadanía\nEmprendimiento para la Productividad',
        verbose_name='Aspectos o materias clave de Segundo Básico (un elemento por línea)'
    )
    descripcion_tercero_basico = models.TextField(
        default='Culminación del ciclo y preparación sólida hacia el Nivel Diversificado y carreras técnicas o científicas.',
        verbose_name='Descripción de Tercero Básico'
    )
    puntos_tercero_basico = models.TextField(
        default='Álgebra, Geometría y Estadística\nOrientación Vocacional Especializada\nDiploma de Conclusión del Ciclo Básico',
        verbose_name='Aspectos o materias clave de Tercero Básico (un elemento por línea)'
    )

    # --- REQUISITOS DE INSCRIPCIÓN ---
    requisitos_subtitulo = models.TextField(
        default='Para formalizar la inscripción en Secretaría, es indispensable presentar el expediente físico completo para su debido registro:',
        verbose_name='Subtítulo o indicación general de requisitos'
    )
    requisitos_primero_basico = models.TextField(
        default='Certificado de Nacimiento reciente emitido por RENAP (CUI legible)\nDocumento Personal de Identificación (DPI) del Padre de Familia o Encargado\nCertificado original de 6to Grado de Primaria sellado por la dirección del centro educativo\nDiploma de conclusión de Primaria (original y copia para cotejo)\nConstancia de Código Personal del Estudiante registrada en sistema SIRE\n2 fotografías recientes tamaño cédula del estudiante',
        verbose_name='Requisitos para Primer Ingreso / Primero Básico (un requisito por línea)'
    )
    requisitos_traslados = models.TextField(
        default='Certificados oficiales de todos los grados previos aprobados (Primaria, 1ro o 2do Básico)\nCódigo Personal del Estudiante (SIRE) en estado liberado o transferido\nCertificado de Nacimiento emitido por RENAP (CUI legible)\nConstancia de solvencia económica emitida por el establecimiento de origen\nFotocopia de DPI de los padres de familia o encargados y datos de contacto vigentes',
        verbose_name='Requisitos para Traslados a 2do y 3ro Básico (un requisito por línea)'
    )
    lema = models.CharField(
        max_length=255,
        default='Formación integral, valores y principios cooperativos al alcance de las familias.',
        verbose_name='Lema o descripción corta'
    )
    telefono_principal = models.CharField(
        max_length=8,
        default='78881234',
        validators=[MinLengthValidator(8), validador_telefono_guatemala],
        verbose_name='Teléfono de planta'
    )
    telefono_whatsapp = models.CharField(
        max_length=8,
        default='50001234',
        validators=[MinLengthValidator(8), validador_telefono_guatemala],
        verbose_name='WhatsApp de atención e información'
    )
    correo_contacto = models.EmailField(
        default='informacion@ibacoopprogreso.edu.gt',
        verbose_name='Correo electrónico oficial'
    )
    direccion_fisica = models.CharField(
        max_length=255,
        default='Colonia El Progreso, Zona 3, Escuintla, Guatemala',
        verbose_name='Dirección física del instituto'
    )
    horario_atencion = models.CharField(
        max_length=150,
        default='Lunes a Viernes de 13:00 a 18:00 hrs',
        verbose_name='Horario de atención presencial'
    )
    jornada = models.CharField(
        max_length=100,
        default='Vespertina (13:00 a 18:00 hrs)',
        verbose_name='Jornada oficial'
    )
    cuota_inscripcion = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('150.00'),
        verbose_name='Cuota de inscripción (Q)'
    )
    cuota_mensual = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('100.00'),
        verbose_name='Cuota escolar mensual (Q)'
    )
    inscripciones_abiertas = models.BooleanField(
        default=True,
        verbose_name='¿Inscripciones abiertas?'
    )
    ciclo_escolar_activo = models.CharField(
        max_length=50,
        default='Ciclo Escolar 2026',
        verbose_name='Ciclo escolar de admisión'
    )
    mostrar_cintillo_alerta = models.BooleanField(
        default=False,
        verbose_name='¿Mostrar cintillo de aviso en portada?'
    )
    texto_cintillo_alerta = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Mensaje del cintillo de aviso'
    )
    tipo_cintillo_alerta = models.CharField(
        max_length=20,
        choices=[
            ('INFO', 'Informativo (Azul)'),
            ('AVISO', 'Aviso Importante (Ámbar)'),
            ('URGENTE', 'Urgente / Oficial (Rojo)'),
        ],
        default='AVISO',
        verbose_name='Nivel visual del cintillo'
    )
    enlace_cintillo = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Enlace opcional del cintillo (ej. /admisiones/)'
    )

    history = HistoricalRecords(verbose_name='Auditoría de Configuración del Portal')

    class Meta:
        verbose_name = 'Configuración del Portal Web'
        verbose_name_plural = 'Configuración del Portal Web'

    def __str__(self):
        return f"Configuración Portal — {self.nombre_instituto}"

    @property
    def link_whatsapp(self):
        """Retorna el enlace directo a la API de WhatsApp con código de país de Guatemala (+502)."""
        if self.telefono_whatsapp:
            return f"https://wa.me/502{self.telefono_whatsapp}"
        return "#"

    @property
    def lista_puntos_primero_basico(self):
        """Retorna la lista de aspectos o materias de Primero Básico separadas por salto de línea."""
        if not self.puntos_primero_basico:
            return []
        return [p.strip() for p in self.puntos_primero_basico.splitlines() if p.strip()]

    @property
    def lista_puntos_segundo_basico(self):
        """Retorna la lista de aspectos o materias de Segundo Básico separadas por salto de línea."""
        if not self.puntos_segundo_basico:
            return []
        return [p.strip() for p in self.puntos_segundo_basico.splitlines() if p.strip()]

    @property
    def lista_puntos_tercero_basico(self):
        """Retorna la lista de aspectos o materias de Tercero Básico separadas por salto de línea."""
        if not self.puntos_tercero_basico:
            return []
        return [p.strip() for p in self.puntos_tercero_basico.splitlines() if p.strip()]

    @property
    def lista_requisitos_primero_basico(self):
        """Retorna los requisitos de Primero Básico como lista."""
        if not self.requisitos_primero_basico:
            return []
        return [r.strip() for r in self.requisitos_primero_basico.splitlines() if r.strip()]

    @property
    def lista_requisitos_traslados(self):
        """Retorna los requisitos de traslados como lista."""
        if not self.requisitos_traslados:
            return []
        return [r.strip() for r in self.requisitos_traslados.splitlines() if r.strip()]

    @classmethod
    def get_solo(cls):
        """Devuelve la configuración activa o crea la configuración predeterminada si no existe."""
        config = cls.objects.first()
        if not config:
            config = cls.objects.create()
        return config


class CategoriaFotoChoices(models.TextChoices):
    ACTIVIDADES    = 'ACTIVIDADES',    'Actividades Académicas'
    INSTALACIONES  = 'INSTALACIONES',  'Instalaciones y Aulas'
    DEPORTES       = 'DEPORTES',       'Deportes y Convivencia'
    ACTOS_CIVICOS  = 'ACTOS_CIVICOS',  'Actos Cívicos y Culturales'
    GENERAL        = 'GENERAL',        'Comunidad Educativa'


class FotoGaleria(ModeloAuditable):
    """
    Registro de fotografías para la galería del portal institucional mediante enlaces externos.
    No almacena archivos binarios en el servidor ni en la base de datos, admitiendo URLs de
    Google Drive, OneDrive, Cloudinary, Imgur o cualquier servidor de imágenes.
    """
    titulo = models.CharField(
        max_length=150,
        verbose_name='Título de la fotografía'
    )
    descripcion = models.TextField(
        blank=True,
        max_length=500,
        verbose_name='Descripción o pie de foto'
    )
    url_imagen = models.URLField(
        max_length=1000,
        verbose_name='Enlace de la imagen (Google Drive u otro servicio externo)'
    )
    categoria = models.CharField(
        max_length=30,
        choices=CategoriaFotoChoices.choices,
        default=CategoriaFotoChoices.GENERAL,
        verbose_name='Categoría'
    )
    destacada_portada = models.BooleanField(
        default=False,
        verbose_name='¿Mostrar en galería de portada?'
    )
    orden = models.PositiveIntegerField(
        default=0,
        verbose_name='Orden de prioridad'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='¿Publicada en el portal?'
    )
    fecha = models.DateField(
        default=timezone.now,
        verbose_name='Fecha de la fotografía o actividad'
    )

    history = HistoricalRecords(verbose_name='Auditoría de Fotografía de Galería')

    class Meta:
        verbose_name = 'Fotografía de Galería'
        verbose_name_plural = 'Fotografías de Galería'
        ordering = ['orden', '-fecha', '-creado_en']

    def __str__(self):
        return f"{self.titulo} ({self.get_categoria_display()})"

    @property
    def url_directa(self):
        """
        Convierte enlaces compartidos de Google Drive en enlaces directos renderizables por el navegador.
        Si la URL no es de Google Drive, la devuelve sin modificar.
        """
        url = (self.url_imagen or '').strip()
        if not url:
            return ''

        # Detección de enlaces compartidos de Google Drive
        drive_file_match = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', url)
        if drive_file_match:
            file_id = drive_file_match.group(1)
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1200"

        drive_id_match = re.search(r'drive\.google\.com/[^?]+\?id=([a-zA-Z0-9_-]+)', url)
        if drive_id_match:
            file_id = drive_id_match.group(1)
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1200"

        return url


class SeccionPortalChoices(models.TextChoices):
    NOTICIAS    = 'NOTICIAS',    'Noticias'
    HISTORIA    = 'HISTORIA',    'Historia del Instituto'
    GALERIA     = 'GALERIA',     'Galería'
    OFERTA      = 'OFERTA',      'Oferta Educativa'
    COMUNICADOS = 'COMUNICADOS', 'Comunicados Oficiales'
    EVENTOS     = 'EVENTOS',     'Eventos'


class ContenidoWeb(ModeloAuditable):
    """Contenido editable y publicable en el portal institucional."""
    seccion = models.CharField(
        max_length=20,
        choices=SeccionPortalChoices.choices,
        verbose_name='Sección del portal'
    )
    titulo = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(3)],
        verbose_name='Título'
    )
    cuerpo = models.TextField(
        max_length=5000,
        verbose_name='Contenido / Cuerpo'
    )
    imagen_url = models.URLField(
        blank=True,
        max_length=1000,
        verbose_name='URL de imagen externa (Drive u otro)'
    )
    imagen_archivo = models.ImageField(
        upload_to='portal/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Imagen (archivo local)'
    )
    fecha_publicacion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de publicación'
    )
    publicado = models.BooleanField(
        default=True,
        verbose_name='¿Publicado?'
    )
    autor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='contenidos_web',
        verbose_name='Autor'
    )

    history = HistoricalRecords(verbose_name='Auditoría de Contenido Web')

    class Meta:
        verbose_name = 'Contenido Web'
        verbose_name_plural = 'Contenidos Web'
        ordering = ['-fecha_publicacion']

    def __str__(self):
        estado = '✓' if self.publicado else '✗'
        return f"[{self.get_seccion_display()}] {self.titulo} ({estado})"

    @property
    def url_directa_imagen(self):
        """Retorna la imagen subida en archivo o la URL externa adaptada para Google Drive."""
        if self.imagen_archivo:
            try:
                return self.imagen_archivo.url
            except Exception:
                pass
        url = (self.imagen_url or '').strip()
        if not url:
            return ''
        drive_file_match = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', url)
        if drive_file_match:
            file_id = drive_file_match.group(1)
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1200"
        return url


class SolicitudContacto(ModeloAuditable):
    """
    Solicitud de información o consulta enviada desde el formulario público del portal.
    Permite registrar mensajes y solicitudes de padres de familia o encargados interesados en el ciclo escolar.
    """
    nombre_remitente = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(3)],
        verbose_name='Nombre del remitente'
    )
    correo = models.EmailField(
        max_length=254,
        verbose_name='Correo electrónico'
    )
    telefono = models.CharField(
        max_length=8,
        validators=[MinLengthValidator(8), validador_telefono_guatemala],
        verbose_name='Teléfono / WhatsApp'
    )
    asunto = models.CharField(
        max_length=150,
        blank=True,
        default='Consulta de Admisión e Información',
        verbose_name='Asunto'
    )
    mensaje = models.TextField(
        max_length=1000,
        validators=[MinLengthValidator(10)],
        verbose_name='Mensaje o consulta'
    )
    atendido = models.BooleanField(
        default=False,
        verbose_name='¿Atendido?'
    )
    notas_seguimiento = models.TextField(
        max_length=500,
        blank=True,
        verbose_name='Notas de seguimiento interno'
    )
    atendido_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contactos_atendidos',
        verbose_name='Atendido por'
    )

    history = HistoricalRecords(verbose_name='Auditoría de Mensaje de Contacto')

    class Meta:
        verbose_name = 'Solicitud de Contacto'
        verbose_name_plural = 'Solicitudes de Contacto'
        ordering = ['-creado_en']

    def __str__(self):
        estado = '✓ Atendido' if self.atendido else '⏳ Pendiente'
        return f"{self.nombre_remitente} - {self.asunto} ({estado})"

    @property
    def link_whatsapp(self):
        """Enlace directo a WhatsApp del remitente con mensaje de saludo predeterminado."""
        if self.telefono:
            msg = f"Estimado/a {self.nombre_remitente}, le saludamos del Instituto El Progreso (IBACOOP) con relación a su consulta recibida."
            import urllib.parse
            return f"https://wa.me/502{self.telefono}?text={urllib.parse.quote(msg)}"
        return "#"
