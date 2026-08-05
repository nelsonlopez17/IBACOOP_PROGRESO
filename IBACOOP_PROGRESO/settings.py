import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-^59f-cp@#)$ez20opmvdr@rk%3sr-*az6(9s+a@(3o#$h*8*#)')

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,web,0.0.0.0').split(',')


# ==============================================================================
# MODELO DE USUARIO PERSONALIZADO
# CRÍTICO: Debe definirse ANTES de la primera migración.
# ==============================================================================

AUTH_USER_MODEL = 'usuarios.Usuario'

AUTHENTICATION_BACKENDS = [
    'APPS.usuarios.backends.CUIOrEmailModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]


# ==============================================================================
# APLICACIONES INSTALADAS
# ==============================================================================

INSTALLED_APPS = [
    # Componentes principales de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps del Sistema ERP Escolar (Prioridad de plantillas e interfaces)
    'APPS.core',               # ModeloAuditable, ActivosManager (base del sistema)
    'APPS.usuarios',           # Usuario personalizado con campo 'rol'
    'APPS.estudiantes',        # Estudiante, Encargado, EstudianteEncargado
    'APPS.rrhh',               # Personal, Puesto, Asistencia, Planilla
    'APPS.academico',          # CicloEscolar, Grado, Seccion, Curso, Notas, Asistencia
    'APPS.financiero',         # MensualidadCobro, PagoColegiatura
    'APPS.inventario',         # ArticuloInventario, MovimientoInventario
    'APPS.portal',             # ContenidoWeb (portal institucional)

    # Librerías de terceros
    'tailwind',
    'theme',
    'simple_history',          # Auditoría de cambios (Notas, Pagos, Inventario)
]


# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'APPS.usuarios.middleware.EnforcePasswordChangeMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'IBACOOP_PROGRESO.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'IBACOOP_PROGRESO.wsgi.application'


# ==============================================================================
# BASE DE DATOS — PostgreSQL
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ.get('DB_NAME', 'IBACOOP_PROGRESO'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}


# ==============================================================================
# VALIDACIÓN DE CONTRASEÑAS
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ==============================================================================
# INTERNACIONALIZACIÓN
# ==============================================================================

LANGUAGE_CODE = 'es-gt'
TIME_ZONE = 'America/Guatemala'
USE_I18N = True
USE_TZ = True


# ==============================================================================
# ARCHIVOS ESTÁTICOS — WhiteNoise
# ==============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
WHITENOISE_MANIFEST_STRICT = False
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Tailwind CSS
TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = ['127.0.0.1']
if os.name == 'nt':
    NPM_BIN_PATH = os.environ.get('NPM_BIN_PATH', r"C:\Program Files\nodejs\npm.cmd")
else:
    NPM_BIN_PATH = os.environ.get('NPM_BIN_PATH', '/usr/bin/npm')

# Redirecciones de Autenticación
LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'usuarios:login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
