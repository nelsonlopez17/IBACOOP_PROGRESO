"""
Configuración ASGI para soporte de servicios web y tiempo real.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IBACOOP_PROGRESO.settings')

application = get_asgi_application()
