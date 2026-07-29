"""
academico/forms.py

Formularios para la gestión académica del Instituto El Progreso.
"""
from django import forms
from APPS.academico.models import NotaBloque


class NotaBloqueForm(forms.ModelForm):
    """
    Formulario para el ingreso y actualización de notas por bloque.

    Solo expone los campos editables (nota_zona y nota_examen).
    Los demás campos (asignacion_estudiante, curso, bloque_academico)
    son de solo lectura y se asignan en la vista.

    Validación adicional:
        - nota_zona debe estar entre 0 y 60
        - nota_examen debe estar entre 0 y 40
    """
    class Meta:
        model = NotaBloque
        fields = ['nota_zona', 'nota_examen']
        widgets = {
            'nota_zona': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'max': '60',
                'step': '0.01',
                'placeholder': '0.00 – 60.00',
            }),
            'nota_examen': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'max': '40',
                'step': '0.01',
                'placeholder': '0.00 – 40.00',
            }),
        }
        labels = {
            'nota_zona': 'Nota de Zona (0 – 60 puntos)',
            'nota_examen': 'Nota de Examen (0 – 40 puntos)',
        }
        help_texts = {
            'nota_zona': 'Incluye parciales, tareas y actividades.',
            'nota_examen': 'Examen final del bloque académico.',
        }

    def clean_nota_zona(self):
        valor = self.cleaned_data.get('nota_zona')
        if valor is not None and (valor < 0 or valor > 60):
            raise forms.ValidationError(
                'La nota de zona debe estar entre 0 y 60 puntos (MINEDUC).'
            )
        return valor

    def clean_nota_examen(self):
        valor = self.cleaned_data.get('nota_examen')
        if valor is not None and (valor < 0 or valor > 40):
            raise forms.ValidationError(
                'La nota de examen debe estar entre 0 y 40 puntos (MINEDUC).'
            )
        return valor
