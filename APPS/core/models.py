"""
core/models.py

Módulo base del sistema de gestión escolar.
Provee:
  - ModeloAuditable y ActivosManager para la eliminación lógica (Soft Delete).
  - Modelo Persona que implementa el patrón Supertipo/Subtipo para Estudiante, Encargado y Personal.
"""
from django.db import models
from django.utils import timezone


class ActivosManager(models.Manager):
    """
    Manager personalizado que filtra automáticamente los registros marcados
    como eliminados lógicamente (esta_eliminado=True).
    """

    def get_queryset(self):
        return super().get_queryset().filter(esta_eliminado=False)


class ModeloAuditable(models.Model):
    """
    Modelo abstracto base para todos los modelos operativos del sistema.
    Proporciona eliminación lógica y auditoría de creación / actualización.
    """
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creado en',
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name='Actualizado en',
    )
    esta_eliminado = models.BooleanField(
        default=False,
        verbose_name='¿Está eliminado?',
        help_text='Indica si el registro fue eliminado lógicamente.',
    )

    objects = ActivosManager()
    todos = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """
        Eliminación lógica con validación de dependencias RESTRICT activas.
        """
        elementos_restringidos = []

        for rel in self._meta.related_objects:
            if rel.on_delete == models.RESTRICT:
                accessor_name = rel.get_accessor_name()
                try:
                    rel_target = getattr(self, accessor_name, None)
                except Exception:
                    continue

                if rel_target is None:
                    continue

                if rel.one_to_one:
                    esta_activo = True
                    if hasattr(rel_target, 'esta_eliminado'):
                        esta_activo = not rel_target.esta_eliminado
                    if esta_activo:
                        elementos_restringidos.append(rel_target)
                else:
                    if hasattr(rel.related_model, 'esta_eliminado'):
                        relacionados_activos = rel_target.filter(esta_eliminado=False)
                    else:
                        relacionados_activos = rel_target.all()

                    if relacionados_activos.exists():
                        elementos_restringidos.append(relacionados_activos.first())

        if elementos_restringidos:
            raise models.deletion.RestrictedError(
                f"No se puede eliminar lógicamente '{self}' porque existen registros activos que dependen de él.",
                elementos_restringidos
            )

        self.esta_eliminado = True
        self.save(update_fields=['esta_eliminado', 'actualizado_en'])

    def restaurar(self):
        """Restaura un registro eliminado lógicamente."""
        self.esta_eliminado = False
        self.save(update_fields=['esta_eliminado', 'actualizado_en'])


class Persona(ModeloAuditable):
    """
    Modelo Supertipo que concentra la información personal común de todos
    los individuos del sistema (Estudiantes, Encargados y Personal).
    """
    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='persona',
        verbose_name='Cuenta de acceso (Usuario)',
        help_text='Cuenta de acceso opcional asignada a la persona.'
    )
    cui = models.CharField(
        max_length=13,
        unique=True,
        verbose_name='CUI / DPI',
        help_text='Código Único de Identificación (DPI o CUI MINEDUC de 13 dígitos).'
    )
    nombres = models.CharField(
        max_length=100,
        verbose_name='Nombres'
    )
    apellidos = models.CharField(
        max_length=100,
        verbose_name='Apellidos'
    )
    fecha_nacimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de nacimiento'
    )
    direccion = models.TextField(
        blank=True,
        verbose_name='Dirección'
    )
    telefono_principal = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='Teléfono principal'
    )
    telefono_secundario = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='Teléfono secundario'
    )
    correo = models.EmailField(
        blank=True,
        verbose_name='Correo de contacto / comercial',
        help_text='Correo electrónico de contacto, independiente del email de usuario.'
    )

    class Meta:
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} (CUI: {self.cui})"

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"
