from django.contrib import admin
from APPS.core.models import Persona


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ['cui', 'apellidos', 'nombres', 'telefono_principal', 'correo', 'usuario']
    search_fields = ['cui', 'nombres', 'apellidos', 'correo', 'telefono_principal']
    list_filter = ['esta_eliminado']
    readonly_fields = ['creado_en', 'actualizado_en']
