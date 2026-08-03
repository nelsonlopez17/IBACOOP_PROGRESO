"""
core/forms.py

Mixin reutilizable para la aplicación de estilos de Tailwind CSS v4 y DaisyUI
y Formulario base para el Supertipo Persona (APPS.core.models).
"""
from django import forms
from APPS.core.models import Persona


class TailwindFormMixin:
    """Clase auxiliar para aplicar estilos corporativos Tailwind a los campos del formulario."""

    def _aplicar_estilos_tailwind(self):
        for name, field in self.fields.items():
            widget_type = field.widget.__class__.__name__

            if widget_type == 'CheckboxInput':
                field.widget.attrs['class'] = (
                    'h-5 w-5 rounded border-slate-300 bg-white text-[#1E6532] '
                    'focus:ring-[#1E6532] focus:ring-offset-white cursor-pointer transition'
                )
            elif widget_type in ['Select', 'SelectMultiple']:
                field.widget.attrs['class'] = (
                    'w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg '
                    'text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1E6532] '
                    'focus:border-[#1E6532] transition-colors shadow-sm text-sm'
                )
            elif widget_type == 'DateInput':
                field.widget.attrs.update({
                    'type': 'date',
                    'class': (
                        'w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg '
                        'text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1E6532] '
                        'focus:border-[#1E6532] transition-colors shadow-sm text-sm'
                    )
                })
            else:
                field.widget.attrs['class'] = (
                    'w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg '
                    'text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 '
                    'focus:ring-[#1E6532] focus:border-[#1E6532] transition-colors shadow-sm text-sm'
                )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilos_tailwind()


class PersonaForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para la captura de información personal (Supertipo Persona)."""

    class Meta:
        model = Persona
        fields = [
            'cui',
            'nombres',
            'apellidos',
            'fecha_nacimiento',
            'direccion',
            'telefono_principal',
            'telefono_secundario',
            'correo',
        ]
        labels = {
            'cui': 'CUI / DPI (13 dígitos)',
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'direccion': 'Dirección Domiciliar',
            'telefono_principal': 'Teléfono Principal',
            'telefono_secundario': 'Teléfono Secundario',
            'correo': 'Correo Electrónico de Contacto',
        }
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'direccion': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_cui(self):
        cui = self.cleaned_data.get('cui')
        if cui:
            cui = cui.strip()
            if len(cui) != 13 or not cui.isdigit():
                raise forms.ValidationError('El CUI/DPI debe contener exactamente 13 dígitos numéricos.')
        return cui
