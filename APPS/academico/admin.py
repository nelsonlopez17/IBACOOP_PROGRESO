from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from APPS.academico.models import (
    CicloEscolar, BloqueAcademico, Grado, Seccion,
    Curso, AsignacionEstudiante, AsignacionDocente,
    NotaBloque, NotaFinalCurso, AsistenciaEstudiantil,
)


class BloqueAcademicoInline(admin.TabularInline):
    model = BloqueAcademico
    extra = 1
    fields = ['nombre_bloque', 'orden', 'fecha_inicio', 'fecha_fin']


@admin.register(CicloEscolar)
class CicloEscolarAdmin(admin.ModelAdmin):
    list_display = ['anio', 'estado_activo', 'fecha_inicio', 'fecha_fin']
    list_filter = ['estado_activo']
    inlines = [BloqueAcademicoInline]
    readonly_fields = ['creado_en', 'actualizado_en']


@admin.register(BloqueAcademico)
class BloqueAcademicoAdmin(admin.ModelAdmin):
    list_display = ['nombre_bloque', 'ciclo_escolar', 'orden', 'fecha_inicio', 'fecha_fin']
    list_filter = ['ciclo_escolar']
    ordering = ['ciclo_escolar__anio', 'orden']


class SeccionInline(admin.TabularInline):
    model = Seccion
    extra = 1
    fields = ['letra', 'cupo_maximo']


class CursoInline(admin.TabularInline):
    model = Curso
    extra = 1
    fields = ['nombre_curso', 'codigo_curso']


@admin.register(Grado)
class GradoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'orden']
    ordering = ['orden']
    inlines = [SeccionInline, CursoInline]


@admin.register(Seccion)
class SeccionAdmin(admin.ModelAdmin):
    list_display = ['grado', 'letra', 'cupo_maximo']
    list_filter = ['grado']
    ordering = ['grado__orden', 'letra']


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['codigo_curso', 'nombre_curso', 'grado']
    list_filter = ['grado']
    search_fields = ['nombre_curso', 'codigo_curso']


@admin.register(AsignacionEstudiante)
class AsignacionEstudianteAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'seccion', 'ciclo_escolar']
    list_filter = ['ciclo_escolar', 'seccion__grado']
    search_fields = ['estudiante__persona__nombres', 'estudiante__persona__apellidos', 'estudiante__codigo_mineduc']
    autocomplete_fields = ['estudiante']


@admin.register(AsignacionDocente)
class AsignacionDocenteAdmin(admin.ModelAdmin):
    list_display = ['personal', 'curso', 'seccion', 'ciclo_escolar']
    list_filter = ['ciclo_escolar', 'seccion__grado', 'curso']
    search_fields = ['personal__persona__nombres', 'personal__persona__apellidos']


@admin.register(NotaBloque)
class NotaBloqueAdmin(SimpleHistoryAdmin):
    """Usa SimpleHistoryAdmin para ver el historial de cambios de notas desde el admin."""
    list_display = [
        'get_estudiante', 'curso', 'bloque_academico',
        'nota_zona', 'nota_examen', 'get_nota_total',
    ]
    list_filter = ['bloque_academico__ciclo_escolar', 'curso', 'bloque_academico']
    search_fields = [
        'asignacion_estudiante__estudiante__persona__nombres',
        'asignacion_estudiante__estudiante__persona__apellidos',
        'asignacion_estudiante__estudiante__codigo_mineduc',
    ]
    readonly_fields = ['get_nota_total', 'creado_en', 'actualizado_en']

    @admin.display(description='Estudiante')
    def get_estudiante(self, obj):
        return obj.asignacion_estudiante.estudiante

    @admin.display(description='Total')
    def get_nota_total(self, obj):
        return obj.nota_total


class EstaPromocionadoListFilter(admin.SimpleListFilter):
    title = '¿Materia Aprobada / Promocionada?'
    parameter_name = 'esta_promocionado'

    def lookups(self, request, model_admin):
        return (
            ('1', 'Sí (Promocionado)'),
            ('0', 'No (No Promocionado)'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(esta_promocionado=True)
        if self.value() == '0':
            return queryset.filter(esta_promocionado=False)
        return queryset


@admin.register(NotaFinalCurso)
class NotaFinalCursoAdmin(admin.ModelAdmin):
    list_display = ['get_estudiante', 'curso', 'nota_promedio', 'esta_promocionado']
    list_filter = [EstaPromocionadoListFilter, 'curso', 'asignacion_estudiante__ciclo_escolar']
    search_fields = [
        'asignacion_estudiante__estudiante__persona__nombres',
        'asignacion_estudiante__estudiante__persona__apellidos',
        'asignacion_estudiante__estudiante__codigo_mineduc',
    ]
    readonly_fields = ['creado_en', 'actualizado_en']

    @admin.display(description='Estudiante')
    def get_estudiante(self, obj):
        return obj.asignacion_estudiante.estudiante


@admin.register(AsistenciaEstudiantil)
class AsistenciaEstudiantilAdmin(admin.ModelAdmin):
    list_display = ['get_estudiante', 'curso', 'fecha', 'presente', 'justificado']
    list_filter = ['presente', 'fecha', 'curso']
    date_hierarchy = 'fecha'

    @admin.display(description='Estudiante')
    def get_estudiante(self, obj):
        return obj.asignacion_estudiante.estudiante
