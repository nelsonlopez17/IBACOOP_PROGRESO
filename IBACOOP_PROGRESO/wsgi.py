"""
Configuración WSGI para ejecutar el proyecto en el servidor web.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IBACOOP_PROGRESO.settings')

application = get_wsgi_application()
