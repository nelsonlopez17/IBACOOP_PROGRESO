from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from APPS.financiero.models import ConceptoPago, CuentaPorCobrar, Abono


class AbonoInline(admin.TabularInline):
    model = Abono
    extra = 0
    readonly_fields = ['numero_boleta', 'monto_pagado', 'fecha_pago']
    can_delete = False


@admin.register(ConceptoPago)
class ConceptoPagoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'monto_estandar']
    search_fields = ['nombre']
    readonly_fields = ['creado_en', 'actualizado_en']


@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'concepto', 'ciclo_escolar', 'monto_total', 'saldo_pendiente', 'estado_pago']
    list_filter = ['estado_pago', 'concepto', 'ciclo_escolar']
    search_fields = ['estudiante__persona__nombres', 'estudiante__persona__apellidos', 'estudiante__codigo_mineduc']
    inlines = [AbonoInline]
    readonly_fields = ['creado_en', 'actualizado_en']


@admin.register(Abono)
class AbonoAdmin(SimpleHistoryAdmin):
    """SimpleHistoryAdmin para auditar cambios en registros de abonos."""
    list_display = ['numero_boleta', 'cuenta_por_cobrar', 'monto_pagado', 'fecha_pago']
    list_filter = ['fecha_pago']
    search_fields = ['numero_boleta', 'cuenta_por_cobrar__estudiante__persona__nombres', 'cuenta_por_cobrar__estudiante__persona__apellidos']
    date_hierarchy = 'fecha_pago'
    readonly_fields = ['creado_en', 'actualizado_en']
