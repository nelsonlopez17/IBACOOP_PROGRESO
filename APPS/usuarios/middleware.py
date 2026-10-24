"""
APPS/usuarios/middleware.py

Middleware para forzar el cambio obligatorio de contraseña en usuarios que inician sesión
por primera vez o a quienes se les ha restablecido la clave.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class EnforcePasswordChangeMiddleware:
    """
    Middleware de seguridad que intercepta las peticiones de usuarios autenticados
    (no superusuarios) con la bandera `debe_cambiar_password = True` y los redirige
    de forma obligatoria a la pantalla de cambio de clave.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            if getattr(request.user, 'debe_cambiar_password', False):
                path = request.path
                url_cambio = reverse('usuarios:cambiar_mi_password')
                url_logout = reverse('usuarios:logout')

                # rutas autorizadas durante el cambio de clave obligatorio
                rutas_permitidas = [url_cambio, url_logout]

                if not any(path.startswith(r) for r in rutas_permitidas) and not path.startswith('/static/') and not path.startswith('/media/'):
                    messages.warning(
                        request,
                        "Por motivos de seguridad e integridad de su cuenta, debe actualizar su contraseña temporal antes de continuar navegando."
                    )
                    return redirect('usuarios:cambiar_mi_password')

        response = self.get_response(request)
        return response
