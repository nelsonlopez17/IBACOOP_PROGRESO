"""
portal/models.py

Portal Web Institucional del Instituto El Progreso.

Permite gestionar el contenido público del sitio web del instituto:
noticias, historia institucional, galería de fotos y oferta educativa.
"""
from django.db import models

from APPS.core.models import ModeloAuditable


class ContenidoWeb(ModeloAuditable):
    """
    Representa un contenido publicable en el portal web del instituto.

    El campo `seccion` determina en qué área del sitio aparecerá el contenido.
    El campo `publicado` actúa como un borrador: el contenido puede existir
    sin estar visible en el portal hasta que publicado=True.

    FK Autor usa SET_NULL (no RESTRICT): si un usuario es desactivado,
    sus contenidos permanecen y simplemente quedan sin autor asignado.
    """
    SECCION_CHOICES = [
        ('NOTICIAS',     'Noticias'),
        ('HISTORIA',     'Historia del Instituto'),
        ('GALERIA',      'Galería'),
        ('OFERTA',       'Oferta Educativa'),
        ('COMUNICADOS',  'Comunicados Oficiales'),
        ('EVENTOS',      'Eventos'),
    ]

    seccion = models.CharField(
        max_length=20,
        choices=SECCION_CHOICES,
        verbose_name='Sección del portal',
    )
    titulo = models.CharField(max_length=200, verbose_name='Título')
    cuerpo = models.TextField(verbose_name='Contenido / Cuerpo')
    imagen_url = models.URLField(
        blank=True,
        verbose_name='URL de imagen externa',
        help_text='URL de una imagen externa. Alternativa a subir un archivo.',
    )
    imagen_archivo = models.ImageField(
        upload_to='portal/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Imagen (archivo)',
        help_text='Suba una imagen directamente. Tiene prioridad sobre imagen_url.',
    )
    fecha_publicacion = models.DateTimeField(
        verbose_name='Fecha de publicación',
    )
    publicado = models.BooleanField(
        default=False,
        verbose_name='¿Publicado en el portal?',
        help_text='Solo los contenidos publicados son visibles en el sitio web.',
    )
    # SET_NULL: el contenido permanece si el autor es dado de baja
    autor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contenidos_web',
        verbose_name='Autor',
    )

    class Meta:
        verbose_name = 'Contenido Web'
        verbose_name_plural = 'Contenidos Web'
        ordering = ['-fecha_publicacion']

    def __str__(self):
        estado = '✓' if self.publicado else '✗'
        return f"[{self.get_seccion_display()}] {self.titulo} {estado}"
