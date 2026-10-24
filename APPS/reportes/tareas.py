"""
APPS/reportes/tareas.py

Procesamiento en segundo plano para la generación de boletas de calificaciones.
Permite procesar en lote la generación de decenas o cientos de boletas de calificaciones
y empaquetarlas en archivos ZIP sin bloquear la aplicación web y sin requerir
servicios externos como Redis o trabajadores Celery dedicados.
"""
import uuid
import zipfile
import threading
from pathlib import Path
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from APPS.academico.models import Seccion, CicloEscolar, AsignacionEstudiante
from APPS.reportes.reportes_academicos import generar_pdf_boleta_calificaciones

CACHE_PREFIX = "tarea_boletas_"
CACHE_TIMEOUT = 7200  # 2 horas de persistencia para descarga


def obtener_estado_tarea(task_id):
    """Recupera el estado actual de la tarea desde la caché del sistema."""
    return cache.get(f"{CACHE_PREFIX}{task_id}")


def actualizar_estado_tarea(task_id, data):
    """Actualiza la información de progreso o resultado de la tarea en caché."""
    cache.set(f"{CACHE_PREFIX}{task_id}", data, timeout=CACHE_TIMEOUT)


def generar_boletas_seccion_zip(task_id, seccion_id, ciclo_id):
    """
    Ejecuta la emisión de boletas de calificaciones individuales (PDF)
    de los estudiantes inscritos en una sección y los empaqueta en un archivo .ZIP.
    Actualiza el estado progresivo (0% a 100%) en la caché para consulta en tiempo real desde la web.
    """
    try:
        try:
            seccion = Seccion.objects.select_related('grado').get(id=seccion_id)
            ciclo = CicloEscolar.objects.get(id=ciclo_id)
        except (Seccion.DoesNotExist, CicloEscolar.DoesNotExist) as e:
            actualizar_estado_tarea(task_id, {
                'state': 'FAILURE',
                'status': 'ERROR',
                'percent': 0,
                'error': str(e),
                'mensaje': str(e),
            })
            return

        asignaciones = AsignacionEstudiante.objects.filter(
            seccion=seccion,
            ciclo_escolar=ciclo,
            esta_eliminado=False
        ).select_related('estudiante__persona')

        total_estudiantes = asignaciones.count()

        if total_estudiantes == 0:
            actualizar_estado_tarea(task_id, {
                'state': 'SUCCESS',
                'status': 'COMPLETADO',
                'percent': 100,
                'total': 0,
                'mensaje': f'No hay estudiantes inscritos en {seccion.grado.nombre} {seccion.letra} para el ciclo {ciclo.anio}.',
                'archivo_url': None,
                'filename': '',
                'seccion': f"{seccion.grado.nombre} - Sección {seccion.letra}",
            })
            return

        output_dir = Path(settings.MEDIA_ROOT) / 'reportes_lotes'
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"Boletas_{seccion.grado.nombre.replace(' ', '_')}_{seccion.letra}_{ciclo.anio}_{timestamp}.zip"
        zip_filepath = output_dir / zip_filename

        with zipfile.ZipFile(zip_filepath, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            for idx, asignacion in enumerate(asignaciones, start=1):
                estudiante = asignacion.estudiante
                persona = estudiante.persona

                percent = int((idx / total_estudiantes) * 100)
                actualizar_estado_tarea(task_id, {
                    'state': 'PROGRESS',
                    'percent': percent,
                    'current': idx,
                    'total': total_estudiantes,
                    'estudiante_actual': persona.nombre_completo,
                    'seccion': f"{seccion.grado.nombre} - Sección {seccion.letra}",
                })

                try:
                    pdf_bytes = generar_pdf_boleta_calificaciones(estudiante, ciclo)
                    pdf_filename = f"Boleta_{persona.apellidos.replace(' ', '_')}_{persona.nombres.replace(' ', '_')}.pdf"
                    zip_file.writestr(pdf_filename, pdf_bytes)
                except Exception as e:
                    error_txt = f"Error al generar boleta de {persona.nombre_completo}: {str(e)}"
                    zip_file.writestr(f"ERROR_{persona.apellidos.replace(' ', '_')}.txt", error_txt.encode('utf-8'))

        download_url = f"{settings.MEDIA_URL}reportes_lotes/{zip_filename}"
        resultado = {
            'state': 'SUCCESS',
            'status': 'COMPLETADO',
            'percent': 100,
            'total': total_estudiantes,
            'archivo_url': download_url,
            'filename': zip_filename,
            'seccion': f"{seccion.grado.nombre} - Sección {seccion.letra}",
            'ciclo': ciclo.anio,
            'mensaje': f'Se generaron con éxito {total_estudiantes} boletas de calificaciones.',
        }
        actualizar_estado_tarea(task_id, resultado)
        return resultado

    except Exception as e:
        actualizar_estado_tarea(task_id, {
            'state': 'FAILURE',
            'status': 'ERROR',
            'percent': 0,
            'error': str(e),
            'mensaje': f'Ocurrió un error al procesar el lote: {str(e)}',
        })
    finally:
        connection.close()


def iniciar_generacion_boletas_seccion_zip(seccion_id, ciclo_id, sincrono=False):
    """
    Inicia la generación en segundo plano o de forma síncrona (según se requiera).
    Retorna el identificador único (UUID) de la tarea.
    """
    task_id = str(uuid.uuid4())
    actualizar_estado_tarea(task_id, {
        'state': 'PENDING',
        'percent': 0,
        'mensaje': 'Iniciando generación de boletas...',
    })

    if sincrono:
        generar_boletas_seccion_zip(task_id, seccion_id, ciclo_id)
    else:
        thread = threading.Thread(
            target=generar_boletas_seccion_zip,
            args=(task_id, seccion_id, ciclo_id),
            daemon=True
        )
        thread.start()

    return task_id
