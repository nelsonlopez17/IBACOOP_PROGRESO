from django.contrib import admin
from APPS.rrhh.models import Puesto, Personal, AsistenciaPersonal, Planilla


@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ['nombre_puesto', 'creado_en']
    search_fields = ['nombre_puesto']
    readonly_fields = ['creado_en', 'actualizado_en']


@admin.register(Personal)
class PersonalAdmin(admin.ModelAdmin):
    list_display = ['apellidos', 'nombres', 'puesto', 'estado_laboral', 'salario_base_asignado', 'fecha_contratacion']
    list_filter = ['estado_laboral', 'puesto']
    search_fields = ['nombres', 'apellidos', 'dpi', 'usuario__username']
    readonly_fields = ['creado_en', 'actualizado_en']
    fieldsets = (
        ('Información Personal', {
            'fields': ('usuario', 'nombres', 'apellidos', 'dpi', 'nit')
        }),
        ('Información Laboral', {
            'fields': ('puesto', 'fecha_contratacion', 'estado_laboral', 'salario_base_asignado')
        }),
        ('Auditoría', {
            'fields': ('creado_en', 'actualizado_en', 'usuario_creacion', 'usuario_modificacion'),
            'classes': ('collapse',),
        }),
    )


@admin.register(AsistenciaPersonal)
class AsistenciaPersonalAdmin(admin.ModelAdmin):
    list_display = ['personal', 'fecha', 'hora_entrada', 'hora_salida', 'estado_asistencia']
    list_filter = ['estado_asistencia', 'fecha']
    search_fields = ['personal__nombres', 'personal__apellidos']
    date_hierarchy = 'fecha'


@admin.register(Planilla)
class PlanillaAdmin(admin.ModelAdmin):
    list_display = ['personal', 'mes_pagado', 'anio_pagado', 'total_pagar', 'pagado', 'fecha_pago']
    list_filter = ['mes_pagado', 'anio_pagado', 'pagado']
    search_fields = ['personal__nombres', 'personal__apellidos']
    readonly_fields = ['creado_en', 'actualizado_en']
