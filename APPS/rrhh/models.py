"""
rrhh/models.py

Recursos Humanos y Planilla de Sueldos del Instituto El Progreso.
Implementa el subtipo Personal (Persona FK primary_key=True), Puesto y Planilla.
"""
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from simple_history.models import HistoricalRecords
from APPS.core.models import ModeloAuditable, Persona


class EstadoLaboralChoices(models.TextChoices):
    ACTIVO     = 'ACTIVO',     'Activo'
    BAJA       = 'BAJA',       'Baja temporal'
    RETIRADO   = 'RETIRADO',   'Retirado'
    SUSPENDIDO = 'SUSPENDIDO', 'Suspendido'



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

class TipoPlanillaChoices(models.TextChoices):
    ORDINARIA      = 'ORDINARIA',      'Planilla Mensual Ordinaria'
    BONO_14        = 'BONO_14',        'Bono 14 (Decreto 42-92)'
    AGUINALDO      = 'AGUINALDO',      'Aguinaldo (Decreto 76-78)'
    EXTRAORDINARIA = 'EXTRAORDINARIA', 'Planilla Extraordinaria'
    LIQUIDACION    = 'LIQUIDACION',    'Liquidación / Finiquito Laboral'



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
    fecha_baja = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de baja o retiro'
    )
    motivo_baja = models.TextField(
        blank=True,
        verbose_name='Motivo de la baja o retiro'
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
        cui = f" | DPI: {self.persona.cui}" if self.persona and self.persona.cui else ""
        return f"{self.persona.nombre_completo}{cui} ({self.puesto.nombre_puesto})"

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




class Planilla(ModeloAuditable):
    """
    Registro de pago de planilla de personal (Normalizado en 3FN/4FN).
    Soporta Planilla Ordinaria Mensual, Bono 14 (Dec. 42-92), Aguinaldo (Dec. 76-78),
    Planilla Extraordinaria y Liquidación / Finiquito Laboral.
    Desglosa deducciones legales (IGSS), anticipos de sueldo, retenciones judiciales y otros descuentos.
    """
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
    tipo_planilla = models.CharField(
        max_length=20,
        choices=TipoPlanillaChoices.choices,
        default=TipoPlanillaChoices.ORDINARIA,
        verbose_name='Tipo de Planilla'
    )
    mes_pagado = models.IntegerField(
        choices=MesChoices.choices,
        verbose_name='Mes pagado'
    )

    # --- PERCEPCIONES / INGRESOS ---
    salario_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Salario Base Contratado (Q)',
        help_text='Salario nominal pactado en el contrato laboral.'
    )
    dias_laborados = models.PositiveSmallIntegerField(
        default=30,
        verbose_name='Días laborados en el período'
    )
    salario_ordinario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Salario Ordinario Devengado (Q)',
        help_text='Salario efectivamente devengado según días laborados.'
    )
    bonificacion_incentivo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Bonificación Incentivo de Ley (Q)',
        help_text='Bonificación decreto 37-2001 (ordinaria Q250.00).'
    )
    bonificaciones = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Otras Bonificaciones / Horas Extras (Q)'
    )

    # --- DEDUCCIONES / DESCUENTOS LABORALES ---
    descuento_igss = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Cuota Laboral IGSS (4.83%) (Q)'
    )
    retencion_isr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Retención ISR Asalariados (Q)',
        help_text='Retención mensual s/rentas del trabajo Decreto 10-2012.'
    )
    descuento_anticipo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Anticipo de Sueldo / Vales (Q)'
    )
    descuento_judicial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Retención Judicial / Embargo (Q)'
    )
    descuento_otros = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Otros Descuentos (Q)'
    )
    motivo_otros_descuentos = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Motivo de Otros Descuentos',
        help_text='Indique la razón específica de otros descuentos o faltas.'
    )
    descuentos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Total Descuentos (Q)'
    )

    # --- APORTES Y CARGAS PATRONALES (12.67% LEY DE GUATEMALA) ---
    cuota_patronal_igss = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Cuota Patronal IGSS (10.67%) (Q)',
        help_text='Aporte patronal IGSS según Decreto 295.'
    )
    cuota_patronal_irtra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Cuota Patronal IRTRA (1.00%) (Q)',
        help_text='Aporte patronal IRTRA según Decreto 1528.'
    )
    cuota_patronal_intecap = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Cuota Patronal INTECAP (1.00%) (Q)',
        help_text='Aporte patronal INTECAP según Decreto 17-72.'
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
    history = HistoricalRecords(
        verbose_name='Auditoría de Planilla'
    )

    class Meta:
        verbose_name = 'Planilla'
        verbose_name_plural = 'Planillas'
        unique_together = [['personal', 'mes_pagado', 'ciclo_escolar', 'tipo_planilla']]
        ordering = ['-mes_pagado', 'tipo_planilla']

    @classmethod
    def obtener_anotaciones_sql(cls) -> dict:
        from django.db.models import F, Value, DecimalField, Case, When
        from django.db.models.functions import Greatest
        sueldo_expr = Case(
            When(salario_ordinario__gt=Decimal('0.00'), then=F('salario_ordinario')),
            When(salario_base__gt=Decimal('0.00'), then=F('salario_base')),
            default=F('personal__salario_base_asignado'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
        ingresos_expr = Case(
            When(tipo_planilla__in=[TipoPlanillaChoices.BONO_14, TipoPlanillaChoices.AGUINALDO],
                 then=sueldo_expr + F('bonificaciones')),
            default=sueldo_expr + F('bonificacion_incentivo') + F('bonificaciones'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
        return {
            'total_pagar': Greatest(
                ingresos_expr - F('descuentos'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
        }

    @property
    def total_ingresos(self) -> Decimal:
        sueldo = Decimal(str(self.salario_ordinario or 0))
        if sueldo <= Decimal('0.00'):
            sueldo = Decimal(str(self.salario_base or 0))
        if sueldo <= Decimal('0.00') and self.personal_id:
            sueldo = Decimal(str(self.personal.salario_base_asignado or 0))
        bono_inc = Decimal(str(self.bonificacion_incentivo or 0))
        bono_extra = Decimal(str(self.bonificaciones or 0))
        if self.tipo_planilla in (TipoPlanillaChoices.BONO_14, TipoPlanillaChoices.AGUINALDO):
            return sueldo + bono_extra
        return sueldo + bono_inc + bono_extra

    @property
    def total_bonificaciones(self) -> Decimal:
        b_inc = Decimal(str(self.bonificacion_incentivo or 0))
        b_ext = Decimal(str(self.bonificaciones or 0))
        return b_inc + b_ext if (b_inc > Decimal('0.00') or b_ext > Decimal('0.00')) else Decimal('0.00')

    @property
    def total_descuentos(self) -> Decimal:
        d_igss = Decimal(str(self.descuento_igss or 0))
        r_isr = Decimal(str(self.retencion_isr or 0))
        d_ant = Decimal(str(self.descuento_anticipo or 0))
        d_jud = Decimal(str(self.descuento_judicial or 0))
        d_otr = Decimal(str(self.descuento_otros or 0))
        suma = d_igss + r_isr + d_ant + d_jud + d_otr
        if suma > Decimal('0.00'):
            return suma
        return Decimal(str(self.descuentos or 0))

    @property
    def total_cuota_patronal(self) -> Decimal:
        igss = Decimal(str(self.cuota_patronal_igss or 0))
        irtra = Decimal(str(self.cuota_patronal_irtra or 0))
        intecap = Decimal(str(self.cuota_patronal_intecap or 0))
        return round(igss + irtra + intecap, 2)

    @property
    def total_pagar(self) -> Decimal:
        return round(max(self.total_ingresos - self.total_descuentos, Decimal('0.00')), 2)

    @total_pagar.setter
    def total_pagar(self, valor) -> None:
        # propiedad derivada calculada dinamicamente
        pass

    def save(self, *args, **kwargs):
        if not self.salario_base and self.personal_id:
            self.salario_base = self.personal.salario_base_asignado
        if not self.salario_ordinario:
            self.salario_ordinario = self.salario_base
        d_igss = Decimal(str(self.descuento_igss or 0))
        r_isr = Decimal(str(self.retencion_isr or 0))
        d_ant = Decimal(str(self.descuento_anticipo or 0))
        d_jud = Decimal(str(self.descuento_judicial or 0))
        d_otr = Decimal(str(self.descuento_otros or 0))
        suma = d_igss + r_isr + d_ant + d_jud + d_otr
        if suma > Decimal('0.00') or self.descuentos == Decimal('0.00'):
            self.descuentos = suma
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Planilla {self.get_tipo_planilla_display()} - {self.get_mes_pagado_display()} - {self.personal.persona.nombre_completo} (Q{self.total_pagar})"
