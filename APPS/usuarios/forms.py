"""
Formularios para la creación, edición, autoservicio de perfil y seguridad de usuarios.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from APPS.usuarios.models import Usuario
from APPS.core.models import Persona


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
            elif widget_type == 'CheckboxSelectMultiple':
                pass
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
            'debe_cambiar_password',
            'groups',
        )
        widgets = {
            'groups': forms.CheckboxSelectMultiple,
        }
        labels = {
            'username': 'Nombre de Usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo Electrónico',
            'rol': 'Tipo de perfil visual',
            'is_active': '¿Usuario Activo?',
            'debe_cambiar_password': 'Obligar cambio de contraseña al ingresar',
            'groups': 'Grupos de Permisos (Seguridad)',
        }
        help_texts = {
            'rol': 'Permite mostrar la etiqueta y color según la función en la institución.',
            'groups': 'Marque las casillas para agregar grupos de permisos al usuario.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilos_tailwind()


class CustomUserChangeForm(TailwindFormMixin, UserChangeForm):
    """Formulario para editar la información de un usuario por parte de un Administrador."""

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
            'debe_cambiar_password',
            'groups',
        )
        widgets = {
            'groups': forms.CheckboxSelectMultiple,
        }
        labels = {
            'username': 'Nombre de Usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo Electrónico',
            'rol': 'Rol',
            'is_active': '¿Usuario Activo?',
            'debe_cambiar_password': 'Obligar cambio de contraseña al ingresar',
            'groups': 'Grupos de Permisos (Seguridad)',
        }
        help_texts = {
            'rol': 'Permite mostrar la etiqueta y color según la función en la institución.',
            'groups': 'Marque las casillas para agregar grupos de permisos al usuario.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilos_tailwind()


class MiPerfilContactoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario de autoservicio para que el usuario edite sus datos de contacto."""

    class Meta:
        model = Persona
        fields = [
            'telefono_principal',
            'telefono_secundario',
            'correo',
            'direccion',
        ]
        labels = {
            'telefono_principal': 'Teléfono Principal',
            'telefono_secundario': 'Teléfono Secundario (Emergencia)',
            'correo': 'Correo Electrónico de Contacto',
            'direccion': 'Dirección Domiciliar',
        }
        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilos_tailwind()


class MiPasswordChangeForm(TailwindFormMixin, PasswordChangeForm):
    """Formulario con estilos Tailwind para que el usuario actualice su clave de acceso."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilos_tailwind()
