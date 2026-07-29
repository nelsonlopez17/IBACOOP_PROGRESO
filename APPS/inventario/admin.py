from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from APPS.inventario.models import ArticuloInventario, MovimientoInventario


class MovimientoInventarioInline(admin.TabularInline):
    model = MovimientoInventario
    extra = 0
    readonly_fields = ['tipo_movimiento', 'cantidad', 'fecha', 'personal_responsable', 'motivo']
    can_delete = False
    max_num = 10


@admin.register(ArticuloInventario)
class ArticuloInventarioAdmin(SimpleHistoryAdmin):
    """SimpleHistoryAdmin para auditar cambios en stock."""
    list_display = [
        'codigo_unico', 'nombre', 'categoria',
        'stock_actual', 'stock_minimo_alerta', 'get_alerta',
    ]
    list_filter = ['categoria']
    search_fields = ['codigo_unico', 'nombre']
    readonly_fields = ['creado_en', 'actualizado_en']
    inlines = [MovimientoInventarioInline]

    @admin.display(description='⚠ Alerta Stock', boolean=True)
    def get_alerta(self, obj):
        return obj.alerta_stock_bajo


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ['articulo', 'tipo_movimiento', 'cantidad', 'fecha', 'personal_responsable']
    list_filter = ['tipo_movimiento', 'fecha']
    search_fields = ['articulo__nombre', 'articulo__codigo_unico', 'motivo']
    date_hierarchy = 'fecha'
    readonly_fields = ['creado_en', 'actualizado_en']
