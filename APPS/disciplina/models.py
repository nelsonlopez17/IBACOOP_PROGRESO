"""
APPS/disciplina/models.py

Modelos de datos para el control de disciplina escolar, bitácora de incidencias
y citaciones a padres de familia conforme a la Normativa de Convivencia Pacífica
y Disciplina para una Cultura de Paz en los Centros Educativos (Acuerdo Ministerial 01-2011 del MINEDUC).
"""
from django.core.validators import MinLengthValidator
from django.db import models
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords

from APPS.core.models import ModeloAuditable
from APPS.estudiantes.models import Estudiante
from APPS.academico.models import CicloEscolar


class TipoFaltaChoices(models.TextChoices):
    LEVE = 'LEVE', 'Falta Leve'
    GRAVE = 'GRAVE', 'Falta Grave'
    MUY_GRAVE = 'MUY_GRAVE', 'Falta Muy Grave'


class CategoriaFaltaChoices(models.TextChoices):
    IMPUNTUALIDAD = 'IMPUNTUALIDAD', 'Impuntualidad reiterada'
    UNIFORME = 'UNIFORME', 'Incumplimiento de uniforme o presentación'
    DESATENCION = 'DESATENCION', 'Desatención o interrupción de clases'
    DISPOSITIVO = 'DISPOSITIVO', 'Uso indebido de celular o dispositivos'
    DESHONESTIDAD = 'DESHONESTIDAD', 'Deshonestidad académica (Copia, Plagio)'
    FALTA_RESPETO = 'FALTA_RESPETO', 'Falta de respeto a compañeros o docentes'
    AGRESION_VERBAL = 'AGRESION_VERBAL', 'Agresión verbal / Lenguaje inapropiado'
    AGRESION_FISICA = 'AGRESION_FISICA', 'Agresión física o riña'
    DANIO_BIENES = 'DANIO_BIENES', 'Daño a instalaciones o bienes de la cooperativa'
    ACOSO = 'ACOSO', 'Acoso escolar / Bullying / Intimidación'
    SUSTRACCION = 'SUSTRACCION', 'Sustracción de pertenencias ajenas'
    OTRO = 'OTRO', 'Otra falta contra la convivencia pacífica'


class EstadoCitacionChoices(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente de Atención'
    ATENDIDA = 'ATENDIDA', 'Atendida / Compromiso Firmado'
    NO_ASISTIO = 'NO_ASISTIO', 'No Asistió el Encargado'
    REPROGRAMADA = 'REPROGRAMADA', 'Reprogramada'


class IncidenteDisciplinario(ModeloAuditable):
    """
    Registro formal de un incidente disciplinario de acuerdo con el marco del MINEDUC (Acuerdo 01-2011).
    Garantiza el debido proceso, derecho de audiencia del estudiante y medidas formativas.
    """
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='incidentes_disciplinarios',
        verbose_name='Estudiante',
    )
    ciclo_escolar = models.ForeignKey(
        CicloEscolar,
        on_delete=models.PROTECT,
        related_name='incidentes_disciplinarios',
        verbose_name='Ciclo Escolar',
    )
    reportado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidentes_reportados',
        verbose_name='Reportado por',
    )
    fecha = models.DateField(
        default=timezone.now,
        verbose_name='Fecha del incidente',
    )
    hora = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora del incidente',
    )
    lugar = models.CharField(
        max_length=150,
        default='Aula de clases',
        validators=[MinLengthValidator(3)],
        verbose_name='Lugar de los hechos',
        help_text='Ej: Aula 102, Patio Central, Laboratorio de Computación, Salida.',
    )
    tipo_falta = models.CharField(
        max_length=15,
        choices=TipoFaltaChoices.choices,
        default=TipoFaltaChoices.LEVE,
        verbose_name='Clasificación de la Falta (MINEDUC)',
    )
    categoria = models.CharField(
        max_length=25,
        choices=CategoriaFaltaChoices.choices,
        default=CategoriaFaltaChoices.DESATENCION,
        verbose_name='Categoría del Incidente',
    )
    descripcion_hechos = models.TextField(
        max_length=1000,
        validators=[MinLengthValidator(10)],
        verbose_name='Descripción objetiva de los hechos',
        help_text='Detalle claro y circunstanciado de lo ocurrido.',
    )
    descargo_estudiante = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name='Declaración o descargo del estudiante',
        help_text='Derecho de audiencia y defensa del estudiante conforme al Acuerdo 01-2011.',
    )
    medida_formativa = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name='Acción pedagógica o medida formativa',
        help_text='Amonestación verbal, trabajo formativo reflexivo, labor comunitaria escolar, etc.',
    )
    requiere_citacion = models.BooleanField(
        default=False,
        verbose_name='¿Requiere citación al padre de familia o encargado?',
    )
    esta_resuelto = models.BooleanField(
        default=False,
        verbose_name='¿Caso resuelto y cerrado?',
    )

    history = HistoricalRecords(verbose_name='Auditoría de Incidente')

    class Meta:
        db_table = 'disciplina_incidentedisciplinario'
        verbose_name = 'Falta Disciplinaria'
        verbose_name_plural = 'Faltas Disciplinarias'
        ordering = ['-fecha', '-creado_en']

    def __str__(self):
        return f"[{self.get_tipo_falta_display()}] {self.estudiante.persona.nombre_completo} ({self.fecha})"

    @property
    def badge_severidad(self):
        if self.tipo_falta == TipoFaltaChoices.LEVE:
            return {'label': 'Falta Leve', 'class': 'bg-amber-50 text-amber-700 border-amber-300'}
        elif self.tipo_falta == TipoFaltaChoices.GRAVE:
            return {'label': 'Falta Grave', 'class': 'bg-orange-50 text-orange-700 border-orange-300'}
        elif self.tipo_falta == TipoFaltaChoices.MUY_GRAVE:
            return {'label': 'Falta Muy Grave', 'class': 'bg-rose-50 text-rose-700 border-rose-300'}
        return {'label': self.tipo_falta, 'class': 'bg-slate-50 text-slate-700 border-slate-300'}


# alias para compatibilidad con llamadas previas
IncidenteConductual = IncidenteDisciplinario


class CitacionPadre(ModeloAuditable):
    """
    Citatorio oficial generado para comparecencia del padre de familia o encargado ante Dirección o Comisión de Disciplina.
    """
    incidente = models.OneToOneField(
        IncidenteDisciplinario,
        on_delete=models.CASCADE,
        related_name='citacion',
        verbose_name='Incidente Disciplinario',
    )
    fecha_hora_citacion = models.DateTimeField(
        verbose_name='Fecha y hora programada',
    )
    motivo_citacion = models.CharField(
        max_length=255,
        validators=[MinLengthValidator(5)],
        verbose_name='Motivo formal de la citación',
    )
    lugar = models.CharField(
        max_length=150,
        default='Dirección / Coordinación Pedagógica',
        validators=[MinLengthValidator(3)],
        verbose_name='Lugar de reunión',
    )
    atendido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citaciones_atendidas',
        verbose_name='Atendido por',
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoCitacionChoices.choices,
        default=EstadoCitacionChoices.PENDIENTE,
        verbose_name='Estado de la citación',
    )
    acuerdos_alcanzados = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name='Acuerdos de convivencia y compromisos asumidos',
        help_text='Compromisos mutuos firmados por el padre de familia y el estudiante.',
    )
    observaciones_seguimiento = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name='Observaciones de seguimiento',
    )
    notificacion_enviada = models.BooleanField(
        default=False,
        verbose_name='¿Notificación entregada al encargado?',
    )

    history = HistoricalRecords(verbose_name='Auditoría de Citación')

    class Meta:
        db_table = 'disciplina_citacionpadre'
        verbose_name = 'Citación a Padre de Familia'
        verbose_name_plural = 'Citaciones a Padres de Familia'
        ordering = ['-fecha_hora_citacion']

    def __str__(self):
        fecha_local = timezone.localtime(self.fecha_hora_citacion) if timezone.is_aware(self.fecha_hora_citacion) else self.fecha_hora_citacion
        return f"Citación #{self.id} - {self.incidente.estudiante.persona.nombre_completo} ({fecha_local.strftime('%d/%m/%Y %H:%M')})"
