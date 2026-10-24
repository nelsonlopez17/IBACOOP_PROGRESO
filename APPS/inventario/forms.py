"""
APPS/inventario/forms.py

Formularios para el Módulo de Inventario y Control de Activos.
Utiliza TailwindFormMixin para estilizado corporativo continuo con Tailwind CSS v4 y DaisyUI
y validaciones de longitud y stock alineadas con la BD.
"""
from django import forms
from django.utils import timezone
from APPS.core.forms import TailwindFormMixin
from APPS.core.validadores import limpiar_texto_longitud
from APPS.inventario.models import ArticuloInventario, MovimientoInventario, TipoMovimientoChoices
from APPS.rrhh.models import Personal


class ArticuloInventarioForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para la creación y edición de artículos en el catálogo de inventario."""

    class Meta:
        model = ArticuloInventario
        fields = [
            'codigo_unico',
            'nombre',
            'descripcion',
            'categoria',
            'stock_actual',
            'stock_minimo_alerta',
            'unidad_medida',
        ]
        labels = {
            'codigo_unico': 'Código Único / Correlativo',
            'nombre': 'Nombre del Artículo / Bien',
            'descripcion': 'Descripción Detallada',
            'categoria': 'Categoría de Inventario',
            'stock_actual': 'Stock Inicial / Actual',
            'stock_minimo_alerta': 'Stock Mínimo de Alerta',
            'unidad_medida': 'Unidad de Medida (ej. unidades, cajas, resmas)',
        }
        widgets = {
            'codigo_unico': forms.TextInput(attrs={
                'minlength': '3',
                'maxlength': '30',
                'placeholder': 'Ej. EQ-TEC-2026-001',
            }),
            'nombre': forms.TextInput(attrs={
                'minlength': '3',
                'maxlength': '150',
                'placeholder': 'Nombre descriptivo del artículo o equipo',
            }),
            'descripcion': forms.Textarea(attrs={
                'rows': 3,
                'maxlength': '500',
                'placeholder': 'Especificaciones, marca, estado o detalles del bien (máx. 500 caracteres)...',
            }),
            'stock_actual': forms.NumberInput(attrs={
                'min': '0',
                'max': '999999',
                'step': '1',
            }),
            'stock_minimo_alerta': forms.NumberInput(attrs={
                'min': '0',
                'max': '999999',
                'step': '1',
            }),
            'unidad_medida': forms.TextInput(attrs={
                'minlength': '2',
                'maxlength': '20',
                'placeholder': 'unidades',
            }),
        }

    def clean_codigo_unico(self):
        codigo = self.cleaned_data.get('codigo_unico')
        if codigo:
            codigo = limpiar_texto_longitud(
                codigo.upper(),
                nombre_campo='El código único',
                min_length=3,
                max_length=30,
                obligatorio=True,
            )
            qs = ArticuloInventario.objects.filter(codigo_unico__iexact=codigo, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('El código único ingresado ya pertenece a otro artículo del inventario.')
        return codigo

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            return limpiar_texto_longitud(
                nombre,
                nombre_campo='El nombre del artículo',
                min_length=3,
                max_length=150,
                obligatorio=True,
                evitar_solo_numeros=True,
            )
        return nombre

    def clean_descripcion(self):
        desc = self.cleaned_data.get('descripcion')
        if desc:
            return limpiar_texto_longitud(desc, 'La descripción del artículo', min_length=3, max_length=500)
        return ''

    def clean_unidad_medida(self):
        unidad = self.cleaned_data.get('unidad_medida')
        if unidad:
            return limpiar_texto_longitud(
                unidad,
                nombre_campo='La unidad de medida',
                min_length=2,
                max_length=20,
                obligatorio=True,
                evitar_solo_numeros=True,
            )
        return unidad

    def clean_stock_actual(self):
        stock = self.cleaned_data.get('stock_actual')
        if stock is not None and (stock < 0 or stock > 999999):
            raise forms.ValidationError('El stock inicial o actual debe estar entre 0 y 999,999.')
        return stock

    def clean_stock_minimo_alerta(self):
        stock_min = self.cleaned_data.get('stock_minimo_alerta')
        if stock_min is not None and (stock_min < 0 or stock_min > 999999):
            raise forms.ValidationError('El stock mínimo de alerta debe estar entre 0 y 999,999.')
        return stock_min


class MovimientoInventarioForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para registrar transacciones de entrada, salida, asignación o ajuste de stock."""

    class Meta:
        model = MovimientoInventario
        fields = [
            'articulo',
            'personal_responsable',
            'tipo_movimiento',
            'cantidad',
            'motivo',
            'documento_referencia',
        ]
        labels = {
            'articulo': 'Artículo de Inventario',
            'personal_responsable': 'Personal Responsable / Solicitante',
            'tipo_movimiento': 'Tipo de Transacción',
            'cantidad': 'Cantidad',
            'motivo': 'Motivo o Destino del Movimiento',
            'documento_referencia': 'Documento de Referencia (Vales / Facturas / Contratos)',
        }
        widgets = {
            'cantidad': forms.NumberInput(attrs={
                'min': '1',
                'max': '999999',
                'step': '1',
            }),
            'motivo': forms.Textarea(attrs={
                'rows': 3,
                'minlength': '5',
                'maxlength': '500',
                'placeholder': 'Justifique el consumo, asignación, entrada o baja del bien (5 a 500 caracteres)...',
            }),
            'documento_referencia': forms.TextInput(attrs={
                'maxlength': '50',
                'placeholder': 'Ej. Orden de Compra #4521 / Acta #04',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['personal_responsable'].queryset = Personal.objects.filter(
            esta_eliminado=False,
            estado_laboral='ACTIVO'
        ).select_related('persona', 'puesto').order_by('persona__apellidos')
        self.fields['articulo'].queryset = ArticuloInventario.objects.filter(
            esta_eliminado=False
        ).order_by('nombre')

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is not None and (cantidad <= 0 or cantidad > 999999):
            raise forms.ValidationError('La cantidad a registrar debe ser un entero positivo entre 1 y 999,999.')
        return cantidad

    def clean_motivo(self):
        motivo = self.cleaned_data.get('motivo')
        if motivo:
            return limpiar_texto_longitud(
                motivo,
                nombre_campo='El motivo del movimiento',
                min_length=5,
                max_length=500,
                obligatorio=True,
            )
        return motivo

    def clean_documento_referencia(self):
        doc = self.cleaned_data.get('documento_referencia')
        if doc:
            return limpiar_texto_longitud(doc, 'El documento de referencia', min_length=2, max_length=50)
        return ''

    def clean(self):
        cleaned_data = super().clean()
        articulo = cleaned_data.get('articulo')
        tipo_movimiento = cleaned_data.get('tipo_movimiento')
        cantidad = cleaned_data.get('cantidad')

        if articulo and tipo_movimiento and cantidad:
            # verificar existencia suficiente en inventario para egresos y bajas
            if tipo_movimiento in [
                TipoMovimientoChoices.SALIDA,
                TipoMovimientoChoices.ASIGNACION,
                TipoMovimientoChoices.BAJA
            ]:
                if cantidad > articulo.stock_actual:
                    self.add_error(
                        'cantidad',
                        f'Stock insuficiente para "{articulo.nombre}". '
                        f'Stock actual disponible: {articulo.stock_actual} {articulo.unidad_medida}. '
                        f'Intenta descontar {cantidad} {articulo.unidad_medida}.'
                    )
        return cleaned_data
