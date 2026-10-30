"""
APPS/financiero/forms.py

Formularios para el módulo financiero del Instituto El Progreso.
Hereda de TailwindFormMixin (APPS.core.forms) para coherencia de estilos visuales
y validación de longitudes y montos en Quetzales (Q).
"""
from decimal import Decimal
from django import forms

from APPS.core.forms import TailwindFormMixin
from APPS.core.validadores import limpiar_texto_longitud
from APPS.financiero.models import ConceptoPago, CuentaPorCobrar, Abono, BecaDescuento, MetodoPagoChoices
from APPS.academico.models import CicloEscolar, Grado, Seccion
from APPS.estudiantes.models import Estudiante


class BecaDescuentoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para asignar becas y convenios de descuento a estudiantes."""

    class Meta:
        model = BecaDescuento
        fields = ['estudiante', 'concepto', 'porcentaje_descuento', 'monto_descuento_fijo', 'motivo_convenio', 'esta_activo']
        labels = {
            'estudiante': 'Estudiante Beneficiario',
            'concepto': 'Concepto Específico (Opcional)',
            'porcentaje_descuento': 'Porcentaje de Descuento (%)',
            'monto_descuento_fijo': 'Monto Fijo de Descuento (Q)',
            'motivo_convenio': 'Motivo / Tipo de Convenio',
            'esta_activo': '¿Convenio Activo?',
        }
        widgets = {
            'motivo_convenio': forms.TextInput(attrs={
                'minlength': '3',
                'maxlength': '200',
                'placeholder': 'Ej. Hijo de Cooperativista (20% desc), Beca Académica',
            }),
            'porcentaje_descuento': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'max': '100',
            }),
            'monto_descuento_fijo': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'max': '99999999.99',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estudiante'].queryset = Estudiante.objects.filter(
            persona__esta_eliminado=False,
            estado_estudiante='ACTIVO'
        ).select_related('persona').order_by('persona__apellidos', 'persona__nombres')

    def clean_motivo_convenio(self):
        motivo = self.cleaned_data.get('motivo_convenio')
        if motivo:
            return limpiar_texto_longitud(
                motivo,
                nombre_campo='El motivo o tipo de convenio',
                min_length=3,
                max_length=200,
                obligatorio=True,
                evitar_solo_numeros=True,
            )
        return motivo

    def clean(self):
        cleaned_data = super().clean()
        porcentaje = cleaned_data.get('porcentaje_descuento') or Decimal('0.00')
        monto_fijo = cleaned_data.get('monto_descuento_fijo') or Decimal('0.00')

        if porcentaje < Decimal('0.00') or porcentaje > Decimal('100.00'):
            self.add_error('porcentaje_descuento', 'El porcentaje de descuento debe estar entre 0% y 100%.')

        if monto_fijo < Decimal('0.00'):
            self.add_error('monto_descuento_fijo', 'El monto fijo de descuento en Quetzales (Q) no puede ser negativo.')

        if porcentaje <= Decimal('0.00') and monto_fijo <= Decimal('0.00'):
            self.add_error(
                'porcentaje_descuento',
                'Debe especificar un porcentaje de descuento (> 0%) o un monto fijo de descuento (> Q0.00).'
            )
        return cleaned_data


class ConceptoPagoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para crear y editar conceptos de pago en el catálogo."""

    class Meta:
        model = ConceptoPago
        fields = ['nombre', 'monto_estandar', 'categoria_concepto', 'aplica_al_inscribir_seccion']
        labels = {
            'nombre': 'Nombre del Concepto de Cobro',
            'monto_estandar': 'Monto Estándar (Q)',
            'categoria_concepto': 'Categoría del Concepto',
            'aplica_al_inscribir_seccion': '¿Generar automáticamente al inscribir al estudiante en una Sección?',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={
                'minlength': '3',
                'maxlength': '100',
                'placeholder': 'Ej. Inscripción Ciclo 2026, Cuota Mensual, Acto de Graduación',
            }),
            'monto_estandar': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'max': '99999999.99',
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            nombre = limpiar_texto_longitud(
                nombre,
                nombre_campo='El nombre del concepto',
                min_length=3,
                max_length=100,
                obligatorio=True,
                evitar_solo_numeros=True,
            )
            qs = ConceptoPago.objects.filter(nombre__iexact=nombre, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Ya existe un concepto de pago registrado con este nombre.')
        return nombre

    def clean_monto_estandar(self):
        monto = self.cleaned_data.get('monto_estandar')
        if monto is not None and monto <= Decimal('0.00'):
            raise forms.ValidationError('El monto del concepto en Quetzales (Q) debe ser mayor a Q0.00.')
        return monto


class CuentaPorCobrarForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para asignar un cargo o deuda individual a un estudiante específico."""

    class Meta:
        model = CuentaPorCobrar
        fields = ['estudiante', 'concepto', 'ciclo_escolar', 'monto_total', 'fecha_limite_pago']
        labels = {
            'estudiante': 'Estudiante Destinatario',
            'concepto': 'Concepto de Pago',
            'ciclo_escolar': 'Ciclo Escolar',
            'monto_total': 'Monto a Cobrar (Q) (Opcional)',
            'fecha_limite_pago': 'Fecha Límite de Pago (Opcional)',
        }
        widgets = {
            'fecha_limite_pago': forms.DateInput(attrs={'type': 'date'}),
            'monto_total': forms.NumberInput(attrs={
                'placeholder': 'Dejar vacío para usar monto estándar',
                'step': '0.01',
                'min': '0.01',
                'max': '99999999.99',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['monto_total'].required = False
        self.fields['estudiante'].queryset = Estudiante.objects.filter(
            persona__esta_eliminado=False,
            estado_estudiante='ACTIVO'
        ).select_related('persona').order_by('persona__apellidos', 'persona__nombres')
        
        self.fields['ciclo_escolar'].queryset = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False)
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True, esta_eliminado=False)
            self.fields['ciclo_escolar'].initial = ciclo_activo
        except Exception:
            pass

        self.fields['concepto'].queryset = ConceptoPago.objects.filter(esta_eliminado=False)

        if not self.is_bound and self.initial.get('concepto'):
            try:
                c = ConceptoPago.objects.get(pk=self.initial.get('concepto'))
                self.initial['monto_total'] = c.monto_estandar
            except ConceptoPago.DoesNotExist:
                pass

    def clean_monto_total(self):
        monto = self.cleaned_data.get('monto_total')
        if monto is not None and monto <= Decimal('0.00'):
            raise forms.ValidationError('El monto a cobrar en Quetzales (Q) debe ser mayor a Q0.00.')
        return monto

    def clean(self):
        cleaned_data = super().clean()
        estudiante = cleaned_data.get('estudiante')
        concepto = cleaned_data.get('concepto')
        ciclo = cleaned_data.get('ciclo_escolar')
        monto_total = cleaned_data.get('monto_total')

        if not monto_total:
            if concepto and concepto.monto_estandar:
                cleaned_data['monto_total'] = concepto.monto_estandar
                self.cleaned_data['monto_total'] = concepto.monto_estandar
            else:
                self.add_error(
                    'monto_total',
                    'Debe ingresar un monto a cobrar o seleccionar un concepto con monto estándar configurado.'
                )

        if estudiante and concepto and ciclo:
            qs = CuentaPorCobrar.objects.filter(
                estudiante=estudiante,
                concepto=concepto,
                ciclo_escolar=ciclo,
                esta_eliminado=False
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    'concepto',
                    f'El estudiante {estudiante.persona.nombre_completo} ya tiene registrado un cobro de "{concepto.nombre}" para el ciclo escolar {ciclo.anio}.'
                )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.monto_total:
            monto = self.cleaned_data.get('monto_total')
            if not monto and instance.concepto and instance.concepto.monto_estandar:
                monto = instance.concepto.monto_estandar
            instance.monto_total = monto
        if commit:
            instance.save()
        return instance


class GenerarCobroMasivoForm(TailwindFormMixin, forms.Form):
    """
    Formulario para la emisión masiva de cobros por Grado, Sección o a todos los estudiantes activos.
    Permite generar deudas masivas como Inscripción, Cuota Mensual o Acto de Graduación para 3ro Básico.
    """

    concepto = forms.ModelChoiceField(
        queryset=ConceptoPago.objects.filter(esta_eliminado=False),
        label='Concepto de Cobro',
        help_text='Seleccione la cuota o actividad a cobrar.'
    )
    ciclo_escolar = forms.ModelChoiceField(
        queryset=CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False),
        label='Ciclo Escolar Activo'
    )
    grado = forms.ModelChoiceField(
        queryset=Grado.objects.filter(esta_eliminado=False),
        required=False,
        label='Grado Destinatario (Opcional)',
        help_text='Déjelo en blanco si el cobro aplica a todos los grados.'
    )
    seccion = forms.ModelChoiceField(
        queryset=Seccion.objects.filter(esta_eliminado=False).select_related('grado'),
        required=False,
        label='Sección Específica (Opcional)',
        help_text='Déjelo en blanco si el cobro aplica a todas las secciones del grado.'
    )
    monto_override = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        max_value=Decimal('99999999.99'),
        required=False,
        label='Monto Personalizado (Q) (Opcional)',
        help_text='Dejar en blanco para usar el monto estándar del concepto.',
        widget=forms.NumberInput(attrs={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0.01',
            'max': '99999999.99',
        }),
    )
    fecha_limite_pago = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha Límite de Pago'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True, esta_eliminado=False)
            self.fields['ciclo_escolar'].initial = ciclo_activo
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            pass

    def clean(self):
        cleaned_data = super().clean()
        grado = cleaned_data.get('grado')
        seccion = cleaned_data.get('seccion')
        if grado and seccion and seccion.grado != grado:
            self.add_error(
                'seccion',
                f'La sección "{seccion.letra}" pertenece a "{seccion.grado.nombre}", no al grado seleccionado "{grado.nombre}".'
            )
        return cleaned_data


class AbonoForm(TailwindFormMixin, forms.ModelForm):
    """
    Formulario para el registro de un abono/pago parcial o total contra una CuentaPorCobrar.
    Soporta pagos en Efectivo (con correlativo institucional automático) y Depósitos Bancarios.
    """

    class Meta:
        model = Abono
        fields = ['metodo_pago', 'monto_pagado', 'fecha_pago', 'numero_boleta', 'observaciones']
        labels = {
            'metodo_pago': 'Método de Pago',
            'monto_pagado': 'Monto a Abonar / Pagado (Q)',
            'fecha_pago': 'Fecha del Pago / Depósito',
            'numero_boleta': 'No. de Boleta Bancaria / Referencia',
            'observaciones': 'Observaciones o Notas de Receptoría',
        }
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
            'numero_boleta': forms.TextInput(attrs={
                'maxlength': '30',
                'placeholder': 'Ej. BOL-2026-98765 (Opcional si es efectivo)',
            }),
            'monto_pagado': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'max': '99999999.99',
            }),
            'observaciones': forms.Textarea(attrs={
                'rows': 2,
                'maxlength': '300',
                'placeholder': 'Notas adicionales de receptoría o comprobante...',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.cuenta_por_cobrar = kwargs.pop('cuenta_por_cobrar', None)
        super().__init__(*args, **kwargs)
        # por defecto, fecha de hoy si no viene establecida
        if not self.is_bound and not self.initial.get('fecha_pago'):
            from django.utils import timezone
            self.initial['fecha_pago'] = timezone.now().date()
        # si la cuenta tiene saldo pendiente, sugerir el monto total restante
        if not self.is_bound and self.cuenta_por_cobrar:
            self.initial['monto_pagado'] = self.cuenta_por_cobrar.saldo_pendiente

    def clean_monto_pagado(self):
        monto = self.cleaned_data.get('monto_pagado')
        if monto is not None and monto <= Decimal('0.00'):
            raise forms.ValidationError('El monto del abono debe ser mayor a Q0.00.')

        if self.cuenta_por_cobrar and monto is not None:
            saldo = self.cuenta_por_cobrar.saldo_pendiente
            if monto > saldo:
                raise forms.ValidationError(
                    f'El monto abonado (Q{monto}) no puede ser mayor al saldo pendiente acumulado (Q{saldo}).'
                )
        return monto

    def clean_numero_boleta(self):
        boleta = self.cleaned_data.get('numero_boleta')
        if boleta:
            boleta = limpiar_texto_longitud(
                boleta.upper(),
                nombre_campo='El número de boleta o comprobante',
                min_length=2,
                max_length=30,
                obligatorio=False,
            )
            qs = Abono.objects.filter(numero_boleta__iexact=boleta, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'El número de boleta o comprobante "{boleta}" ya fue registrado previamente en el sistema.'
                )
        return boleta or ''

    def clean(self):
        cleaned_data = super().clean()
        metodo = cleaned_data.get('metodo_pago')
        boleta = cleaned_data.get('numero_boleta')

        if metodo in [MetodoPagoChoices.DEPOSITO, MetodoPagoChoices.TRANSFERENCIA] and not boleta:
            self.add_error(
                'numero_boleta',
                'Para depósitos bancarios o transferencias, el número de boleta o referencia bancaria es obligatorio.'
            )
        return cleaned_data

    def clean_observaciones(self):
        obs = self.cleaned_data.get('observaciones')
        if obs:
            return limpiar_texto_longitud(obs, 'Las observaciones', min_length=2, max_length=300)
        return ''
