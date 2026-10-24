from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from APPS.usuarios.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Admin personalizado para el modelo Usuario."""
    fieldsets = UserAdmin.fieldsets + (
        ('Información del Sistema', {'fields': ('rol',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información del Sistema', {'fields': ('rol',)}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'rol', 'is_active', 'is_staff']
    list_filter = ['rol', 'is_active', 'is_staff', 'groups']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and 'username' not in readonly:
            readonly.append('username')
        return readonly

