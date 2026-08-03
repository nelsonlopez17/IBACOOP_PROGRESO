"""
inventario/models.py

Control de Inventario y Bienes del Instituto El Progreso.
Incluye ArticuloInventario (auditado con simple-history) y MovimientoInventario.
"""
from django.db import models
from simple_history.models import HistoricalRecords

from APPS.core.models import ModeloAuditable


class CategoriaChoices(models.TextChoices):
    PAPELERIA   = 'PAPELERIA',   'Papelería y Útiles'
    TECNOLOGIA  = 'TECNOLOGIA',  'Tecnología'
    MOBILIARIO  = 'MOBILIARIO',  'Mobiliario'
    LIMPIEZA    = 'LIMPIEZA',    'Productos de Limpieza'
    DEPORTIVO   = 'DEPORTIVO',   'Material Deportivo'
    LABORATORIO = 'LABORATORIO', 'Material de Laboratorio'
    LIBROS      = 'LIBROS',      'Libros y Didáctico'
    OTRO        = 'OTRO',        'Otro'


class TipoMovimientoChoices(models.TextChoices):
    ENTRADA    = 'ENTRADA',    'Entrada de mercancía'
    SALIDA     = 'SALIDA',     'Salida / Consumo'
    ASIGNACION = 'ASIGNACION', 'Asignación a personal/sección'
    DEVOLUCION = 'DEVOLUCION', 'Devolución'
    AJUSTE     = 'AJUSTE',     'Ajuste de inventario'
    BAJA       = 'BAJA',       'Baja por daño o pérdida'


class ArticuloInventario(ModeloAuditable):
    """Artículo o bien perteneciente al inventario institucional."""
    codigo_unico = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Código único'
    )
    nombre = models.CharField(
        max_length=150,
        verbose_name='Nombre del artículo'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    categoria = models.CharField(
        max_length=20,
        choices=CategoriaChoices.choices,
        verbose_name='Categoría'
    )
    stock_actual = models.IntegerField(
        default=0,
        verbose_name='Stock actual'
    )
    stock_minimo_alerta = models.IntegerField(
        default=5,
        verbose_name='Stock mínimo de alerta'
    )
    unidad_medida = models.CharField(
        max_length=20,
        default='unidades',
        verbose_name='Unidad de medida'
    )
    history = HistoricalRecords(
        verbose_name='Historial de inventario'
    )

    class Meta:
        verbose_name = 'Artículo de Inventario'
        verbose_name_plural = 'Artículos de Inventario'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return f"[{self.codigo_unico}] {self.nombre} (Stock: {self.stock_actual} {self.unidad_medida})"

    @property
    def alerta_stock_bajo(self) -> bool:
        return self.stock_actual <= self.stock_minimo_alerta


class MovimientoInventario(ModeloAuditable):
    """Transacción inmutable de entrada, salida o asignación de inventario."""
    articulo = models.ForeignKey(
        ArticuloInventario,
        on_delete=models.RESTRICT,
        related_name='movimientos',
        verbose_name='Artículo'
    )
    personal_responsable = models.ForeignKey(
        'rrhh.Personal',
        on_delete=models.RESTRICT,
        related_name='movimientos_inventario',
        verbose_name='Personal responsable'
    )
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TipoMovimientoChoices.choices,
        verbose_name='Tipo de movimiento'
    )
    cantidad = models.IntegerField(
        verbose_name='Cantidad'
    )
    fecha = models.DateTimeField(
        verbose_name='Fecha y hora del movimiento'
    )
    motivo = models.TextField(
        verbose_name='Motivo'
    )
    documento_referencia = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Documento de referencia'
    )

    class Meta:
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.get_tipo_movimiento_display()} — {self.articulo.nombre} ({self.cantidad})"
