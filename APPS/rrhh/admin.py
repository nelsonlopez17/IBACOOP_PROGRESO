from django.contrib import admin
from APPS.rrhh.models import Puesto, Personal, Planilla


@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ['nombre_puesto', 'creado_en']
    search_fields = ['nombre_puesto']
    readonly_fields = ['creado_en', 'actualizado_en']


@admin.register(Personal)
class PersonalAdmin(admin.ModelAdmin):
    list_display = ['get_nombre_completo', 'puesto', 'estado_laboral', 'salario_base_asignado', 'fecha_contratacion']
    list_filter = ['estado_laboral', 'puesto']
    search_fields = ['persona__nombres', 'persona__apellidos', 'persona__cui', 'nit']
    readonly_fields = ['creado_en', 'actualizado_en']

    @admin.display(description='Nombre Completo')
    def get_nombre_completo(self, obj):
        return obj.persona.nombre_completo


@admin.register(Planilla)
class PlanillaAdmin(admin.ModelAdmin):
    list_display = ['personal', 'mes_pagado', 'ciclo_escolar', 'total_pagar', 'pagado', 'fecha_pago']
    list_filter = ['mes_pagado', 'ciclo_escolar', 'pagado']
    search_fields = ['personal__persona__nombres', 'personal__persona__apellidos']
    readonly_fields = ['creado_en', 'actualizado_en']
