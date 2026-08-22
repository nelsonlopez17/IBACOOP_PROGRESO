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


class CategoriaConceptoChoices(models.TextChoices):
    MATRICULA   = 'MATRICULA',   'Cuota de Inscripción / Matrícula Escolar'
    COLEGIATURA = 'COLEGIATURA', 'Colegiatura / Mensualidad Regular'
    MATERIALES  = 'MATERIALES',  'Libros, Guías y Materiales Didácticos'
    SERVICIOS   = 'SERVICIOS',   'Seguro Estudiantil, Carnets y Servicios'
    EVENTOS     = 'EVENTOS',     'Actos de Graduación, Diplomas y Eventos'
    GENERAL     = 'GENERAL',     'Otros Servicios Varios / Extraordinarios'


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
    categoria_concepto = models.CharField(
        max_length=30,
        choices=CategoriaConceptoChoices.choices,
        default=CategoriaConceptoChoices.GENERAL,
        verbose_name='Categoría del Concepto'
    )
    aplica_al_inscribir_seccion = models.BooleanField(
        default=False,
        verbose_name='¿Generar automáticamente al matricular al alumno en una Sección?',
        help_text='Si se marca, este cobro se emitirá automáticamente cada vez que el estudiante sea inscrito en una Sección (alumnos nuevos y reinscripciones anuales).'
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
    mes_aplicacion = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Mes de aplicación (1-12)',
        help_text='Indica el mes calendario al que corresponde la colegiatura (1=Enero, 2=Febrero, etc.).'
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


class BecaDescuento(ModeloAuditable):
    """Registro de becas, convenios o descuentos especiales por estudiante."""
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.CASCADE,
        related_name='becas_descuentos',
        verbose_name='Estudiante Beneficiario'
    )
    concepto = models.ForeignKey(
        ConceptoPago,
        on_delete=models.RESTRICT,
        related_name='becas_descuentos',
        null=True,
        blank=True,
        verbose_name='Concepto Específico (Opcional)',
        help_text='Si se deja en blanco, el descuento se aplicará a todas las colegiaturas.'
    )
    porcentaje_descuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Porcentaje de Descuento (%)'
    )
    monto_descuento_fijo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Monto Fijo de Descuento (Q)'
    )
    motivo_convenio = models.CharField(
        max_length=200,
        verbose_name='Motivo / Tipo de Convenio'
    )
    esta_activo = models.BooleanField(
        default=True,
        verbose_name='¿Convenio Activo?'
    )

    class Meta:
        verbose_name = 'Beca / Descuento'
        verbose_name_plural = 'Becas y Descuentos'
        ordering = ['estudiante__persona__apellidos']

    def __str__(self):
        desc = f"{self.porcentaje_descuento}%" if self.porcentaje_descuento > 0 else f"Q{self.monto_descuento_fijo}"
        return f"Beca ({desc}): {self.estudiante.persona.nombre_completo} — {self.motivo_convenio}"

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
