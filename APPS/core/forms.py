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
                campos_buscables = {
                    'estudiante', 'personal', 'encargado', 'personal_responsable',
                    'personal_reporta', 'docente', 'articulo', 'cuenta', 'cobro',
                    'concepto', 'proveedor', 'usuario'
                }
                es_relacion_buscable = (
                    name in campos_buscables or
                    name.endswith('_estudiante') or
                    name.endswith('_personal') or
                    getattr(field, 'searchable', False)
                )
                clases = (
                    'w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg '
                    'text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#1E6532] '
                    'focus:border-[#1E6532] transition-colors shadow-sm text-sm'
                )
                if es_relacion_buscable:
                    clases += ' searchable-select'
                    field.widget.attrs['data-searchable'] = 'true'
                    label_texto = str(field.label) if field.label else name
                    field.widget.attrs['data-placeholder'] = f"Buscar {label_texto} por nombre, CUI/DPI o código..."
                field.widget.attrs['class'] = clases
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

    def is_valid(self):
        valid = super().is_valid()
        if not valid:
            for field_name in self.errors:
                if field_name in self.fields:
                    field = self.fields[field_name]
                    field.widget.attrs['aria-invalid'] = 'true'
                    clase_actual = field.widget.attrs.get('class', '')
                    clase_actual = clase_actual.replace('border-slate-300', 'border-rose-500 focus:ring-rose-500 focus:border-rose-500')
                    if 'border-rose-500' not in clase_actual:
                        clase_actual += ' border-rose-500'
                    field.widget.attrs['class'] = clase_actual
        return valid

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
            'genero',
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
            'genero': 'Género',
            'direccion': 'Dirección Domiciliar',
            'telefono_principal': 'Teléfono Principal',
            'telefono_secundario': 'Teléfono Secundario',
            'correo': 'Correo Electrónico de Contacto',
        }
        widgets = {
            'cui': forms.TextInput(attrs={'minlength': '13', 'maxlength': '13'}),
            'nombres': forms.TextInput(attrs={'minlength': '2', 'maxlength': '100'}),
            'apellidos': forms.TextInput(attrs={'minlength': '2', 'maxlength': '100'}),
            'telefono_principal': forms.TextInput(attrs={'minlength': '8', 'maxlength': '8'}),
            'telefono_secundario': forms.TextInput(attrs={'minlength': '8', 'maxlength': '8'}),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'direccion': forms.Textarea(attrs={'rows': 2, 'maxlength': '300'}),
        }

    def clean_cui(self):
        cui = self.cleaned_data.get('cui')
        if cui:
            cui = cui.strip()
            if len(cui) != 13 or not cui.isdigit():
                raise forms.ValidationError('El CUI/DPI debe contener exactamente 13 dígitos numéricos.')
        return cui

    def clean_nombres(self):
        nombres = self.cleaned_data.get('nombres')
        if nombres:
            nombres = nombres.strip()
            if any(c.isdigit() for c in nombres):
                raise forms.ValidationError('Los nombres no pueden contener números.')
        return nombres

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get('apellidos')
        if apellidos:
            apellidos = apellidos.strip()
            if any(c.isdigit() for c in apellidos):
                raise forms.ValidationError('Los apellidos no pueden contener números.')
        return apellidos

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if correo:
            correo = correo.strip().lower()
            qs = Persona.objects.filter(correo__iexact=correo, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Este correo electrónico ya está registrado en el sistema para otra persona.')
        return correo

    def clean_fecha_nacimiento(self):
        from datetime import date
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha:
            if fecha > date.today():
                raise forms.ValidationError('La fecha de nacimiento no puede ser una fecha futura.')
        return fecha

    def clean_telefono_principal(self):
        tel = self.cleaned_data.get('telefono_principal')
        if tel:
            digits = ''.join(c for c in tel if c.isdigit())
            if len(digits) != 8:
                raise forms.ValidationError('El número de teléfono en Guatemala debe contener exactamente 8 dígitos numéricos.')
            return digits
        return tel

