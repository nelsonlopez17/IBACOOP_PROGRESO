"""
APPS/estudiantes/forms.py

Formularios para el registro y gestión de Estudiantes y Encargados.
Hereda de TailwindFormMixin (APPS.core.forms) para la inyección automática de estilos visuales
y atributos HTML5 de longitud y formato para Guatemala.
"""
from django import forms
from APPS.core.forms import TailwindFormMixin, PersonaForm
from APPS.core.validadores import (
    limpiar_codigo_mineduc,
    limpiar_telefono_guatemala,
    limpiar_texto_longitud,
)
from APPS.estudiantes.models import Estudiante, Encargado, EstudianteEncargado
from APPS.academico.models import Seccion


class EstudianteForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para capturar los datos académicos y de expediente de un Estudiante."""

    _CAMPOS_PROPIEDADES = (
        'nombre_padre',
        'telefono_padre',
        'nombre_madre',
        'telefono_madre',
        'doc_cert_nacimiento_renap',
        'doc_dpi_encargado',
        'doc_certificado_grado_anterior',
        'doc_diploma_primaria',
        'doc_codigo_mineduc',
        'estado_activo',
    )

    seccion_asignada = forms.ModelChoiceField(
        queryset=Seccion.objects.filter(esta_eliminado=False).select_related('grado').order_by('grado__orden', 'letra'),
        required=False,
        label='Grado y Sección Académica Asignada (Inscripción Inmediata)',
        help_text='Seleccione para inscribir al estudiante en el Módulo Académico con 1 solo clic.'
    )
    nombre_padre = forms.CharField(
        min_length=3,
        max_length=150,
        required=False,
        label='Nombre Completo del Padre',
        widget=forms.TextInput(attrs={
            'minlength': '3',
            'maxlength': '150',
            'placeholder': 'Nombre completo del padre',
        }),
    )
    telefono_padre = forms.CharField(
        min_length=8,
        max_length=8,
        required=False,
        label='Teléfono del Padre (8 dígitos)',
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
    nombre_madre = forms.CharField(
        min_length=3,
        max_length=150,
        required=False,
        label='Nombre Completo de la Madre',
        widget=forms.TextInput(attrs={
            'minlength': '3',
            'maxlength': '150',
            'placeholder': 'Nombre completo de la madre',
        }),
    )
    telefono_madre = forms.CharField(
        min_length=8,
        max_length=8,
        required=False,
        label='Teléfono de la Madre (8 dígitos)',
        widget=forms.TextInput(attrs={
            'minlength': '8',
            'maxlength': '8',
            'pattern': r'\d{8}',
            'inputmode': 'numeric',
            'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 8)",
            'placeholder': 'Ej. 44445678',
            'title': 'Ingrese un número telefónico de Guatemala de exactamente 8 dígitos numéricos.',
        }),
    )
    doc_cert_nacimiento_renap = forms.BooleanField(
        required=False,
        label='Certificado de Nacimiento RENAP (con CUI)',
    )
    doc_dpi_encargado = forms.BooleanField(
        required=False,
        label='Fotocopia de DPI del Encargado / Padre',
    )
    doc_certificado_grado_anterior = forms.BooleanField(
        required=False,
        label='Certificado de Estudios del Grado Anterior',
    )
    doc_diploma_primaria = forms.BooleanField(
        required=False,
        label='Diploma de Educación Primaria (para 1ro Básico)',
    )
    doc_codigo_mineduc = forms.BooleanField(
        required=False,
        label='Constancia de Código Personal MINEDUC (SIRE)',
    )
    estado_activo = forms.BooleanField(
        required=False,
        initial=True,
        label='¿Estudiante Activo en el Instituto?',
    )

    class Meta:
        model = Estudiante
        fields = [
            'codigo_mineduc',
            'estado_estudiante',
            'encargado',
            'historial_medico',
        ]
        labels = {
            'codigo_mineduc': 'Código Oficial MINEDUC',
            'estado_estudiante': 'Estado Académico del Estudiante',
            'encargado': 'Padre de Familia o Encargado Principal',
            'historial_medico': 'Historial Médico / Observaciones de Salud',
        }
        widgets = {
            'codigo_mineduc': forms.TextInput(attrs={
                'minlength': '5',
                'maxlength': '15',
                'pattern': r'[A-Za-z0-9\-]{5,15}',
                'placeholder': 'Ej. E123ABC',
                'title': 'Código Personal MINEDUC (entre 5 y 15 caracteres alfanuméricos).',
            }),
            'historial_medico': forms.Textarea(attrs={
                'rows': 2,
                'maxlength': '500',
                'placeholder': 'Alergias, medicamentos, antecedentes u observaciones médicas (máx. 500 caracteres)...',
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

    def clean_codigo_mineduc(self):
        codigo = self.cleaned_data.get('codigo_mineduc')
        if codigo:
            codigo = limpiar_codigo_mineduc(codigo)
            qs = Estudiante.todos.filter(codigo_mineduc__iexact=codigo)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Este Código Personal MINEDUC ya está asignado a otro estudiante.')
        return codigo

    def clean_encargado(self):
        encargado = self.cleaned_data.get('encargado')
        if not encargado:
            raise forms.ValidationError('Debe seleccionar obligatoriamente un Padre de Familia o Encargado Principal para el estudiante.')
        return encargado

    def clean_nombre_padre(self):
        val = self.cleaned_data.get('nombre_padre')
        if val:
            return limpiar_texto_longitud(val, 'El nombre del padre', min_length=3, max_length=150, evitar_solo_numeros=True)
        return ''

    def clean_telefono_padre(self):
        tel = self.cleaned_data.get('telefono_padre')
        if tel:
            return limpiar_telefono_guatemala(tel)
        return ''

    def clean_nombre_madre(self):
        val = self.cleaned_data.get('nombre_madre')
        if val:
            return limpiar_texto_longitud(val, 'El nombre de la madre', min_length=3, max_length=150, evitar_solo_numeros=True)
        return ''

    def clean_telefono_madre(self):
        tel = self.cleaned_data.get('telefono_madre')
        if tel:
            return limpiar_telefono_guatemala(tel)
        return ''

    def clean_historial_medico(self):
        val = self.cleaned_data.get('historial_medico')
        if val:
            return limpiar_texto_longitud(val, 'El historial médico', min_length=3, max_length=500)
        return ''

    def save(self, commit=True):
        estudiante = super().save(commit=False)
        for campo in self._CAMPOS_PROPIEDADES:
            if campo in self.cleaned_data:
                setattr(estudiante, campo, self.cleaned_data[campo])
        if commit:
            estudiante.save()
        return estudiante


class EncargadoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para capturar los datos de un Padre de Familia o Encargado (Subtipo)."""

    class Meta:
        model = Encargado
        fields = [
            'lugar_de_trabajo',
        ]
        labels = {
            'lugar_de_trabajo': 'Lugar de trabajo / Empresa',
        }
        widgets = {
            'lugar_de_trabajo': forms.TextInput(attrs={
                'minlength': '2',
                'maxlength': '150',
                'placeholder': 'Ej. Cooperativa El Progreso, Comercio Propio, Agricultura...',
            }),
        }

    def clean_lugar_de_trabajo(self):
        val = self.cleaned_data.get('lugar_de_trabajo')
        if val:
            return limpiar_texto_longitud(val, 'El lugar de trabajo', min_length=2, max_length=150)
        return ''
