"""
URL Configuration — IBACOOP_PROGRESO
Sistema de Gestión Escolar — Instituto "El Progreso"
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Administración de Django
    path('admin/', admin.site.urls),

    # Módulos Principales del ERP Escolar
    path('', include('APPS.core.urls')),
    path('usuarios/', include('APPS.usuarios.urls')),

    # Otros Módulos del Sistema ERP
    path('estudiantes/', include('APPS.estudiantes.urls')),
    path('rrhh/', include('APPS.rrhh.urls')),
    path('academico/', include('APPS.academico.urls')),
    path('financiero/', include('APPS.financiero.urls')),
    path('inventario/', include('APPS.inventario.urls')),
    path('portal/', include('APPS.portal.urls')),
]

# Servir archivos media en desarrollo (DEBUG=True)
# En producción, usar Nginx o servidor web equivalente
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
