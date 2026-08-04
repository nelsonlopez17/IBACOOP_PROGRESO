"""
APPS/estudiantes/forms.py

Formularios para el registro y gestión de Estudiantes y Encargados.
Hereda de TailwindFormMixin (APPS.core.forms) para la inyección automática de estilos visuales.
"""
from django import forms
from APPS.core.forms import TailwindFormMixin, PersonaForm
from APPS.estudiantes.models import Estudiante, Encargado, EstudianteEncargado


class EstudianteForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para capturar los datos académicos de un Estudiante (Subtipo)."""

    class Meta:
        model = Estudiante
        fields = [
            'codigo_mineduc',
            'historial_medico',
            'estado_activo',
        ]
        labels = {
            'codigo_mineduc': 'Código Oficial MINEDUC',
            'historial_medico': 'Historial Médico / Padecimientos',
            'estado_activo': '¿Estudiante Activo en el Instituto?',
        }
        widgets = {
            'historial_medico': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Alergias, medicamentos, antecedentes u observaciones médicas...'}),
        }

    def clean_codigo_mineduc(self):
        codigo = self.cleaned_data.get('codigo_mineduc')
        if codigo:
            codigo = codigo.strip().upper()
        return codigo


class EncargadoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para capturar los datos de un Encargado / Tutor Legal (Subtipo)."""

    class Meta:
        model = Encargado
        fields = [
            'lugar_de_trabajo',
        ]
        labels = {
            'lugar_de_trabajo': 'Lugar de trabajo / Empresa',
        }
