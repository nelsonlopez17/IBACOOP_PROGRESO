"""
estudiantes/models.py

Gestión de Estudiantes, Encargados y sus relaciones de parentesco.
Implementa el patrón Subtipo en Estudiante y Encargado con OneToOneField hacia Persona (primary_key=True).
"""
from django.db import models
from APPS.core.models import ModeloAuditable, Persona


class GeneroChoices(models.TextChoices):
    MASCULINO = 'M', 'Masculino'
    FEMENINO  = 'F', 'Femenino'


class ParentescoChoices(models.TextChoices):
    PADRE   = 'PADRE',   'Padre'
    MADRE   = 'MADRE',   'Madre'
    ABUELO  = 'ABUELO',  'Abuelo/a'
    TIO     = 'TIO',     'Tío/a'
    HERMANO = 'HERMANO', 'Hermano/a'
    TUTOR   = 'TUTOR',   'Tutor Legal'
    OTRO    = 'OTRO',    'Otro'


class Estudiante(ModeloAuditable):
    """
    Subtipo de Persona para representar a los estudiantes matriculados.
    La relación persona (OneToOneField) actúa como llave primaria.
    """
    persona = models.OneToOneField(
        Persona,
        on_delete=models.RESTRICT,
        primary_key=True,
        related_name='estudiante',
        verbose_name='Persona'
    )
    codigo_mineduc = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código MINEDUC',
        help_text='Código único otorgado por el MINEDUC.'
    )
    genero = models.CharField(
        max_length=1,
        choices=GeneroChoices.choices,
        verbose_name='Género'
    )
    estado_activo = models.BooleanField(
        default=True,
        verbose_name='Estudiante activo',
        help_text='Indica si el estudiante se encuentra activo en el instituto.'
    )

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'

    def __str__(self):
        return f"{self.persona.nombre_completo} (MINEDUC: {self.codigo_mineduc})"


class Encargado(ModeloAuditable):
    """
    Subtipo de Persona para representar a los padres o tutores legales.
    La relación persona (OneToOneField) actúa como llave primaria.
    """
    persona = models.OneToOneField(
        Persona,
        on_delete=models.RESTRICT,
        primary_key=True,
        related_name='encargado',
        verbose_name='Persona'
    )
    ocupacion = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ocupación'
    )

    class Meta:
        verbose_name = 'Encargado'
        verbose_name_plural = 'Encargados'

    def __str__(self):
        return f"{self.persona.nombre_completo} (Ocupación: {self.ocupacion or 'N/A'})"


class EstudianteEncargado(ModeloAuditable):
    """
    Tabla pivote N:M entre Estudiantes y Encargados especificando parentesco y contacto principal.
    """
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.RESTRICT,
        related_name='encargados',
        verbose_name='Estudiante'
    )
    encargado = models.ForeignKey(
        Encargado,
        on_delete=models.RESTRICT,
        related_name='estudiantes',
        verbose_name='Encargado'
    )
    parentesco = models.CharField(
        max_length=20,
        choices=ParentescoChoices.choices,
        verbose_name='Parentesco'
    )
    es_contacto_principal = models.BooleanField(
        default=False,
        verbose_name='¿Es contacto principal?'
    )

    class Meta:
        verbose_name = 'Relación Estudiante-Encargado'
        verbose_name_plural = 'Relaciones Estudiante-Encargado'
        unique_together = [['estudiante', 'encargado']]

    def __str__(self):
        return f"{self.estudiante.persona.nombre_completo} - {self.encargado.persona.nombre_completo} ({self.get_parentesco_display()})"
