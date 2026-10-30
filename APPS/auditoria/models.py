"""
auditoria/models.py

Modelos para el registro y auditoría de eventos de seguridad del sistema.
Captura accesos no autorizados, descargas masivas de datos y eventos de autenticación.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class TipoEventoSeguridad(models.TextChoices):
    ACCESO_DENEGADO = 'ACCESO_DENEGADO', 'Acceso denegado / No autorizado'
    DESCARGA_REPORTE = 'DESCARGA_REPORTE', 'Descarga o exportación masiva'
    CIERRE_SESION = 'CIERRE_SESION', 'Cierre de sesión'
    CAMBIO_PASSWORD = 'CAMBIO_PASSWORD', 'Cambio o restablecimiento de contraseña'
    DESBLOQUEO_CUENTA = 'DESBLOQUEO_CUENTA', 'Desbloqueo administrativo de cuenta'


class EventoSeguridad(models.Model):
    """
    Registro inmutable de eventos de seguridad y meta-auditoría.
    """
    tipo = models.CharField(
        max_length=30,
        choices=TipoEventoSeguridad.choices,
        db_index=True,
        verbose_name='Tipo de evento'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eventos_seguridad',
        verbose_name='Usuario autenticado'
    )
    username_ingresado = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nombre de usuario'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Dirección IP'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='Navegador / User-Agent'
    )
    ruta = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Ruta o recurso solicitado'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Detalle o parámetros del evento'
    )
    fecha = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Fecha y hora'
    )

    class Meta:
        verbose_name = 'Evento de Seguridad'
        verbose_name_plural = 'Eventos de Seguridad'
        ordering = ['-fecha']

    def __str__(self):
        usuario_str = self.usuario.username if self.usuario else (self.username_ingresado or 'Anónimo')
        return f"[{self.get_tipo_display()}] {usuario_str} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"


def obtener_ip_cliente(request):
    """Extrae la IP real del cliente considerando proxies inversos."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def registrar_evento_seguridad(tipo, request=None, usuario=None, ruta=None, descripcion='', username_ingresado=''):
    """
    Función utilitaria tolerante a fallos para registrar eventos de seguridad.
    Nunca propaga excepciones hacia la lógica principal de la petición.
    """
    try:
        user = usuario
        ip = None
        ua = ''
        path = ruta or ''

        if request:
            if not user and getattr(request, 'user', None) and request.user.is_authenticated:
                user = request.user
            ip = obtener_ip_cliente(request)
            ua = request.META.get('HTTP_USER_AGENT', '')
            if not path:
                path = request.path

        if not username_ingresado and user:
            username_ingresado = getattr(user, 'username', '')

        EventoSeguridad.objects.create(
            tipo=tipo,
            usuario=user,
            username_ingresado=username_ingresado,
            ip_address=ip,
            user_agent=ua[:500] if ua else '',
            ruta=path[:255] if path else '',
            descripcion=descripcion,
            fecha=timezone.now()
        )
    except Exception:
        # se previene que cualquier fallo en auditoria bloquee la respuesta del sistema
        pass
