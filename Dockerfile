# ==============================================================================
# DOCKERFILE — ERP ESCOLAR INSTITUTO "EL PROGRESO" (Nivel Básico — Guatemala)
# Python 3.12 + Node.js (Tailwind v4) + PostgreSQL Driver
# ==============================================================================

FROM python:3.12-slim

# Prevenir generación de archivos .pyc y forzar buffer de salida limpio
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=America/Guatemala

# Directorio de trabajo principal
WORKDIR /app

# Instalación de dependencias del sistema operativo (incluye Node.js/npm para Tailwind y tzdata para zona horaria de Guatemala)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    netcat-openbsd \
    libpq-dev \
    gcc \
    curl \
    nodejs \
    npm \
    && ln -fs /usr/share/zoneinfo/America/Guatemala /etc/localtime \
    && echo "America/Guatemala" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente completo de la aplicación
COPY . /app/

# Dar permisos de ejecución al script entrypoint.sh (soporta finales de línea LF)
RUN chmod +x /app/entrypoint.sh && \
    sed -i 's/\r$//' /app/entrypoint.sh

# Recopilar archivos estáticos para WhiteNoise durante la construcción
RUN SECRET_KEY="build-key-for-collectstatic" python manage.py collectstatic --noinput

# Puerto expuesto por el contenedor
EXPOSE 8000

# Script de entrada para migraciones y recolección de estáticos
ENTRYPOINT ["/app/entrypoint.sh"]

# Comando por defecto: Servidor WSGI Gunicorn para producción/despliegue (soporta $PORT de Render o 8000 por defecto)
CMD ["sh", "-c", "gunicorn IBACOOP_PROGRESO.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"]
