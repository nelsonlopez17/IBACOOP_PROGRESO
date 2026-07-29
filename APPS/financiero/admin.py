from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from APPS.financiero.models import MensualidadCobro, PagoColegiatura


class PagoColegiaturaInline(admin.TabularInline):
    model = PagoColegiatura
    extra = 0
    readonly_fields = ['numero_boleta', 'monto_pagado', 'fecha_pago', 'recibo_generado']
    can_delete = False


@admin.register(MensualidadCobro)
class MensualidadCobroAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'get_mes', 'ciclo_escolar', 'monto_esperado', 'estado_pagado']
    list_filter = ['estado_pagado', 'mes_cobro', 'ciclo_escolar']
    search_fields = ['estudiante__nombres', 'estudiante__apellidos', 'estudiante__codigo_mineduc']
    inlines = [PagoColegiaturaInline]
    readonly_fields = ['creado_en', 'actualizado_en']

    @admin.display(description='Mes')
    def get_mes(self, obj):
        return obj.get_mes_cobro_display()


@admin.register(PagoColegiatura)
class PagoColegiaturaAdmin(SimpleHistoryAdmin):
    """SimpleHistoryAdmin para auditar cambios en registros de pago."""
    list_display = ['numero_boleta', 'mensualidad', 'monto_pagado', 'fecha_pago', 'recibo_generado']
    list_filter = ['recibo_generado', 'fecha_pago']
    search_fields = ['numero_boleta', 'mensualidad__estudiante__nombres']
    date_hierarchy = 'fecha_pago'
    readonly_fields = ['creado_en', 'actualizado_en']
