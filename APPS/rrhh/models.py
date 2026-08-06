"""
rrhh/models.py

Recursos Humanos y Planilla/Nómina del Instituto El Progreso.
Implementa el subtipo Personal (Persona FK primary_key=True), Puesto, AsistenciaPersonal y Planilla.
"""
from django.db import models
from APPS.core.models import ModeloAuditable, Persona


class EstadoLaboralChoices(models.TextChoices):
    ACTIVO     = 'ACTIVO',     'Activo'
    BAJA       = 'BAJA',       'Baja temporal'
    RETIRADO   = 'RETIRADO',   'Retirado'
    SUSPENDIDO = 'SUSPENDIDO', 'Suspendido'


class EstadoAsistenciaChoices(models.TextChoices):
    PRESENTE   = 'PRESENTE',   'Presente'
    AUSENTE    = 'AUSENTE',    'Ausente'
    TARDANZA   = 'TARDANZA',   'Tardanza'
    PERMISO    = 'PERMISO',    'Con permiso'
    VACACIONES = 'VACACIONES', 'En vacaciones'


class MesChoices(models.IntegerChoices):
    ENERO      = 1,  'Enero'
    FEBRERO    = 2,  'Febrero'
    MARZO      = 3,  'Marzo'
    ABRIL      = 4,  'Abril'
    MAYO       = 5,  'Mayo'
    JUNIO      = 6,  'Junio'
    JULIO      = 7,  'Julio'
    AGOSTO     = 8,  'Agosto'
    SEPTIEMBRE = 9,  'Septiembre'
    OCTUBRE    = 10, 'Octubre'
    NOVIEMBRE  = 11, 'Noviembre'
    DICIEMBRE  = 12, 'Diciembre'


class Puesto(ModeloAuditable):
    """Representa un cargo o puesto laboral en la institución."""
    nombre_puesto = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del puesto'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )

    class Meta:
        verbose_name = 'Puesto'
        verbose_name_plural = 'Puestos'
        ordering = ['nombre_puesto']

    def __str__(self):
        return self.nombre_puesto


class Personal(ModeloAuditable):
    """
    Subtipo de Persona para colaboradores (docentes, administrativos, conserjes).
    La relación persona (OneToOneField) actúa como llave primaria.
    """
    persona = models.OneToOneField(
        Persona,
        on_delete=models.RESTRICT,
        primary_key=True,
        related_name='personal',
        verbose_name='Persona'
    )
    puesto = models.ForeignKey(
        Puesto,
        on_delete=models.RESTRICT,
        related_name='empleados',
        verbose_name='Puesto'
    )
    nit = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='NIT'
    )
    fecha_contratacion = models.DateField(
        verbose_name='Fecha de contratación'
    )
    estado_laboral = models.CharField(
        max_length=20,
        choices=EstadoLaboralChoices.choices,
        default=EstadoLaboralChoices.ACTIVO,
        verbose_name='Estado laboral'
    )
    salario_base_asignado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Salario base asignado (Q)'
    )

    # Ubicación del Contrato y Resguardo Físico en Secretaría
    numero_contrato_fisico = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='No. Contrato Físico',
        help_text='Número o correlativo del contrato laboral firmado en físico.'
    )
    ubicacion_expediente_fisico = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ubicación Físico (Archivador/Carpeta)',
        help_text='Ej. Archivador B-1, Carpeta 15 (Secretaría).'
    )
    contacto_emergencia_nombre = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nombre contacto de emergencia'
    )
    contacto_emergencia_telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono contacto de emergencia'
    )

    # Checklist Papelería Obligatoria Nivel Medio (Guatemala)
    doc_dpi_personal = models.BooleanField(
        default=False,
        verbose_name='Fotocopia DPI / CUI (RENAP)'
    )
    doc_nit_sat = models.BooleanField(
        default=False,
        verbose_name='Constancia de NIT (RTU SAT)'
    )
    doc_titulo_academico = models.BooleanField(
        default=False,
        verbose_name='Fotocopia Título Académico / Cédula Docente'
    )
    doc_colegiado_activo = models.BooleanField(
        default=False,
        verbose_name='Constancia Colegiado Activo / Registro MINEDUC'
    )
    doc_antecedentes_penales = models.BooleanField(
        default=False,
        verbose_name='Antecedentes Penales (Vigentes)'
    )
    doc_antecedentes_policiales = models.BooleanField(
        default=False,
        verbose_name='Antecedentes Policiales (Vigentes)'
    )
    doc_contrato_fisico = models.BooleanField(
        default=False,
        verbose_name='Contrato Físico Firmado'
    )
    doc_tarjeta_salud = models.BooleanField(
        default=False,
        verbose_name='Tarjeta de Salud / Sanidad'
    )

    class Meta:
        verbose_name = 'Personal'
        verbose_name_plural = 'Personal'
        ordering = ['persona__apellidos', 'persona__nombres']

    def __str__(self):
        return f"{self.persona.nombre_completo} - {self.puesto.nombre_puesto}"

    @property
    def expediente_completo(self):
        """Indica si se entregaron los documentos obligatorios principales."""
        return all([
            self.doc_dpi_personal,
            self.doc_nit_sat,
            self.doc_titulo_academico,
            self.doc_antecedentes_penales,
            self.doc_antecedentes_policiales,
            self.doc_contrato_fisico
        ])

    @property
    def documentos_entregados_count(self):
        """Retorna la cantidad de documentos entregados de la lista (0 a 8)."""
        docs = [
            self.doc_dpi_personal,
            self.doc_nit_sat,
            self.doc_titulo_academico,
            self.doc_colegiado_activo,
            self.doc_antecedentes_penales,
            self.doc_antecedentes_policiales,
            self.doc_contrato_fisico,
            self.doc_tarjeta_salud
        ]
        return sum(1 for d in docs if d)

    @property
    def porcentaje_expediente(self):
        """Retorna el porcentaje de papelería física completada (0 a 100)."""
        return int((self.documentos_entregados_count / 8) * 100)



class AsistenciaPersonal(ModeloAuditable):
    """Registro diario de asistencia del personal."""
    personal = models.ForeignKey(
        Personal,
        on_delete=models.RESTRICT,
        related_name='asistencias',
        verbose_name='Personal'
    )
    fecha = models.DateField(
        verbose_name='Fecha'
    )
    hora_entrada = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de entrada'
    )
    hora_salida = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de salida'
    )
    estado_asistencia = models.CharField(
        max_length=20,
        choices=EstadoAsistenciaChoices.choices,
        default=EstadoAsistenciaChoices.PRESENTE,
        verbose_name='Estado de asistencia'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )

    class Meta:
        verbose_name = 'Asistencia de Personal'
        verbose_name_plural = 'Asistencias de Personal'
        unique_together = [['personal', 'fecha']]
        ordering = ['-fecha', 'personal']

    def __str__(self):
        return f"{self.personal.persona.nombre_completo} - {self.fecha} ({self.get_estado_asistencia_display()})"


class Planilla(ModeloAuditable):
    """Registro de pago de planilla mensual de personal."""
    personal = models.ForeignKey(
        Personal,
        on_delete=models.RESTRICT,
        related_name='planillas',
        verbose_name='Personal'
    )
    ciclo_escolar = models.ForeignKey(
        'academico.CicloEscolar',
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='planillas',
        verbose_name='Ciclo Escolar'
    )
    mes_pagado = models.IntegerField(
        choices=MesChoices.choices,
        verbose_name='Mes pagado'
    )
    bonificaciones = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Bonificaciones (Q)'
    )
    descuentos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Descuentos (Q)'
    )
    total_pagar = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Total a pagar (Q)'
    )
    comprobante_pdf = models.FileField(
        upload_to='planillas/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Comprobante PDF'
    )
    fecha_pago = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de pago'
    )
    pagado = models.BooleanField(
        default=False,
        verbose_name='¿Pagado?'
    )

    class Meta:
        verbose_name = 'Planilla'
        verbose_name_plural = 'Planillas'
        unique_together = [['personal', 'mes_pagado', 'ciclo_escolar']]
        ordering = ['-mes_pagado']

    def __str__(self):
        return f"Planilla {self.get_mes_pagado_display()} - {self.personal.persona.nombre_completo} (Q{self.total_pagar})"
