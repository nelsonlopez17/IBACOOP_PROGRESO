"""
APPS/financiero/forms.py

Formularios para el módulo financiero del Instituto El Progreso.
Hereda de TailwindFormMixin (APPS.core.forms) para coherencia de estilos visuales.
"""
from decimal import Decimal
from django import forms

from APPS.core.forms import TailwindFormMixin
from APPS.financiero.models import ConceptoPago, CuentaPorCobrar, Abono, BecaDescuento
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
            'motivo_convenio': forms.TextInput(attrs={'placeholder': 'Ej. Hijo de Cooperativista (20% desc), Beca Académica'}),
            'porcentaje_descuento': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0', 'max': '100'}),
            'monto_descuento_fijo': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
        }


class ConceptoPagoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para crear y editar conceptos de pago en el catálogo."""

    class Meta:
        model = ConceptoPago
        fields = ['nombre', 'monto_estandar', 'categoria_concepto', 'aplica_al_inscribir_seccion']
        labels = {
            'nombre': 'Nombre del Concepto de Cobro',
            'monto_estandar': 'Monto Estándar (Q)',
            'categoria_concepto': 'Categoría del Concepto',
            'aplica_al_inscribir_seccion': '¿Generar automáticamente al matricular al alumno en una Sección?',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej. Inscripción Ciclo 2026, Colegiatura Mensual, Acto de Graduación'}),
            'monto_estandar': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            nombre = nombre.strip()
            qs = ConceptoPago.objects.filter(nombre__iexact=nombre, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Ya existe un concepto de pago registrado con este nombre.')
        return nombre

    def clean_monto_estandar(self):
        monto = self.cleaned_data.get('monto_estandar')
        if monto is not None and monto < Decimal('0.00'):
            raise forms.ValidationError('El monto del concepto no puede ser negativo.')
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
            'monto_total': 'Monto a Cobrar (Q)',
            'fecha_limite_pago': 'Fecha Límite de Pago (Opcional)',
        }
        widgets = {
            'fecha_limite_pago': forms.DateInput(attrs={'type': 'date'}),
            'monto_total': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo estudiantes y ciclos activos
        self.fields['estudiante'].queryset = Estudiante.objects.filter(
            persona__esta_eliminado=False,
            estado_estudiante='ACTIVO'
        ).select_related('persona').order_by('persona__apellidos', 'persona__nombres')
        
        self.fields['ciclo_escolar'].queryset = CicloEscolar.objects.filter(esta_eliminado=False)
        self.fields['concepto'].queryset = ConceptoPago.objects.filter(esta_eliminado=False)

        # Si se selecciona un concepto por JS/default, autocompletar el monto
        if not self.is_bound and self.initial.get('concepto'):
            try:
                c = ConceptoPago.objects.get(pk=self.initial.get('concepto'))
                self.initial['monto_total'] = c.monto_estandar
            except ConceptoPago.DoesNotExist:
                pass


class GenerarCobroMasivoForm(TailwindFormMixin, forms.Form):
    """
    Formulario para la emisión masiva de cobros por Grado, Sección o a todos los alumnos activos.
    Permite generar deudas masivas como Inscripción, Colegiatura del Mes o Acto de Graduación para 3ro Básico.
    """

    concepto = forms.ModelChoiceField(
        queryset=ConceptoPago.objects.filter(esta_eliminado=False),
        label='Concepto de Cobro',
        help_text='Seleccione el arancel o actividad a cobrar.'
    )
    ciclo_escolar = forms.ModelChoiceField(
        queryset=CicloEscolar.objects.filter(esta_eliminado=False),
        label='Ciclo Escolar Activo'
    )
    grado = forms.ModelChoiceField(
        queryset=Grado.objects.filter(esta_eliminado=False),
        required=False,
        label='Grado Destinatario (Opcional)',
        help_text='Déjelo en blanco si el cobro aplica a todos los grados.'
    )
    seccion = forms.ModelChoiceField(
        queryset=Seccion.objects.filter(esta_eliminado=False),
        required=False,
        label='Sección Específica (Opcional)',
        help_text='Déjelo en blanco si el cobro aplica a todas las secciones del grado.'
    )
    monto_override = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label='Monto Personalizado (Q) (Opcional)',
        help_text='Dejar en blanco para usar el monto estándar del concepto.'
    )
    fecha_limite_pago = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha Límite de Pago'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True)
            self.fields['ciclo_escolar'].initial = ciclo_activo
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            pass


class AbonoForm(TailwindFormMixin, forms.ModelForm):
    """
    Formulario para el registro de un abono/pago parcial o total contra una CuentaPorCobrar.
    """

    class Meta:
        model = Abono
        fields = ['monto_pagado', 'fecha_pago', 'numero_boleta', 'observaciones']
        labels = {
            'monto_pagado': 'Monto a Abonar / Pagado (Q)',
            'fecha_pago': 'Fecha del Depósito / Pago',
            'numero_boleta': 'Número de Boleta Bancaria / Referencia',
            'observaciones': 'Observaciones o Notas de Receptoría',
        }
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
            'numero_boleta': forms.TextInput(attrs={'placeholder': 'Ej. BOL-2026-98765'}),
            'monto_pagado': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0.01'}),
            'observaciones': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ej. Depósito Banco Industrial / Pago en efectivo en caja...'}),
        }

    def __init__(self, *args, **kwargs):
        self.cuenta_por_cobrar = kwargs.pop('cuenta_por_cobrar', None)
        super().__init__(*args, **kwargs)

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
            boleta = boleta.strip().upper()
            qs = Abono.objects.filter(numero_boleta__iexact=boleta, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'El número de boleta "{boleta}" ya fue registrado previamente en el sistema.'
                )
        return boleta
