"""
portal/context_processors.py

Procesador de contexto para inyectar los parámetros institucionales,
configuración del portal web y contador de mensajes pendientes en todas las plantillas.
"""
from APPS.portal.models import ConfiguracionPortal, SolicitudContacto


def portal_settings(request):
    """Suministra el objeto singleton ConfiguracionPortal y el contador de mensajes de contacto pendientes."""
    try:
        config = ConfiguracionPortal.get_solo()
    except Exception:
        config = None

    mensajes_pendientes = 0
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        rol = getattr(user, 'rol', None)
        if rol in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA'] or getattr(user, 'is_superuser', False):
            try:
                mensajes_pendientes = SolicitudContacto.objects.filter(atendido=False).count()
            except Exception:
                mensajes_pendientes = 0

    return {
        'config_portal': config,
        'mensajes_portal_pendientes_count': mensajes_pendientes,
    }
