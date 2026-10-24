from django.contrib import admin
from APPS.estudiantes.models import Estudiante, Encargado, EstudianteEncargado


class EstudianteEncargadoInline(admin.TabularInline):
    model = EstudianteEncargado
    extra = 1
    fields = ['encargado', 'parentesco', 'es_contacto_principal']


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ['codigo_mineduc', 'get_nombre_completo', 'estado_estudiante', 'estado_activo', 'creado_en']
    list_filter = ['estado_estudiante', 'persona__genero']
    search_fields = ['codigo_mineduc', 'persona__nombres', 'persona__apellidos', 'persona__cui']
    readonly_fields = ['creado_en', 'actualizado_en']
    inlines = [EstudianteEncargadoInline]

    @admin.display(description='Nombre Completo')
    def get_nombre_completo(self, obj):
        return obj.persona.nombre_completo


@admin.register(Encargado)
class EncargadoAdmin(admin.ModelAdmin):
    list_display = ['get_nombre_completo', 'lugar_de_trabajo', 'creado_en']
    search_fields = ['persona__nombres', 'persona__apellidos', 'persona__cui', 'lugar_de_trabajo']
    readonly_fields = ['creado_en', 'actualizado_en']

    @admin.display(description='Nombre Completo')
    def get_nombre_completo(self, obj):
        return obj.persona.nombre_completo


@admin.register(EstudianteEncargado)
class EstudianteEncargadoAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'encargado', 'parentesco', 'es_contacto_principal']
    list_filter = ['parentesco', 'es_contacto_principal']
    search_fields = ['estudiante__persona__nombres', 'estudiante__persona__apellidos', 'encargado__persona__nombres', 'encargado__persona__apellidos']
