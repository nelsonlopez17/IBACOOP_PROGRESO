"""
financiero/models.py

Gestión financiera del Instituto El Progreso.
Cubre el cobro de mensualidades (colegiaturas) y el registro de pagos.

django-simple-history en PagoColegiatura: audita cada registro de pago
para garantizar trazabilidad completa en operaciones financieras.
"""
from django.db import models
from simple_history.models import HistoricalRecords

from APPS.core.models import ModeloAuditable


class MensualidadCobro(ModeloAuditable):
    """
    Representa la cuota mensual (colegiatura) que debe pagar un estudiante.

    Se genera un registro por estudiante por mes del ciclo escolar.
    La unicidad (estudiante, ciclo_escolar, mes_cobro) evita duplicados.
    RESTRICT en FK: protege la integridad financiera — no se puede eliminar
    un estudiante o ciclo que tenga mensualidades registradas.
    """
    MESES = [
        (1, 'Enero'),    (2, 'Febrero'),   (3, 'Marzo'),
        (4, 'Abril'),    (5, 'Mayo'),       (6, 'Junio'),
        (7, 'Julio'),    (8, 'Agosto'),     (9, 'Septiembre'),
        (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
    ]

    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.RESTRICT,
        related_name='mensualidades',
        verbose_name='Estudiante',
    )
    ciclo_escolar = models.ForeignKey(
        'academico.CicloEscolar',
        on_delete=models.RESTRICT,
        related_name='mensualidades',
        verbose_name='Ciclo Escolar',
    )
    mes_cobro = models.PositiveSmallIntegerField(
        choices=MESES,
        verbose_name='Mes de cobro',
    )
    monto_esperado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto esperado (Q)',
    )
    estado_pagado = models.BooleanField(
        default=False,
        verbose_name='¿Pagado?',
    )
    fecha_limite_pago = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha límite de pago',
    )

    class Meta:
        verbose_name = 'Mensualidad de Cobro'
        verbose_name_plural = 'Mensualidades de Cobro'
        unique_together = [['estudiante', 'ciclo_escolar', 'mes_cobro']]
        ordering = ['ciclo_escolar', 'mes_cobro', 'estudiante']

    def __str__(self):
        return (
            f"{self.estudiante} — "
            f"{self.get_mes_cobro_display()} {self.ciclo_escolar.anio} "
            f"(Q{self.monto_esperado})"
        )


class PagoColegiatura(ModeloAuditable):
    """
    Registro de un pago realizado contra una mensualidad.

    Se permite pago parcial (monto_pagado puede ser menor a monto_esperado).
    El número de boleta es único a nivel del sistema.
    django-simple-history: cada modificación al registro de pago queda auditada
    (quién cambió el monto, cuándo se marcó como pagado, etc.).
    RESTRICT en MensualidadCobro: no se puede eliminar una mensualidad que
    ya tenga pagos registrados.
    """
    mensualidad = models.ForeignKey(
        MensualidadCobro,
        on_delete=models.RESTRICT,
        related_name='pagos',
        verbose_name='Mensualidad',
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto pagado (Q)',
    )
    fecha_pago = models.DateField(verbose_name='Fecha de pago')
    numero_boleta = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Número de boleta',
    )
    recibo_generado = models.BooleanField(
        default=False,
        verbose_name='¿Recibo generado?',
    )
    recibo_pdf = models.FileField(
        upload_to='recibos/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Archivo de recibo (PDF)',
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
    )
    # --- Auditoría de pagos (django-simple-history) ---
    history = HistoricalRecords(
        verbose_name='Historial de cambios del pago',
    )

    class Meta:
        verbose_name = 'Pago de Colegiatura'
        verbose_name_plural = 'Pagos de Colegiatura'
        ordering = ['-fecha_pago']

    def __str__(self):
        return (
            f"Boleta {self.numero_boleta} — "
            f"{self.mensualidad} (Q{self.monto_pagado})"
        )
