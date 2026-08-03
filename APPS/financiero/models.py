"""
financiero/models.py

Gestión financiera del Instituto El Progreso basada en el sistema de Cuenta Corriente:
ConceptoPago (Catálogo), CuentaPorCobrar (Deuda) y Abono (Pagos auditados con simple-history).
"""
from django.db import models
from simple_history.models import HistoricalRecords

from APPS.core.models import ModeloAuditable


class EstadoPagoChoices(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    PARCIAL   = 'PARCIAL',   'Pago Parcial'
    PAGADO    = 'PAGADO',    'Pagado / Solvente'


class ConceptoPago(ModeloAuditable):
    """Catálogo de conceptos de cobro (Colegiatura, Inscripción, Materiales, etc.)."""
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del concepto'
    )
    monto_estandar = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto estándar (Q)'
    )

    class Meta:
        verbose_name = 'Concepto de Pago'
        verbose_name_plural = 'Conceptos de Pago'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} (Q{self.monto_estandar})"


class CuentaPorCobrar(ModeloAuditable):
    """Registro de la obligación financiera (deuda) de un estudiante."""
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.RESTRICT,
        related_name='cuentas_por_cobrar',
        verbose_name='Estudiante'
    )
    concepto = models.ForeignKey(
        ConceptoPago,
        on_delete=models.RESTRICT,
        related_name='cuentas_por_cobrar',
        verbose_name='Concepto de Pago'
    )
    ciclo_escolar = models.ForeignKey(
        'academico.CicloEscolar',
        on_delete=models.RESTRICT,
        related_name='cuentas_por_cobrar',
        verbose_name='Ciclo Escolar'
    )
    monto_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto total (Q)'
    )
    saldo_pendiente = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Saldo pendiente (Q)'
    )
    fecha_limite_pago = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha límite de pago'
    )
    estado_pago = models.CharField(
        max_length=20,
        choices=EstadoPagoChoices.choices,
        default=EstadoPagoChoices.PENDIENTE,
        verbose_name='Estado del pago'
    )

    class Meta:
        verbose_name = 'Cuenta por Cobrar'
        verbose_name_plural = 'Cuentas por Cobrar'
        ordering = ['ciclo_escolar', 'fecha_limite_pago']

    def __str__(self):
        return f"Deuda: {self.estudiante.persona.nombre_completo} — {self.concepto.nombre} (Saldo: Q{self.saldo_pendiente})"

    def actualizar_saldo(self):
        """Actualiza el saldo pendiente y el estado del pago basado en los abonos activos."""
        total_abonado = sum(
            abono.monto_pagado for abono in self.abonos.filter(esta_eliminado=False)
        )
        self.saldo_pendiente = max(self.monto_total - total_abonado, 0)
        
        if self.saldo_pendiente == 0:
            self.estado_pago = EstadoPagoChoices.PAGADO
        elif total_abonado > 0:
            self.estado_pago = EstadoPagoChoices.PARCIAL
        else:
            self.estado_pago = EstadoPagoChoices.PENDIENTE

        self.save(update_fields=['saldo_pendiente', 'estado_pago', 'actualizado_en'])


class Abono(ModeloAuditable):
    """
    Registro de cada pago parcial o total recibido contra una CuentaPorCobrar.
    Auditado con django-simple-history para trazabilidad contable inmutable.
    """
    cuenta_por_cobrar = models.ForeignKey(
        CuentaPorCobrar,
        on_delete=models.RESTRICT,
        related_name='abonos',
        verbose_name='Cuenta por cobrar'
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto pagado (Q)'
    )
    fecha_pago = models.DateField(
        verbose_name='Fecha de pago'
    )
    numero_boleta = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Número de boleta'
    )
    recibo_pdf = models.FileField(
        upload_to='recibos/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Recibo en PDF'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    history = HistoricalRecords(
        verbose_name='Historial de cambios de abonos'
    )

    class Meta:
        verbose_name = 'Abono'
        verbose_name_plural = 'Abonos'
        ordering = ['-fecha_pago']

    def __str__(self):
        return f"Boleta {self.numero_boleta} — {self.cuenta_por_cobrar.estudiante.persona.nombre_completo} (Q{self.monto_pagado})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.cuenta_por_cobrar.actualizar_saldo()
