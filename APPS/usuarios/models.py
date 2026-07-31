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
        """Retorna el nombre completo del usuario."""
        return self.get_full_name() or self.username

    def tiene_rol(self, *roles):
        """
        Verifica si el usuario tiene alguno de los roles indicados.
        Solo para uso en templates y lógica visual — no para seguridad.

        Ejemplo:
            {% if request.user.tiene_rol 'DOCENTE' 'DIRECTOR' %}
        """
        return self.rol in roles
