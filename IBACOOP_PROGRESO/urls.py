"""
URL Configuration — IBACOOP_PROGRESO
Sistema de Gestión Escolar — Instituto "El Progreso"
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('APPS.portal.urls')),
    path('dashboard/', include('APPS.core.urls')),
    path('usuarios/', include('APPS.usuarios.urls')),
    path('estudiantes/', include('APPS.estudiantes.urls')),
    path('rrhh/', include('APPS.rrhh.urls')),
    path('academico/', include('APPS.academico.urls')),
    path('financiero/', include('APPS.financiero.urls')),
    path('inventario/', include('APPS.inventario.urls')),
    path('auditoria/', include('APPS.auditoria.urls')),
    path('reportes/', include('APPS.reportes.urls')),
    path('disciplina/', include('APPS.disciplina.urls')),
]

# servir archivos multimedia en modo de desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = 'APPS.core.views.error_403'
