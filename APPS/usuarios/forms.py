"""
Formularios para la creación, edición, autoservicio de perfil y seguridad de usuarios.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import Group
from APPS.usuarios.models import Usuario
from APPS.core.models import Persona
from APPS.core.forms import TailwindFormMixin
from APPS.core.validadores import limpiar_telefono_guatemala, limpiar_texto_longitud


class CustomUserCreationForm(TailwindFormMixin, UserCreationForm):
    """Formulario para registrar un nuevo usuario."""

    first_name = forms.CharField(
        max_length=100,
        min_length=2,
        required=False,
        label='Nombres',
        widget=forms.TextInput(attrs={'minlength': '2', 'maxlength': '100'}),
    )
    last_name = forms.CharField(
        max_length=100,
        min_length=2,
        required=False,
        label='Apellidos',
        widget=forms.TextInput(attrs={'minlength': '2', 'maxlength': '100'}),
    )

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
            'username': forms.TextInput(attrs={'minlength': '3', 'maxlength': '150'}),
            'email': forms.EmailInput(attrs={'maxlength': '254'}),
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
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        if self.current_user and not self.current_user.is_superuser:
            if 'groups' in self.fields:
                del self.fields['groups']
        for pwd_field in ('password1', 'password2'):
            if pwd_field in self.fields:
                self.fields[pwd_field].widget.attrs.update({
                    'minlength': '8',
                    'maxlength': '128',
                })
        self._aplicar_estilos_tailwind()

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3 or len(username) > 150:
            raise forms.ValidationError('El nombre de usuario debe tener entre 3 y 150 caracteres.')
        return username

    def clean_first_name(self):
        val = self.cleaned_data.get('first_name', '')
        if val:
            return limpiar_texto_longitud(val, 'Los nombres', min_length=2, max_length=100, evitar_solo_numeros=True)
        return val

    def clean_last_name(self):
        val = self.cleaned_data.get('last_name', '')
        if val:
            return limpiar_texto_longitud(val, 'Los apellidos', min_length=2, max_length=100, evitar_solo_numeros=True)
        return val

    def save(self, commit=True):
        if 'groups' in self.fields:
            self.instance._omitir_sincronizacion_grupo = True
        user = super().save(commit=commit)
        if commit and user.rol and 'groups' not in self.fields:
            from APPS.usuarios.permisos import sincronizar_grupo_usuario
            sincronizar_grupo_usuario(user)
        return user


class CustomUserChangeForm(TailwindFormMixin, UserChangeForm):
    """Formulario para editar la información de un usuario por parte de un Administrador."""

    password = None  # No se modifica la contraseña directamente en este formulario
    first_name = forms.CharField(
        max_length=100,
        min_length=2,
        required=False,
        label='Nombres',
        widget=forms.TextInput(attrs={'minlength': '2', 'maxlength': '100'}),
    )
    last_name = forms.CharField(
        max_length=100,
        min_length=2,
        required=False,
        label='Apellidos',
        widget=forms.TextInput(attrs={'minlength': '2', 'maxlength': '100'}),
    )

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
            'username': forms.TextInput(attrs={'minlength': '3', 'maxlength': '150'}),
            'email': forms.EmailInput(attrs={'maxlength': '254'}),
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
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        if self.current_user and not self.current_user.is_superuser:
            if 'groups' in self.fields:
                del self.fields['groups']

        # el nombre de usuario permanece inmutable por trazabilidad
        if 'username' in self.fields:
            self.fields['username'].disabled = True
            self.fields['username'].help_text = (
                'El nombre de usuario es inmutable por trazabilidad y seguridad. '
                'En cuentas vinculadas a expediente oficial, se sincroniza con el CUI.'
            )

        # si el usuario tiene expediente asociado los nombres se gestionan en su modulo
        tiene_persona = False
        if self.instance and self.instance.pk:
            try:
                tiene_persona = bool(self.instance.persona)
            except Exception:
                tiene_persona = False

        if tiene_persona:
            for campo in ('first_name', 'last_name', 'email'):
                if campo in self.fields:
                    self.fields[campo].disabled = True
                    self.fields[campo].help_text = (
                        'Dato sincronizado desde su expediente oficial (Persona). '
                        'Modifíquelo en el módulo correspondiente (Estudiantes o RRHH).'
                    )

        # impedir que el usuario autenticado desactive su propia cuenta
        if self.current_user and self.instance and self.instance.pk == self.current_user.pk:
            if 'is_active' in self.fields:
                self.fields['is_active'].disabled = True
                self.fields['is_active'].help_text = (
                    'No puede desactivar su propia cuenta mientras tiene una sesión activa.'
                )

        self._aplicar_estilos_tailwind()

        # apariencia visual de solo lectura para campos deshabilitados
        for field in self.fields.values():
            if field.disabled:
                clases = field.widget.attrs.get('class', '')
                if field.widget.__class__.__name__ == 'CheckboxInput':
                    field.widget.attrs['class'] = f"{clases} opacity-60 cursor-not-allowed".strip()
                else:
                    clases = clases.replace('bg-white', 'bg-slate-100 text-slate-500 cursor-not-allowed')
                    field.widget.attrs['class'] = clases

    def clean_username(self):
        if self.instance and self.instance.pk:
            return self.instance.username
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3 or len(username) > 150:
            raise forms.ValidationError('El nombre de usuario debe tener entre 3 y 150 caracteres.')
        return username

    def clean_first_name(self):
        val = self.cleaned_data.get('first_name', '')
        if val:
            return limpiar_texto_longitud(val, 'Los nombres', min_length=2, max_length=100, evitar_solo_numeros=True)
        return val

    def clean_last_name(self):
        val = self.cleaned_data.get('last_name', '')
        if val:
            return limpiar_texto_longitud(val, 'Los apellidos', min_length=2, max_length=100, evitar_solo_numeros=True)
        return val

    def save(self, commit=True):
        if 'groups' in self.fields:
            self.instance._omitir_sincronizacion_grupo = True
        user = super().save(commit=commit)
        if commit and user.rol and 'groups' not in self.fields:
            from APPS.usuarios.permisos import sincronizar_grupo_usuario
            sincronizar_grupo_usuario(user)
        return user


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
            'telefono_principal': 'Teléfono Principal (8 dígitos)',
            'telefono_secundario': 'Teléfono Secundario (Emergencia)',
            'correo': 'Correo Electrónico de Contacto',
            'direccion': 'Dirección Domiciliar',
        }
        widgets = {
            'telefono_principal': forms.TextInput(attrs={
                'minlength': '8',
                'maxlength': '8',
                'pattern': r'\d{8}',
                'inputmode': 'numeric',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 8)",
                'placeholder': 'Ej. 55551234',
                'title': 'Ingrese un número telefónico de Guatemala de exactamente 8 dígitos numéricos.',
            }),
            'telefono_secundario': forms.TextInput(attrs={
                'minlength': '8',
                'maxlength': '8',
                'pattern': r'\d{8}',
                'inputmode': 'numeric',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 8)",
                'placeholder': 'Ej. 44445678',
                'title': 'Ingrese un número telefónico de Guatemala de exactamente 8 dígitos numéricos.',
            }),
            'correo': forms.EmailInput(attrs={
                'maxlength': '254',
                'placeholder': 'ejemplo@correo.com',
            }),
            'direccion': forms.Textarea(attrs={
                'rows': 2,
                'maxlength': '300',
                'placeholder': 'Aldea, caserío, barrio o zona, municipio y departamento',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilos_tailwind()

    def clean_telefono_principal(self):
        tel = self.cleaned_data.get('telefono_principal')
        if tel:
            return limpiar_telefono_guatemala(tel)
        return tel

    def clean_telefono_secundario(self):
        tel = self.cleaned_data.get('telefono_secundario')
        if tel:
            return limpiar_telefono_guatemala(tel)
        return tel

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if correo:
            correo = correo.strip().lower()
            if len(correo) > 254:
                raise forms.ValidationError('El correo electrónico no puede exceder los 254 caracteres.')
            qs = Persona.objects.filter(correo__iexact=correo, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Este correo electrónico ya está registrado en el sistema para otra persona.')
        return correo

    def clean_direccion(self):
        direccion = self.cleaned_data.get('direccion')
        if direccion:
            return limpiar_texto_longitud(
                direccion,
                nombre_campo='La dirección domiciliar',
                min_length=3,
                max_length=300,
                obligatorio=False,
            )
        return ''


class MiPasswordChangeForm(TailwindFormMixin, PasswordChangeForm):
    """Formulario con estilos Tailwind para que el usuario actualice su clave de acceso."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'old_password' in self.fields:
            self.fields['old_password'].widget.attrs['maxlength'] = '128'
        for pwd_field in ('new_password1', 'new_password2'):
            if pwd_field in self.fields:
                self.fields[pwd_field].widget.attrs.update({
                    'minlength': '8',
                    'maxlength': '128',
                })
        self._aplicar_estilos_tailwind()



class GrupoPermisosForm(TailwindFormMixin, forms.ModelForm):
    """
    Formulario intuitivo para crear y actualizar Grupos de Permisos / Roles del sistema.
    """
    name = forms.CharField(
        label='Nombre del Rol / Grupo',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ej. Coordinador Académico de Nivel Básico',
            'minlength': '3',
            'maxlength': '150',
        }),
        help_text='Nombre descriptivo del rol o perfil de acceso dentro de la institución.'
    )

    class Meta:
        model = Group
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from APPS.usuarios.permisos import es_grupo_base_protegido
        self._es_base = False
        if self.instance and self.instance.pk:
            self._es_base = es_grupo_base_protegido(self.instance.name)
            if self._es_base:
                self.fields['name'].help_text = (
                    'Este es un rol institucional base del sistema. '
                    'Su nombre no puede modificarse para preservar la integridad operativa, pero puede ajustar libremente su lista de permisos.'
                )
                self.fields['name'].widget.attrs['readonly'] = True
        self._aplicar_estilos_tailwind()

    def clean_name(self):
        nombre = self.cleaned_data.get('name', '').strip()
        if not nombre:
            raise forms.ValidationError('El nombre del rol es obligatorio.')
        if len(nombre) < 3:
            raise forms.ValidationError('El nombre debe contener al menos 3 caracteres.')

        if self.instance and self.instance.pk and self._es_base:
            return self.instance.name

        qs = Group.objects.filter(name__iexact=nombre)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Ya existe un rol o grupo con el nombre '{nombre}'. Ingrese uno diferente.")
        return nombre
