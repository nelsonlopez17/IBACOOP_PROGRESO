"""
inventario/models.py

Control de Inventario del Instituto El Progreso.

Gestiona el stock de artículos (papelería, tecnología, mobiliario, etc.)
y registra cada movimiento (entradas, salidas, asignaciones).

django-simple-history en ArticuloInventario: audita cambios en el stock_actual,
permitiendo rastrear qué usuario modificó el inventario y cuándo.
"""
from django.db import models
from simple_history.models import HistoricalRecords

from APPS.core.models import ModeloAuditable


class ArticuloInventario(ModeloAuditable):
    """
    Representa un artículo o bien del inventario del instituto.

    El campo stock_minimo_alerta permite generar alertas cuando el stock
    cae por debajo del umbral definido.
    La propiedad alerta_stock_bajo facilita la creación de dashboards de alerta.

    django-simple-history: registra cada cambio en el inventario para
    trazabilidad y auditoría de activos.
    """
    CATEGORIA_CHOICES = [
        ('PAPELERIA',   'Papelería y Útiles'),
        ('TECNOLOGIA',  'Tecnología'),
        ('MOBILIARIO',  'Mobiliario'),
        ('LIMPIEZA',    'Productos de Limpieza'),
        ('DEPORTIVO',   'Material Deportivo'),
        ('LABORATORIO', 'Material de Laboratorio'),
        ('LIBROS',      'Libros y Material Didáctico'),
        ('OTRO',        'Otro'),
    ]

    codigo_unico = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Código único',
        help_text='Código interno del artículo. Ej: PAP-001, TEC-023.',
    )
    nombre = models.CharField(max_length=150, verbose_name='Nombre del artículo')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        verbose_name='Categoría',
    )
    stock_actual = models.IntegerField(
        default=0,
        verbose_name='Stock actual',
    )
    stock_minimo_alerta = models.IntegerField(
        default=5,
        verbose_name='Stock mínimo de alerta',
        help_text='Se generará una alerta cuando stock_actual <= este valor.',
    )
    unidad_medida = models.CharField(
        max_length=20,
        default='unidades',
        verbose_name='Unidad de medida',
        help_text='Ej: unidades, resmas, cajas, litros.',
    )
    # --- Auditoría de inventario (django-simple-history) ---
    history = HistoricalRecords(
        verbose_name='Historial de cambios de inventario',
    )

    class Meta:
        verbose_name = 'Artículo de Inventario'
        verbose_name_plural = 'Artículos de Inventario'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return f"[{self.codigo_unico}] {self.nombre} (Stock: {self.stock_actual} {self.unidad_medida})"

    @property
    def alerta_stock_bajo(self):
        """Retorna True si el stock actual está en o por debajo del mínimo."""
        return self.stock_actual <= self.stock_minimo_alerta


class MovimientoInventario(ModeloAuditable):
    """
    Registra cada transacción de inventario (entrada, salida, asignación, etc.).

    Cada movimiento es inmutable una vez registrado — no se debe editar.
    Para corregir un error, se registra un movimiento de ajuste con el motivo.
    RESTRICT en ArticuloInventario y Personal: garantiza trazabilidad completa.
    """
    TIPO_MOVIMIENTO_CHOICES = [
        ('ENTRADA',    'Entrada de mercancía'),
        ('SALIDA',     'Salida / Consumo'),
        ('ASIGNACION', 'Asignación a personal/sección'),
        ('DEVOLUCION', 'Devolución'),
        ('AJUSTE',     'Ajuste de inventario'),
        ('BAJA',       'Baja por daño o pérdida'),
    ]

    articulo = models.ForeignKey(
        ArticuloInventario,
        on_delete=models.RESTRICT,
        related_name='movimientos',
        verbose_name='Artículo',
    )
    personal_responsable = models.ForeignKey(
        'rrhh.Personal',
        on_delete=models.RESTRICT,
        related_name='movimientos_inventario',
        verbose_name='Personal responsable',
    )
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        verbose_name='Tipo de movimiento',
    )
    cantidad = models.IntegerField(
        verbose_name='Cantidad',
        help_text='Positivo para entradas/devoluciones. Negativo para salidas/bajas.',
    )
    fecha = models.DateTimeField(verbose_name='Fecha y hora del movimiento')
    motivo = models.TextField(verbose_name='Motivo o descripción del movimiento')
    documento_referencia = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Documento de referencia',
        help_text='Ej: Factura No., Orden de compra, etc.',
    )

    class Meta:
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha']

    def __str__(self):
        return (
            f"{self.get_tipo_movimiento_display()} — "
            f"{self.articulo.nombre} ({self.cantidad} {self.articulo.unidad_medida}) — "
            f"{self.fecha.strftime('%d/%m/%Y')}"
        )
