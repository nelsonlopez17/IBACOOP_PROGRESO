"""
rrhh/models.py

Recursos Humanos y Nómina del Instituto El Progreso.
Cubre la gestión de puestos, personal, control de asistencia y generación de planillas.
Todos los modelos heredan de ModeloAuditable para auditoría y soft delete.
"""
from django.db import models
from APPS.core.models import ModeloAuditable


class Puesto(ModeloAuditable):
    """
    Representa un puesto o cargo dentro de la institución.
    Ejemplos: Docente de Matemáticas, Director, Contador, Conserje.
    """
    nombre_puesto = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del puesto',
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
    )

    class Meta:
        verbose_name = 'Puesto'
        verbose_name_plural = 'Puestos'
        ordering = ['nombre_puesto']

    def __str__(self):
        return self.nombre_puesto


class Personal(ModeloAuditable):
    """
    Representa a un miembro del personal del instituto (docente, administrativo, etc.).

    Cada miembro del personal tiene un Usuario del sistema asociado para acceso.
    RESTRICT en FK Usuario y Puesto: no se puede desactivar un puesto si tiene
    personal activo, y no se puede eliminar un usuario si tiene registro de personal.
    """
    ESTADO_LABORAL_CHOICES = [
        ('ACTIVO',    'Activo'),
        ('BAJA',      'Baja temporal'),
        ('RETIRADO',  'Retirado'),
        ('SUSPENDIDO','Suspendido'),
    ]

    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.RESTRICT,
        related_name='personal',
        verbose_name='Usuario del sistema',
    )
    puesto = models.ForeignKey(
        Puesto,
        on_delete=models.RESTRICT,
        related_name='empleados',
        verbose_name='Puesto',
    )
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    dpi = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='DPI',
    )
    nit = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='NIT',
    )
    fecha_contratacion = models.DateField(verbose_name='Fecha de contratación')
    estado_laboral = models.CharField(
        max_length=20,
        choices=ESTADO_LABORAL_CHOICES,
        default='ACTIVO',
        verbose_name='Estado laboral',
    )
    salario_base_asignado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Salario base asignado (Q)',
    )

    class Meta:
        verbose_name = 'Personal'
        verbose_name_plural = 'Personal'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} — {self.puesto}"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"


class AsistenciaPersonal(ModeloAuditable):
    """
    Registro diario de asistencia del personal.

    La restricción unique_together garantiza un único registro por persona por día.
    RESTRICT en FK Personal: no se puede eliminar personal con registros de asistencia.
    """
    ESTADO_CHOICES = [
        ('PRESENTE',  'Presente'),
        ('AUSENTE',   'Ausente'),
        ('TARDANZA',  'Tardanza'),
        ('PERMISO',   'Con permiso'),
        ('VACACIONES','En vacaciones'),
    ]

    personal = models.ForeignKey(
        Personal,
        on_delete=models.RESTRICT,
        related_name='asistencias',
        verbose_name='Personal',
    )
    fecha = models.DateField(verbose_name='Fecha')
    hora_entrada = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de entrada',
    )
    hora_salida = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de salida',
    )
    estado_asistencia = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PRESENTE',
        verbose_name='Estado de asistencia',
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
    )

    class Meta:
        verbose_name = 'Asistencia de Personal'
        verbose_name_plural = 'Asistencias de Personal'
        unique_together = [['personal', 'fecha']]
        ordering = ['-fecha', 'personal']

    def __str__(self):
        return (
            f"{self.personal} — {self.fecha} "
            f"({self.get_estado_asistencia_display()})"
        )


class Planilla(ModeloAuditable):
    """
    Registro de pago mensual (planilla) de un miembro del personal.

    La unicidad por (personal, mes_pagado, ciclo_escolar) garantiza que no se
    genere doble pago para el mismo mes dentro de un ciclo escolar.
    El campo comprobante_pdf almacena el archivo del recibo generado.
    """
    MESES = [
        (1, 'Enero'),    (2, 'Febrero'),   (3, 'Marzo'),
        (4, 'Abril'),    (5, 'Mayo'),       (6, 'Junio'),
        (7, 'Julio'),    (8, 'Agosto'),     (9, 'Septiembre'),
        (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
    ]

    personal = models.ForeignKey(
        Personal,
        on_delete=models.RESTRICT,
        related_name='planillas',
        verbose_name='Personal',
    )
    mes_pagado = models.PositiveSmallIntegerField(
        choices=MESES,
        verbose_name='Mes pagado',
    )
    ciclo_escolar = models.ForeignKey(
        'academico.CicloEscolar',
        on_delete=models.RESTRICT,
        related_name='planillas',
        verbose_name='Ciclo Escolar',
        null=True,
        blank=True,
    )
    bonificaciones = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Bonificaciones (Q)',
    )
    descuentos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Descuentos (Q)',
    )
    total_pagar = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Total a pagar (Q)',
    )
    comprobante_pdf = models.FileField(
        upload_to='planillas/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Comprobante PDF',
    )
    fecha_pago = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de pago',
    )
    pagado = models.BooleanField(
        default=False,
        verbose_name='¿Pagado?',
    )

    class Meta:
        verbose_name = 'Planilla'
        verbose_name_plural = 'Planillas'
        unique_together = [['personal', 'mes_pagado', 'ciclo_escolar']]
        ordering = ['-ciclo_escolar__anio', '-mes_pagado']

    def __str__(self):
        return (
            f"Planilla — {self.personal} — "
            f"{self.get_mes_pagado_display()} {self.ciclo_escolar.anio} "
            f"(Q{self.total_pagar})"
        )
