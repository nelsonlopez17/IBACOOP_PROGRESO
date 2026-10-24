"""
financiero/models.py

Gestión financiera del Instituto El Progreso basada en el sistema de Cuenta Corriente:
ConceptoPago (Catálogo), CuentaPorCobrar (Deuda) y Abono (Pagos auditados con simple-history).
"""
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from django.db import models
from simple_history.models import HistoricalRecords

from APPS.core.models import ModeloAuditable


class EstadoPagoChoices(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    PARCIAL   = 'PARCIAL',   'Pago Parcial'
    PAGADO    = 'PAGADO',    'Pagado / Solvente'


class CategoriaConceptoChoices(models.TextChoices):
    MATRICULA   = 'MATRICULA',   'Cuota de Inscripción Escolar'
    COLEGIATURA = 'COLEGIATURA', 'Cuota Mensual de Enseñanza'
    MATERIALES  = 'MATERIALES',  'Libros, Guías y Materiales Didácticos'
    SERVICIOS   = 'SERVICIOS',   'Seguro Estudiantil, Carnets y Servicios'
    EVENTOS     = 'EVENTOS',     'Actos de Graduación, Diplomas y Eventos'
    GENERAL     = 'GENERAL',     'Otros Servicios Varios / Extraordinarios'


class MetodoPagoChoices(models.TextChoices):
    EFECTIVO      = 'EFECTIVO',      'Efectivo en Caja'
    DEPOSITO      = 'DEPOSITO',      'Depósito Bancario'
    TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia Bancaria'


class ConceptoPago(ModeloAuditable):
    """Catálogo de conceptos de cobro (Cuota Mensual, Inscripción, Materiales, etc.)."""
    nombre = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(3)],
        verbose_name='Nombre del concepto'
    )
    monto_estandar = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
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
        verbose_name='¿Generar automáticamente al inscribir al estudiante en una Sección?',
        help_text='Si se marca, este cobro se emitirá automáticamente cada vez que el estudiante sea inscrito en una Sección (estudiantes nuevos y reinscripciones anuales).'
    )

    class Meta:
        verbose_name = 'Concepto de Pago'
        verbose_name_plural = 'Conceptos de Pago'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} (Q{self.monto_estandar})"


class CuentaPorCobrar(ModeloAuditable):
    """
    Registro de la obligación financiera (deuda) de un estudiante (Normalizado en 3FN/4FN).
    Los atributos derivados `saldo_pendiente` y `estado_pago` se calculan dinámicamente
    a partir de `monto_total` y la suma de `abonos` activos sin redundancia física.
    """
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
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Monto total (Q)'
    )
    fecha_limite_pago = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha límite de pago'
    )
    mes_aplicacion = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name='Mes de aplicación (1-12)',
        help_text='Indica el mes calendario al que corresponde la cuota mensual (1=Enero, 2=Febrero, etc.).'
    )
    history = HistoricalRecords(
        verbose_name='Auditoría de Cuenta por Cobrar'
    )

    class Meta:
        verbose_name = 'Cuenta por Cobrar'
        verbose_name_plural = 'Cuentas por Cobrar'
        ordering = ['ciclo_escolar', 'fecha_limite_pago']

    @classmethod
    def obtener_anotaciones_sql(cls) -> dict:
        from django.db.models import Subquery, OuterRef, Sum, F, Value, DecimalField, CharField, Case, When
        from django.db.models.functions import Coalesce, Greatest
        abonos_sub = Subquery(
            Abono.todos.filter(
                cuenta_por_cobrar_id=OuterRef('pk'),
                esta_eliminado=False,
            )
            .values('cuenta_por_cobrar_id')
            .annotate(s=Sum('monto_pagado'))
            .values('s')[:1],
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
        total_abonado_expr = Coalesce(
            abonos_sub,
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
        saldo_expr = Greatest(
            F('monto_total') - total_abonado_expr,
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
        estado_expr = Case(
            When(saldo_pendiente__lte=Decimal('0.00'), then=Value(EstadoPagoChoices.PAGADO)),
            When(_total_abonado_sql__gt=Decimal('0.00'), then=Value(EstadoPagoChoices.PARCIAL)),
            default=Value(EstadoPagoChoices.PENDIENTE),
            output_field=CharField(max_length=20),
        )
        return {
            '_total_abonado_sql': total_abonado_expr,
            'saldo_pendiente': saldo_expr,
            'estado_pago': estado_expr,
        }

    @property
    def total_abonado(self) -> Decimal:
        if not self.pk:
            return Decimal('0.00')
        res = self.abonos.filter(esta_eliminado=False).aggregate(total=models.Sum('monto_pagado'))['total']
        return Decimal(str(res)) if res is not None else Decimal('0.00')

    @property
    def saldo_pendiente(self) -> Decimal:
        monto = Decimal(str(self.monto_total)) if self.monto_total is not None else Decimal('0.00')
        return round(max(monto - self.total_abonado, Decimal('0.00')), 2)

    @saldo_pendiente.setter
    def saldo_pendiente(self, valor) -> None:
        # propiedad derivada calculada dinamicamente
        pass

    @property
    def estado_pago(self) -> str:
        if self.saldo_pendiente <= Decimal('0.00'):
            return EstadoPagoChoices.PAGADO
        if self.total_abonado > Decimal('0.00'):
            return EstadoPagoChoices.PARCIAL
        return EstadoPagoChoices.PENDIENTE

    @estado_pago.setter
    def estado_pago(self, valor) -> None:
        # propiedad derivada calculada dinamicamente
        pass

    def get_estado_pago_display(self) -> str:
        return dict(EstadoPagoChoices.choices).get(self.estado_pago, self.estado_pago)

    def __str__(self):
        return f"Deuda: {self.estudiante.persona.nombre_completo} — {self.concepto.nombre} (Saldo: Q{self.saldo_pendiente})"

    def actualizar_saldo(self):
        """Registra la actualización de auditoría al modificarse los abonos asociados."""
        if self.pk:
            self.save(update_fields=['actualizado_en'])


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
        help_text='Si se deja en blanco, el descuento se aplicará a todas las cuotas mensuales.'
    )
    porcentaje_descuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name='Porcentaje de Descuento (%)'
    )
    monto_descuento_fijo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Monto Fijo de Descuento (Q)'
    )
    motivo_convenio = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(3)],
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

    @property
    def motivo(self) -> str:
        """Alias hacia motivo_convenio para reportes y plantillas."""
        return self.motivo_convenio

    def calcular_monto_con_descuento(self, monto_base: Decimal) -> Decimal:
        """Calcula el monto neto en Quetzales aplicando el porcentaje o monto fijo de beca/convenio."""
        base = Decimal(str(monto_base or '0.00'))
        if self.porcentaje_descuento and self.porcentaje_descuento > Decimal('0.00'):
            descuento = round(base * (Decimal(str(self.porcentaje_descuento)) / Decimal('100.00')), 2)
        else:
            descuento = Decimal(str(self.monto_descuento_fijo or '0.00'))
        return max(round(base - descuento, 2), Decimal('0.00'))


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
    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPagoChoices.choices,
        default=MetodoPagoChoices.EFECTIVO,
        verbose_name='Método de pago'
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Monto pagado (Q)'
    )
    fecha_pago = models.DateField(
        verbose_name='Fecha de pago'
    )
    numero_boleta = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        verbose_name='Número de boleta o recibo'
    )
    recibo_pdf = models.FileField(
        upload_to='recibos/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Recibo en PDF'
    )
    observaciones = models.TextField(
        max_length=300,
        blank=True,
        verbose_name='Observaciones'
    )
    history = HistoricalRecords(
        verbose_name='Historial de cambios de abonos'
    )

    class Meta:
        verbose_name = 'Abono'
        verbose_name_plural = 'Abonos'
        ordering = ['-fecha_pago', '-creado_en']

    def __str__(self):
        return f"{self.get_metodo_pago_display()} ({self.numero_boleta}) — {self.cuenta_por_cobrar.estudiante.persona.nombre_completo} (Q{self.monto_pagado})"

    def save(self, *args, **kwargs):
        if not self.numero_boleta:
            from django.utils import timezone
            anio = self.fecha_pago.year if self.fecha_pago else timezone.now().year
            ultimo_count = Abono.objects.filter(numero_boleta__startswith=f'REC-{anio}-').count() + 1
            correlativo = f'REC-{anio}-{ultimo_count:05d}'
            while Abono.objects.filter(numero_boleta=correlativo).exists():
                ultimo_count += 1
                correlativo = f'REC-{anio}-{ultimo_count:05d}'
            self.numero_boleta = correlativo
        super().save(*args, **kwargs)
        self.cuenta_por_cobrar.actualizar_saldo()
