"""
Formularios para la creación y edición de usuarios en el sistema escolar.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from APPS.usuarios.models import Usuario


class TailwindFormMixin:
    """Clase auxiliar para aplicar los colores y diseño corporativo a los campos del formulario."""

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
            else:
                field.widget.attrs['class'] = (
                    'w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg '
                    'text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 '
                    'focus:ring-[#1E6532] focus:border-[#1E6532] transition-colors shadow-sm text-sm'
                )


class CustomUserCreationForm(TailwindFormMixin, UserCreationForm):
    """Formulario para registrar un nuevo usuario."""

    class Meta:
        model = Usuario
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'rol',
            'is_active',
            'groups',
        )
        labels = {
            'username': 'Nombre de Usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo Electrónico',
            'rol': 'Tipo de perfil visual',
            'is_active': '¿Usuario Activo?',
            'groups': 'Grupos de Permisos (Seguridad)',
        }
        help_texts = {
            'rol': 'Permite mostrar la etiqueta y color según la función en la institución.',
            'groups': 'Mantenga presionada la tecla Ctrl/Cmd para seleccionar múltiples grupos de permisos.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilos_tailwind()


class CustomUserChangeForm(TailwindFormMixin, UserChangeForm):
    """Formulario para editar la información de un usuario registrado."""

    password = None  # No se modifica la contraseña directamente en este formulario

    class Meta:
        model = Usuario
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'rol',
            'is_active',
            'groups',
        )
        labels = {
            'username': 'Nombre de Usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo Electrónico',
            'rol': 'Tipo de perfil visual',
            'is_active': '¿Usuario Activo?',
            'groups': 'Grupos de Permisos (Seguridad)',
        }
        help_texts = {
            'rol': 'Permite mostrar la etiqueta y color según la función en la institución.',
            'groups': 'Mantenga presionada la tecla Ctrl/Cmd para seleccionar múltiples grupos de permisos.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilos_tailwind()
