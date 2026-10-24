"""
portal/models.py

Portal Web Institucional del Instituto El Progreso.
Permite gestionar la publicación de contenidos institucionales.
"""
from django.core.validators import MinLengthValidator
from django.db import models
from APPS.core.models import ModeloAuditable
from APPS.core.validadores import validador_telefono_guatemala


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
        verbose_name='URL de imagen externa'
    )
    imagen_archivo = models.ImageField(
        upload_to='portal/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Imagen (archivo)'
    )
    fecha_publicacion = models.DateTimeField(
        verbose_name='Fecha de publicación'
    )
    publicado = models.BooleanField(
        default=False,
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

    class Meta:
        verbose_name = 'Contenido Web'
        verbose_name_plural = 'Contenidos Web'
        ordering = ['-fecha_publicacion']

    def __str__(self):
        estado = '✓' if self.publicado else '✗'
        return f"[{self.get_seccion_display()}] {self.titulo} ({estado})"


class SolicitudContacto(ModeloAuditable):
    """
    Solicitud de información o consulta enviada desde el formulario público del portal.
    Permite registrar prospectos y padres de familia o encargados interesados en el ciclo escolar.
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

    class Meta:
        verbose_name = 'Solicitud de Contacto'
        verbose_name_plural = 'Solicitudes de Contacto'
        ordering = ['-creado_en']

    def __str__(self):
        estado = '✓ Atendido' if self.atendido else '⏳ Pendiente'
        return f"{self.nombre_remitente} - {self.asunto} ({estado})"

