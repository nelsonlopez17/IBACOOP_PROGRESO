"""
core/models.py

Módulo base del sistema de gestión escolar.
Provee el modelo abstracto `ModeloAuditable` y el `ActivosManager` que
implementan la eliminación lógica (Soft Delete) y auditoría en todas las
tablas del sistema. NINGÚN registro se elimina físicamente de la base de datos.
"""
from django.db import models
from django.utils import timezone


class ActivosManager(models.Manager):
    """
    Manager personalizado que filtra automáticamente los registros marcados
    como eliminados lógicamente (esta_eliminado=True).

    Es el manager por defecto en todos los modelos que hereden de ModeloAuditable,
    garantizando que ninguna consulta estándar devuelva registros "borrados".
    """

    def get_queryset(self):
        return super().get_queryset().filter(esta_eliminado=False)


class ModeloAuditable(models.Model):
    """
    Modelo abstracto base para todos los modelos del sistema.

    Proporciona:
        - Auditoría de fechas (creación y modificación automáticas).
        - Eliminación lógica (Soft Delete): el método delete() marca el
          registro como eliminado en lugar de borrarlo de la BD.
        - Registro de usuario que creó/modificó el registro.

    IMPORTANTE: Todos los modelos del sistema deben heredar de este modelo
    para garantizar consistencia en auditoría e integridad de datos.
    """

    # --- Campos de auditoría temporal ---
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creado en',
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name='Actualizado en',
    )
    eliminado_en = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Eliminado en',
        help_text='Fecha y hora en que se realizó la eliminación lógica.',
    )

    # --- Flag de eliminación lógica ---
    esta_eliminado = models.BooleanField(
        default=False,
        verbose_name='¿Está eliminado?',
        help_text='Si es True, el registro ha sido eliminado lógicamente y no aparecerá en consultas normales.',
    )

    # --- Auditoría de usuarios ---
    # Nota: FK a 'usuarios.Usuario' usando string para evitar importación circular.
    #       Se usa SET_NULL para no perder registros si el usuario es desactivado.
    usuario_creacion = models.ForeignKey(
        'usuarios.Usuario',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(class)s_creados',
        verbose_name='Creado por',
        help_text='Usuario que creó este registro.',
    )
    usuario_modificacion = models.ForeignKey(
        'usuarios.Usuario',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='%(class)s_modificados',
        verbose_name='Modificado por',
        help_text='Último usuario que modificó este registro.',
    )

    # --- Managers ---
    # 'objects' (default): solo registros activos — usado en todas las consultas normales
    objects = ActivosManager()
    # 'todos': acceso completo incluyendo eliminados — solo para auditoría y administración
    todos = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, usuario=None):
        """
        Sobrescribe el método delete() para implementar eliminación lógica.

        Valida mediante reflexión y la API de metadatos de Django (_meta.related_objects)
        si existen objetos relacionados configurados con on_delete=models.RESTRICT que permanezcan
        activos (esta_eliminado=False). Si se encuentran dependencias activas, se eleva
        models.deletion.RestrictedError impidiendo el borrado lógico.

        Args:
            usuario: Instancia del Usuario que realiza la eliminación para auditoría.
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
                    # rel_target es un RelatedManager (uno a muchos)
                    if hasattr(rel.related_model, 'esta_eliminado'):
                        relacionados_activos = rel_target.filter(esta_eliminado=False)
                    else:
                        relacionados_activos = rel_target.all()

                    if relacionados_activos.exists():
                        elementos_restringidos.append(relacionados_activos.first())

        if elementos_restringidos:
            raise models.deletion.RestrictedError(
                f"No se puede eliminar lógicamente el registro '{self}' porque existen elementos relacionados activos que dependen de él.",
                elementos_restringidos
            )

        self.esta_eliminado = True
        self.eliminado_en = timezone.now()
        if usuario:
            self.usuario_modificacion = usuario
        self.save(
            update_fields=[
                'esta_eliminado',
                'eliminado_en',
                'usuario_modificacion',
                'actualizado_en',
            ]
        )

    def restaurar(self, usuario=None):
        """
        Restaura un registro que fue eliminado lógicamente.

        Args:
            usuario: Instancia del Usuario que realiza la restauración.
        """
        self.esta_eliminado = False
        self.eliminado_en = None
        if usuario:
            self.usuario_modificacion = usuario
        self.save(
            update_fields=[
                'esta_eliminado',
                'eliminado_en',
                'usuario_modificacion',
                'actualizado_en',
            ]
        )

    def __repr__(self):
        estado = '[ELIMINADO] ' if self.esta_eliminado else ''
        return f'{estado}{self.__class__.__name__}(pk={self.pk})'
