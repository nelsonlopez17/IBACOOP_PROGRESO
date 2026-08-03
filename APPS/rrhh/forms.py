"""
APPS/rrhh/forms.py

Formularios para la contratación y gestión de Personal laboral del Instituto El Progreso.
Hereda de TailwindFormMixin (APPS.core.forms) para la inyección de estilos corporativos.
"""
from django import forms
from APPS.core.forms import TailwindFormMixin
from APPS.rrhh.models import Personal, Puesto


class PersonalForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para capturar los datos laborales y contratación de un miembro del Personal."""

    class Meta:
        model = Personal
        fields = [
            'puesto',
            'nit',
            'fecha_contratacion',
            'estado_laboral',
            'salario_base_asignado',
        ]
        labels = {
            'puesto': 'Puesto o Cargo Asignado',
            'nit': 'NIT (Número de Identificación Tributaria)',
            'fecha_contratacion': 'Fecha de Contratación',
            'estado_laboral': 'Estado Laboral',
            'salario_base_asignado': 'Salario Base Mensual (Q)',
        }
        widgets = {
            'fecha_contratacion': forms.DateInput(attrs={'type': 'date'}),
        }
