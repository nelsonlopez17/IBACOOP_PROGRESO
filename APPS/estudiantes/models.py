"""
estudiantes/models.py

Gestión de Estudiantes y sus Encargados.
Todos los modelos heredan de ModeloAuditable para garantizar
auditoría y eliminación lógica (soft delete).
"""
from django.db import models
from APPS.core.models import ModeloAuditable


class Estudiante(ModeloAuditable):
    """
    Representa a un estudiante inscrito en el instituto.

    Cada estudiante tiene un Usuario del sistema asociado (OneToOne)
    para poder acceder al portal con credenciales propias.
    El código MINEDUC es el identificador oficial emitido por el Ministerio
    de Educación de Guatemala.
    """
    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.RESTRICT,
        related_name='estudiante',
        verbose_name='Usuario del sistema',
        help_text='Cuenta de acceso al sistema para el estudiante.',
    )
    codigo_mineduc = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código MINEDUC',
        help_text='Código único asignado por el MINEDUC.',
    )
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    fecha_nacimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de nacimiento',
    )
    genero = models.CharField(
        max_length=1,
        choices=[('M', 'Masculino'), ('F', 'Femenino')],
        blank=True,
        verbose_name='Género',
    )
    direccion = models.TextField(blank=True, verbose_name='Dirección')
    estado_activo = models.BooleanField(
        default=True,
        verbose_name='Estudiante activo',
        help_text='Desactivar si el estudiante se retiró del instituto.',
    )

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} ({self.codigo_mineduc})"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"


class Encargado(ModeloAuditable):
    """
    Representa al padre, madre o tutor legal de un estudiante.

    El campo `usuario` es opcional (null=True) ya que no todos los encargados
    tendrán acceso al portal web del sistema.
    El DPI (Documento Personal de Identificación) es el documento de identidad
    oficial en Guatemala.
    """
    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='encargado',
        verbose_name='Usuario del sistema',
        help_text='Cuenta de acceso al portal para el encargado (opcional).',
    )
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    dpi = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='DPI',
        help_text='Documento Personal de Identificación (13 dígitos).',
    )
    telefono_contacto = models.CharField(
        max_length=15,
        verbose_name='Teléfono de contacto',
    )
    telefono_secundario = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='Teléfono secundario',
    )
    correo = models.EmailField(
        blank=True,
        verbose_name='Correo electrónico',
    )
    ocupacion = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ocupación',
    )

    class Meta:
        verbose_name = 'Encargado'
        verbose_name_plural = 'Encargados'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} (DPI: {self.dpi})"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"


class EstudianteEncargado(ModeloAuditable):
    """
    Tabla pivote que relaciona Estudiantes con sus Encargados.

    Permite que un estudiante tenga múltiples encargados (ej. padre y madre)
    y que un encargado pueda estar a cargo de múltiples estudiantes (hermanos).
    El campo `es_contacto_principal` marca al encargado prioritario para
    comunicaciones y citaciones.
    """
    PARENTESCO_CHOICES = [
        ('PADRE',   'Padre'),
        ('MADRE',   'Madre'),
        ('ABUELO',  'Abuelo/a'),
        ('TIO',     'Tío/a'),
        ('HERMANO', 'Hermano/a'),
        ('TUTOR',   'Tutor Legal'),
        ('OTRO',    'Otro'),
    ]

    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.RESTRICT,
        related_name='encargados',
        verbose_name='Estudiante',
    )
    encargado = models.ForeignKey(
        Encargado,
        on_delete=models.RESTRICT,
        related_name='estudiantes',
        verbose_name='Encargado',
    )
    parentesco = models.CharField(
        max_length=20,
        choices=PARENTESCO_CHOICES,
        verbose_name='Parentesco',
    )
    es_contacto_principal = models.BooleanField(
        default=False,
        verbose_name='¿Es contacto principal?',
        help_text='Solo un encargado puede ser el contacto principal.',
    )

    class Meta:
        verbose_name = 'Relación Estudiante-Encargado'
        verbose_name_plural = 'Relaciones Estudiante-Encargado'
        unique_together = [['estudiante', 'encargado']]

    def __str__(self):
        return (
            f"{self.estudiante} — {self.encargado} "
            f"({self.get_parentesco_display()})"
        )
