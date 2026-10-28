"""
usuarios/models.py

Define el modelo de Usuario personalizado del sistema.

ESTRATEGIA DE AUTENTICACIÓN:
  - El modelo hereda de AbstractUser para conservar toda la funcionalidad
    nativa de Django (login, passwords, grupos, permisos).
  - Se añade el campo `rol` para lógica visual en templates (ej. mostrar menús
    diferentes). NO se usa para control de acceso.
  - La seguridad real de vistas y APIs se maneja mediante Groups y Permissions
    nativos de Django (PermissionRequiredMixin, @permission_required, etc.).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


class RolChoices(models.TextChoices):
    """
    Roles disponibles en el sistema.

    IMPORTANTE: Estos roles son EXCLUSIVAMENTE para lógica visual en templates.
    La autorización real se gestiona via Groups y Permissions de Django.
    """
    ADMINISTRADOR = 'ADMINISTRADOR', 'Administrador'
    DIRECTOR      = 'DIRECTOR',      'Director'
    SECRETARIA    = 'SECRETARIA',    'Secretaría'
    CONTADOR      = 'CONTADOR',      'Contador'
    DOCENTE       = 'DOCENTE',       'Docente'
    ESTUDIANTE    = 'ESTUDIANTE',    'Estudiante'
    ENCARGADO     = 'ENCARGADO',     'Encargado'
    PERSONAL      = 'PERSONAL',      'Personal General'



class Usuario(AbstractUser):
    """
    Modelo de Usuario personalizado del Instituto El Progreso.

    Extiende AbstractUser añadiendo el campo `rol` para identificar
    visualmente el tipo de usuario dentro del sistema.

    Campos heredados de AbstractUser relevantes:
        - username, password, email
        - first_name, last_name
        - is_active, is_staff, is_superuser
        - groups (ManyToMany) → usado para permisos reales
        - user_permissions (ManyToMany) → permisos individuales
        - date_joined, last_login

    Nota: No hereda de ModeloAuditable porque AbstractUser ya provee
    date_joined y last_login como campos temporales.
    """
    rol = models.CharField(
        max_length=20,
        choices=RolChoices.choices,
        verbose_name='Rol en el sistema',
        blank=True,
        help_text=(
            'Rol visual del usuario. Úselo en templates para mostrar menús '
            'o secciones relevantes. NO lo use para control de acceso — '
            'use Groups y Permissions para eso.'
        ),
    )
    debe_cambiar_password = models.BooleanField(
        default=True,
        verbose_name='Debe cambiar contraseña',
        help_text='Obliga al usuario a cambiar su contraseña en su próximo inicio de sesión.'
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        nombre_completo = self.get_full_name()
        if nombre_completo:
            return f"{nombre_completo} ({self.get_rol_display() or self.username})"
        return self.username

    @property
    def nombre_completo(self):
        """Retorna el nombre completo del usuario o de la persona vinculada."""
        full = self.get_full_name()
        if full:
            return full
        try:
            if hasattr(self, 'persona') and self.persona and self.persona.nombre_completo:
                return self.persona.nombre_completo
        except Exception:
            pass
        return self.username

    @property
    def cui(self):
        """Retorna el CUI/DPI de la persona vinculada si existe."""
        try:
            if hasattr(self, 'persona') and self.persona and self.persona.cui:
                return self.persona.cui
        except Exception:
            pass
        return None

    @property
    def iniciales(self) -> str:
        """Retorna las iniciales del nombre y apellido del titular (ej. PA), o los 2 primeros caracteres del usuario."""
        if self.first_name and self.last_name:
            return f"{self.first_name.strip()[:1]}{self.last_name.strip()[:1]}".upper()
        try:
            if self.persona and self.persona.nombres and self.persona.apellidos:
                return f"{self.persona.nombres.strip()[:1]}{self.persona.apellidos.strip()[:1]}".upper()
        except Exception:
            pass
        return self.username[:2].upper()

    @property
    def mi_estudiante_id(self):
        """Retorna el ID del expediente Estudiante vinculado al usuario si su rol es ESTUDIANTE."""
        try:
            if self.persona and hasattr(self.persona, 'estudiante'):
                return self.persona.estudiante.pk
        except Exception:
            pass
        return None

    def tiene_rol(self, *roles):
        """
        Verifica si el usuario tiene alguno de los roles indicados.
        Solo para uso en templates y lógica visual — no para seguridad.

        Ejemplo:
            {% if request.user.tiene_rol 'DOCENTE' 'DIRECTOR' %}
        """
        return self.rol in roles

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and 'rol' not in update_fields:
            return
        if self.rol and not getattr(self, '_omitir_sincronizacion_grupo', False):
            try:
                from APPS.usuarios.permisos import sincronizar_grupo_usuario
                sincronizar_grupo_usuario(self)
            except Exception:
                pass

