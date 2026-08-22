from django.contrib import admin
from APPS.portal.models import ContenidoWeb


@admin.register(ContenidoWeb)
class ContenidoWebAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'seccion', 'publicado', 'fecha_publicacion', 'autor']
    list_filter = ['seccion', 'publicado']
    search_fields = ['titulo', 'cuerpo']
    date_hierarchy = 'fecha_publicacion'
    readonly_fields = ['creado_en', 'actualizado_en']
    fieldsets = (
        ('Contenido', {
            'fields': ('seccion', 'titulo', 'cuerpo')
        }),
        ('Imagen', {
            'fields': ('imagen_archivo', 'imagen_url'),
            'description': 'El archivo tiene prioridad sobre la URL si se proporcionan ambos.',
        }),
        ('Publicación', {
            'fields': ('fecha_publicacion', 'publicado', 'autor')
        }),
        ('Auditoría', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',),
        }),
    )
