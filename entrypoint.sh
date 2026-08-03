#!/bin/sh
set -e

echo "=== INICIANDO CONTENEDOR ERP ESCOLAR — INSTITUTO EL PROGRESO ==="

# Esperar a que la base de datos PostgreSQL esté lista
if [ "$DB_HOST" ]; then
    echo "Esperando conexión a la base de datos PostgreSQL en $DB_HOST:$DB_PORT..."
    while ! nc -z $DB_HOST ${DB_PORT:-5432}; do
      sleep 1
    done
    echo "✓ Conexión establecida con la base de datos PostgreSQL."
fi

# Aplicar migraciones pendientes
echo "Ejecutando migraciones de base de datos..."
python manage.py migrate --noinput

# Recopilar archivos estáticos
echo "Recopilando archivos estáticos..."
python manage.py collectstatic --noinput --clear || true

echo "=== SERVIDOR LISTO — INICIANDO APLICACIÓN ==="

# Ejecutar el comando especificado en CMD
exec "$@"
