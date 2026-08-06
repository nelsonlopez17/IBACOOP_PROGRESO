"""
estudiantes/models.py

Gestión de Estudiantes, Encargados y sus relaciones de parentesco.
Implementa el patrón Subtipo en Estudiante y Encargado con OneToOneField hacia Persona (primary_key=True).
"""
from django.db import models
from APPS.core.models import ModeloAuditable, Persona


class ParentescoChoices(models.TextChoices):
    PADRE   = 'PADRE',   'Padre'
    MADRE   = 'MADRE',   'Madre'
    ABUELO  = 'ABUELO',  'Abuelo/a'
    TIO     = 'TIO',     'Tío/a'
    HERMANO = 'HERMANO', 'Hermano/a'
    TUTOR   = 'TUTOR',   'Tutor Legal'
    OTRO    = 'OTRO',    'Otro'


class EstadoEstudianteChoices(models.TextChoices):
    ACTIVO     = 'ACTIVO',     'Activo'
    RETIRADO   = 'RETIRADO',   'Retirado'
    GRADUADO   = 'GRADUADO',   'Graduado'
    SUSPENDIDO = 'SUSPENDIDO', 'Suspendido'


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
    estado_estudiante = models.CharField(
        max_length=20,
        choices=EstadoEstudianteChoices.choices,
        default=EstadoEstudianteChoices.ACTIVO,
        verbose_name='Estado académico'
    )
    encargado = models.ForeignKey(
        'Encargado',
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='estudiantes',
        verbose_name='Encargado / Tutor Legal'
    )
    nombre_padre = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nombre del padre'
    )
    telefono_padre = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono del padre'
    )
    nombre_madre = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nombre de la madre'
    )
    telefono_madre = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono de la madre'
    )
    historial_medico = models.TextField(
        blank=True,
        verbose_name='Historial médico',
        help_text='Información médica relevante, alergias, afecciones, etc.'
    )
    # Checklist Papelería Oficial MINEDUC (5 Documentos Obligatorios)
    doc_cert_nacimiento_renap = models.BooleanField(
        default=False,
        verbose_name='Certificado de Nacimiento RENAP'
    )
    doc_dpi_encargado = models.BooleanField(
        default=False,
        verbose_name='Fotocopia DPI Encargado'
    )
    doc_certificado_grado_anterior = models.BooleanField(
        default=False,
        verbose_name='Certificado del Grado Anterior'
    )
    doc_diploma_primaria = models.BooleanField(
        default=False,
        verbose_name='Diploma de Primaria'
    )
    doc_codigo_mineduc = models.BooleanField(
        default=False,
        verbose_name='Constancia Código Personal MINEDUC'
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

    @property
    def expediente_completo(self):
        """Indica si entregó los 5 documentos obligatorios del MINEDUC."""
        return all([
            self.doc_cert_nacimiento_renap,
            self.doc_dpi_encargado,
            self.doc_certificado_grado_anterior,
            self.doc_diploma_primaria,
            self.doc_codigo_mineduc
        ])

    @property
    def documentos_entregados_count(self):
        """Retorna el número de documentos obligatorios entregados (0 a 5)."""
        docs = [
            self.doc_cert_nacimiento_renap,
            self.doc_dpi_encargado,
            self.doc_certificado_grado_anterior,
            self.doc_diploma_primaria,
            self.doc_codigo_mineduc
        ]
        return sum(1 for d in docs if d)

    @property
    def porcentaje_expediente(self):
        """Retorna el porcentaje de papelería física completada (0 a 100)."""
        return int((self.documentos_entregados_count / 5) * 100)



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
    lugar_de_trabajo = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Lugar de trabajo'
    )

    class Meta:
        verbose_name = 'Encargado'
        verbose_name_plural = 'Encargados'

    def __str__(self):
        return f"{self.persona.nombre_completo} (Lugar de trabajo: {self.lugar_de_trabajo or 'N/A'})"


class EstudianteEncargado(ModeloAuditable):
    """
    Tabla pivote N:M entre Estudiantes y Encargados especificando parentesco y contacto principal.
    """
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.RESTRICT,
        related_name='encargados_rel',
        verbose_name='Estudiante'
    )
    encargado = models.ForeignKey(
        Encargado,
        on_delete=models.RESTRICT,
        related_name='estudiantes_rel',
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

