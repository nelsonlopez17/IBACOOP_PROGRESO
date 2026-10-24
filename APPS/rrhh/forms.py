"""
APPS/rrhh/forms.py

Formularios para la contratación y gestión de Personal laboral del Instituto El Progreso.
Incluye:
  - PersonalForm: Captura de datos laborales y papelería con validaciones para Guatemala (NIT SAT, teléfono de 8 dígitos).
  - PlanillaGenerarMasivaForm: Generación masiva de planilla de sueldos mensual.
  - PlanillaUpdateForm: Modificación de bonos, retenciones y estado de pago de planilla de sueldos.
"""
from decimal import Decimal
from django import forms
from django.utils import timezone
from APPS.core.forms import TailwindFormMixin
from APPS.core.validadores import (
    limpiar_nit_guatemala,
    limpiar_telefono_guatemala,
    limpiar_texto_longitud,
)
from APPS.rrhh.models import (
    Personal, Puesto, Planilla,
    EstadoLaboralChoices, MesChoices, TipoPlanillaChoices
)
from APPS.academico.models import CicloEscolar


class PersonalForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para capturar y modificar los datos laborales, custodia de contrato físico y papelería del Empleado."""

    _CAMPOS_PROPIEDADES = (
        'contacto_emergencia_nombre',
        'contacto_emergencia_telefono',
        'doc_dpi_personal',
        'doc_nit_sat',
        'doc_titulo_academico',
        'doc_colegiado_activo',
        'doc_antecedentes_penales',
        'doc_antecedentes_policiales',
        'doc_contrato_fisico',
        'doc_tarjeta_salud',
    )

    contacto_emergencia_nombre = forms.CharField(
        min_length=3,
        max_length=150,
        required=False,
        label='Nombre de Contacto de Emergencia',
        widget=forms.TextInput(attrs={
            'minlength': '3',
            'maxlength': '150',
            'placeholder': 'Nombre completo del familiar o contacto de emergencia',
        }),
    )
    contacto_emergencia_telefono = forms.CharField(
        min_length=8,
        max_length=8,
        required=False,
        label='Teléfono de Contacto de Emergencia (8 dígitos)',
        widget=forms.TextInput(attrs={
            'minlength': '8',
            'maxlength': '8',
            'pattern': r'\d{8}',
            'inputmode': 'numeric',
            'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 8)",
            'placeholder': 'Ej. 55551234',
            'title': 'Ingrese un número telefónico de Guatemala de exactamente 8 dígitos numéricos.',
        }),
    )
    doc_dpi_personal = forms.BooleanField(
        required=False,
        label='1. Fotocopia de DPI / CUI (RENAP)',
    )
    doc_nit_sat = forms.BooleanField(
        required=False,
        label='2. Constancia de NIT (RTU SAT)',
    )
    doc_titulo_academico = forms.BooleanField(
        required=False,
        label='3. Fotocopia de Título Académico / Cédula Docente',
    )
    doc_colegiado_activo = forms.BooleanField(
        required=False,
        label='4. Constancia Colegiado Activo / Acreditación MINEDUC',
    )
    doc_antecedentes_penales = forms.BooleanField(
        required=False,
        label='5. Antecedentes Penales (Vigentes)',
    )
    doc_antecedentes_policiales = forms.BooleanField(
        required=False,
        label='6. Antecedentes Policiales (Vigentes)',
    )
    doc_contrato_fisico = forms.BooleanField(
        required=False,
        label='7. Contrato Físico Firmado',
    )
    doc_tarjeta_salud = forms.BooleanField(
        required=False,
        label='8. Tarjeta de Salud / Sanidad',
    )

    class Meta:
        model = Personal
        fields = [
            'puesto',
            'nit',
            'fecha_contratacion',
            'estado_laboral',
            'salario_base_asignado',
            'numero_contrato_fisico',
            'ubicacion_expediente_fisico',
        ]
        labels = {
            'puesto': 'Puesto o Cargo Asignado',
            'nit': 'NIT (Número de Identificación Tributaria - SAT)',
            'fecha_contratacion': 'Fecha de Contratación',
            'estado_laboral': 'Estado Laboral',
            'salario_base_asignado': 'Salario Base Mensual (Q)',
            'numero_contrato_fisico': 'No. Correlativo de Contrato Físico',
            'ubicacion_expediente_fisico': 'Ubicación Físico (Archivador/Carpeta)',
        }
        widgets = {
            'nit': forms.TextInput(attrs={
                'minlength': '2',
                'maxlength': '15',
                'pattern': r'([0-9]{1,12}-?[0-9Kk]|CF|C/F|cf|c/f)',
                'placeholder': 'Ej. 1234567-8 o CF',
                'title': 'Ingrese un NIT válido de la SAT (ej. 1234567-8, 1234567K o CF).',
            }),
            'fecha_contratacion': forms.DateInput(attrs={'type': 'date'}),
            'salario_base_asignado': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'max': '99999999.99',
            }),
            'numero_contrato_fisico': forms.TextInput(attrs={
                'maxlength': '50',
                'placeholder': 'Ej. CONT-2026-001',
            }),
            'ubicacion_expediente_fisico': forms.TextInput(attrs={
                'maxlength': '100',
                'placeholder': 'Ej. Archivador B-1, Carpeta 15 (Secretaría)',
            }),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance is not None and getattr(instance, 'pk', None):
            initial = dict(kwargs.get('initial') or {})
            for campo in self._CAMPOS_PROPIEDADES:
                if campo not in initial:
                    initial[campo] = getattr(instance, campo)
            kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean_salario_base_asignado(self):
        salario = self.cleaned_data.get('salario_base_asignado')
        if salario is not None and salario <= Decimal('0.00'):
            raise forms.ValidationError("El salario base asignado en Quetzales (Q) debe ser mayor a Q0.00.")
        return salario

    def clean_nit(self):
        nit = self.cleaned_data.get('nit')
        if nit:
            return limpiar_nit_guatemala(nit)
        return ''

    def clean_contacto_emergencia_nombre(self):
        val = self.cleaned_data.get('contacto_emergencia_nombre')
        if val:
            return limpiar_texto_longitud(
                val,
                nombre_campo='El nombre del contacto de emergencia',
                min_length=3,
                max_length=150,
                evitar_solo_numeros=True,
            )
        return ''

    def clean_contacto_emergencia_telefono(self):
        tel = self.cleaned_data.get('contacto_emergencia_telefono')
        if tel:
            return limpiar_telefono_guatemala(tel)
        return ''

    def clean_numero_contrato_fisico(self):
        val = self.cleaned_data.get('numero_contrato_fisico')
        if val:
            return limpiar_texto_longitud(val, 'El número de contrato físico', min_length=2, max_length=50)
        return ''

    def clean_ubicacion_expediente_fisico(self):
        val = self.cleaned_data.get('ubicacion_expediente_fisico')
        if val:
            return limpiar_texto_longitud(val, 'La ubicación del expediente físico', min_length=2, max_length=100)
        return ''

    def save(self, commit=True):
        personal = super().save(commit=False)
        for campo in self._CAMPOS_PROPIEDADES:
            if campo in self.cleaned_data:
                setattr(personal, campo, self.cleaned_data[campo])
        if commit:
            personal.save()
        return personal


class PersonalBajaForm(TailwindFormMixin, forms.Form):
    """Formulario para registrar el retiro / baja de un colaborador y deshabilitar sus credenciales."""

    fecha_baja = forms.DateField(
        label='Fecha Efectiva de Baja / Retiro',
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )
    estado_laboral = forms.ChoiceField(
        choices=[
            (EstadoLaboralChoices.RETIRADO, 'Retirado / Desvinculación Definitiva'),
            (EstadoLaboralChoices.BAJA, 'Baja Temporal'),
            (EstadoLaboralChoices.SUSPENDIDO, 'Suspendido (IGSS u Orden Legal)'),
        ],
        initial=EstadoLaboralChoices.RETIRADO,
        label='Estado Laboral Resultante',
        required=True
    )
    motivo_baja = forms.CharField(
        label='Motivo Detallado de la Baja o Retiro',
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Indique la justificación formal (ej. Renuncia voluntaria, término de contrato lectivo, despido con causa, traslado, etc.).',
        }),
        required=True
    )
    desactivar_usuario = forms.BooleanField(
        label='¿Desactivar inmediatamente la cuenta de acceso institucional?',
        initial=True,
        required=False,
        help_text='Impide que el colaborador vuelva a iniciar sesión en la plataforma ERP.'
    )


class PlanillaGenerarMasivaForm(TailwindFormMixin, forms.Form):
    """Formulario para la emisión y cálculo masivo de la planilla de sueldos (Ordinaria, Bono 14, Aguinaldo o Extraordinaria)."""

    ciclo_escolar = forms.ModelChoiceField(
        queryset=CicloEscolar.objects.filter(esta_eliminado=False, estado_activo=True).order_by('-anio'),
        label='Ciclo Escolar',
        required=True
    )
    tipo_planilla = forms.ChoiceField(
        choices=TipoPlanillaChoices.choices,
        initial=TipoPlanillaChoices.ORDINARIA,
        label='Tipo de Planilla',
        required=False
    )
    mes_pagado = forms.ChoiceField(
        choices=MesChoices.choices,
        label='Mes a Liquidar',
        required=True
    )
    bonificacion_ley = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal('0.00'),
        max_value=Decimal('999999.99'),
        initial=Decimal('250.00'),
        label='Bonificación Incentivo de Ley (Q)',
        help_text='Monto de bonificación según Decreto 37-2001 (Estándar Q250.00). Aplica únicamente a Planilla Ordinaria.',
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'min': '0',
            'max': '999999.99',
        }),
    )
    descontar_igss = forms.BooleanField(
        required=False,
        initial=False,
        label='¿Calcular y descontar cuota laboral IGSS (4.83%)?',
        help_text='Aplica retención del 4.83% sobre el salario base de cada trabajador. Solo aplica a Planilla Ordinaria.'
    )
    calcular_cuota_patronal = forms.BooleanField(
        required=False,
        initial=True,
        label='¿Calcular Aportes Patronales (12.67% IGSS, IRTRA, INTECAP)?',
        help_text='Registra el pasivo patronal de ley: IGSS 10.67%, IRTRA 1.00%, INTECAP 1.00%. Aplica a planillas ordinarias.'
    )
    calcular_retencion_isr = forms.BooleanField(
        required=False,
        initial=True,
        label='¿Calcular Retención Estimada de ISR Asalariados (Decreto 10-2012)?',
        help_text='Aplica retención mensual estimada sobre salarios base mayores a Q4,000.00 mensuales (Rentas del Trabajo).'
    )
    prorratear_altas = forms.BooleanField(
        required=False,
        initial=True,
        label='¿Prorratear días laborados en contrataciones del mes en curso?',
        help_text='Si el empleado fue contratado en el mes que se liquida, calcula el sueldo según días efectivos (30 - día inicio + 1).'
    )
    fecha_pago = forms.DateField(
        label='Fecha de Pago Estimada',
        initial=timezone.now().date,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        if ciclo_activo:
            self.fields['ciclo_escolar'].initial = ciclo_activo
        self.fields['mes_pagado'].initial = timezone.now().month

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_planilla') or TipoPlanillaChoices.ORDINARIA
        cleaned_data['tipo_planilla'] = tipo
        if tipo == TipoPlanillaChoices.BONO_14:
            cleaned_data['mes_pagado'] = MesChoices.JULIO
            cleaned_data['bonificacion_ley'] = Decimal('0.00')
            cleaned_data['descontar_igss'] = False
            cleaned_data['calcular_cuota_patronal'] = False
        elif tipo == TipoPlanillaChoices.AGUINALDO:
            cleaned_data['mes_pagado'] = MesChoices.DICIEMBRE
            cleaned_data['bonificacion_ley'] = Decimal('0.00')
            cleaned_data['descontar_igss'] = False
            cleaned_data['calcular_cuota_patronal'] = False
        elif tipo == TipoPlanillaChoices.EXTRAORDINARIA:
            cleaned_data['bonificacion_ley'] = Decimal('0.00')
        return cleaned_data


class PlanillaUpdateForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para ajustar ingresos, deducciones desglosadas y liquidar boleta de pago de planilla."""

    class Meta:
        model = Planilla
        fields = [
            'salario_base',
            'dias_laborados',
            'salario_ordinario',
            'bonificacion_incentivo',
            'bonificaciones',
            'descuento_igss',
            'retencion_isr',
            'descuento_anticipo',
            'descuento_judicial',
            'descuento_otros',
            'motivo_otros_descuentos',
            'descuentos',
            'cuota_patronal_igss',
            'cuota_patronal_irtra',
            'cuota_patronal_intecap',
            'fecha_pago',
            'pagado',
        ]
        labels = {
            'salario_base': 'Salario Base Contratado (Q)',
            'dias_laborados': 'Días Laborados en el Período',
            'salario_ordinario': 'Salario Ordinario Devengado (Q)',
            'bonificacion_incentivo': 'Bonificación Incentivo Ley (Dec. 37-2001) (Q)',
            'bonificaciones': 'Otras Bonificaciones / Horas Extras (Q)',
            'descuento_igss': 'Retención Cuota Laboral IGSS (4.83%) (Q)',
            'retencion_isr': 'Retención ISR Asalariados (Decreto 10-2012) (Q)',
            'descuento_anticipo': 'Anticipo de Sueldo / Vales (Q)',
            'descuento_judicial': 'Retención Judicial / Embargo (Q)',
            'descuento_otros': 'Otros Descuentos (Q)',
            'motivo_otros_descuentos': 'Motivo u Observación de Otros Descuentos',
            'descuentos': 'Total Descuentos (Q)',
            'cuota_patronal_igss': 'Cuota Patronal IGSS (10.67%) (Q)',
            'cuota_patronal_irtra': 'Cuota Patronal IRTRA (1.00%) (Q)',
            'cuota_patronal_intecap': 'Cuota Patronal INTECAP (1.00%) (Q)',
            'fecha_pago': 'Fecha de Pago',
            'pagado': '¿Planilla Pagada / Liquidada?',
        }
        widgets = {
            'salario_base': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'dias_laborados': forms.NumberInput(attrs={'min': '1', 'max': '31'}),
            'salario_ordinario': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'bonificacion_incentivo': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'bonificaciones': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'descuento_igss': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'retencion_isr': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'descuento_anticipo': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'descuento_judicial': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'descuento_otros': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'motivo_otros_descuentos': forms.TextInput(attrs={'placeholder': 'Ej. 2 días de falta injustificada, reposición de material'}),
            'descuentos': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'cuota_patronal_igss': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'cuota_patronal_irtra': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'cuota_patronal_intecap': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99999999.99'}),
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in [
            'salario_base', 'dias_laborados', 'salario_ordinario',
            'bonificacion_incentivo', 'bonificaciones',
            'descuento_igss', 'retencion_isr', 'descuento_anticipo', 'descuento_judicial',
            'descuento_otros', 'motivo_otros_descuentos', 'descuentos',
            'cuota_patronal_igss', 'cuota_patronal_irtra', 'cuota_patronal_intecap'
        ]:
            if f in self.fields:
                self.fields[f].required = False

    def clean(self):
        cleaned_data = super().clean()

        # Validación de inmutabilidad financiera: una boleta pagada no puede ser alterada
        if self.instance and self.instance.pk:
            pagado_original = Planilla.objects.filter(pk=self.instance.pk).values_list('pagado', flat=True).first()
            if pagado_original:
                raise forms.ValidationError("Esta boleta de pago ya se encuentra en estado 'PAGADO' y no puede ser modificada.")

        for field in [
            'salario_base', 'salario_ordinario',
            'bonificacion_incentivo', 'bonificaciones',
            'descuento_igss', 'retencion_isr', 'descuento_anticipo',
            'descuento_judicial', 'descuento_otros', 'descuentos',
            'cuota_patronal_igss', 'cuota_patronal_irtra', 'cuota_patronal_intecap'
        ]:
            val = cleaned_data.get(field) or Decimal('0.00')
            if val < 0:
                self.add_error(field, 'El monto no puede ser negativo.')

        d_igss = cleaned_data.get('descuento_igss') or Decimal('0.00')
        r_isr = cleaned_data.get('retencion_isr') or Decimal('0.00')
        d_ant = cleaned_data.get('descuento_anticipo') or Decimal('0.00')
        d_jud = cleaned_data.get('descuento_judicial') or Decimal('0.00')
        d_otros = cleaned_data.get('descuento_otros') or Decimal('0.00')
        suma_desglose = d_igss + r_isr + d_ant + d_jud + d_otros

        if suma_desglose > Decimal('0.00'):
            cleaned_data['descuentos'] = suma_desglose
        elif cleaned_data.get('descuentos'):
            pass
        else:
            cleaned_data['descuentos'] = Decimal('0.00')

        motivo = (cleaned_data.get('motivo_otros_descuentos') or '').strip()
        if d_otros > 0 and not motivo:
            self.add_error('motivo_otros_descuentos', 'Debe especificar el motivo u observación de otros descuentos.')

        return cleaned_data
