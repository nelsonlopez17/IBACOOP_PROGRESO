"""
auditoria/signals.py

Receptores de señales de Django para auditar eventos del ciclo de vida de sesiones y credenciales.
"""
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_out
from APPS.auditoria.models import registrar_evento_seguridad, TipoEventoSeguridad


@receiver(user_logged_out)
def auditar_cierre_sesion(sender, request, user, **kwargs):
    """Registra el cierre voluntario o administrativo de sesión."""
    if user and user.is_authenticated:
        registrar_evento_seguridad(
            tipo=TipoEventoSeguridad.CIERRE_SESION,
            request=request,
            usuario=user,
            descripcion='Cierre voluntario de sesión en el sistema'
        )
