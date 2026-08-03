"""
portal/models.py

Portal Web Institucional del Instituto El Progreso.
Permite gestionar la publicación de contenidos institucionales.
"""
from django.db import models
from APPS.core.models import ModeloAuditable


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
        verbose_name='Título'
    )
    cuerpo = models.TextField(
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
