from django.contrib import admin
from APPS.estudiantes.models import Estudiante, Encargado, EstudianteEncargado


class EstudianteEncargadoInline(admin.TabularInline):
    model = EstudianteEncargado
    extra = 1
    fields = ['encargado', 'parentesco', 'es_contacto_principal']


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ['codigo_mineduc', 'apellidos', 'nombres', 'estado_activo', 'creado_en']
    list_filter = ['estado_activo', 'genero']
    search_fields = ['codigo_mineduc', 'nombres', 'apellidos', 'usuario__username']
    readonly_fields = ['creado_en', 'actualizado_en']
    inlines = [EstudianteEncargadoInline]
    fieldsets = (
        ('Información Personal', {
            'fields': ('usuario', 'codigo_mineduc', 'nombres', 'apellidos', 'fecha_nacimiento', 'genero')
        }),
        ('Contacto', {
            'fields': ('direccion',)
        }),
        ('Estado', {
            'fields': ('estado_activo',)
        }),
        ('Auditoría', {
            'fields': ('creado_en', 'actualizado_en', 'usuario_creacion', 'usuario_modificacion'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Encargado)
class EncargadoAdmin(admin.ModelAdmin):
    list_display = ['apellidos', 'nombres', 'dpi', 'telefono_contacto', 'creado_en']
    search_fields = ['nombres', 'apellidos', 'dpi']
    readonly_fields = ['creado_en', 'actualizado_en']


@admin.register(EstudianteEncargado)
class EstudianteEncargadoAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'encargado', 'parentesco', 'es_contacto_principal']
    list_filter = ['parentesco', 'es_contacto_principal']
    search_fields = ['estudiante__nombres', 'estudiante__apellidos', 'encargado__nombres']
