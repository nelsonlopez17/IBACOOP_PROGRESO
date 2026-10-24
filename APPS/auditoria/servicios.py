"""
auditoria/services.py

Servicio unificado para la consulta, agregación y cálculo de diferencias (diffs)
de la pista de auditoría empresarial basada en django-simple-history.
"""
from datetime import datetime, time
from django.utils import timezone
from django.contrib.auth import get_user_model
from APPS.academico.models import NotaBloque, AsignacionEstudiante
from APPS.financiero.models import Abono, CuentaPorCobrar
from APPS.inventario.models import ArticuloInventario
from APPS.rrhh.models import Planilla
from APPS.disciplina.models import IncidenteDisciplinario

Usuario = get_user_model()


AUDITED_MODELS = {
    'notabloque': {
        'clave': 'notabloque',
        'nombre': 'Notas y Calificaciones',
        'modulo': 'Académico',
        'icono': 'graduation-cap',
        'badge_color': 'bg-emerald-100 text-emerald-800 border-emerald-200',
        'model_class': NotaBloque,
    },
    'abono': {
        'clave': 'abono',
        'nombre': 'Pagos y Abonos',
        'modulo': 'Financiero',
        'icono': 'receipt',
        'badge_color': 'bg-blue-100 text-blue-800 border-blue-200',
        'model_class': Abono,
    },
    'cuentaporcobrar': {
        'clave': 'cuentaporcobrar',
        'nombre': 'Cuentas por Cobrar',
        'modulo': 'Financiero',
        'icono': 'credit-card',
        'badge_color': 'bg-indigo-100 text-indigo-800 border-indigo-200',
        'model_class': CuentaPorCobrar,
    },
    'articuloinventario': {
        'clave': 'articuloinventario',
        'nombre': 'Control de Inventario',
        'modulo': 'Inventario',
        'icono': 'package',
        'badge_color': 'bg-amber-100 text-amber-800 border-amber-200',
        'model_class': ArticuloInventario,
    },
    'planilla': {
        'clave': 'planilla',
        'nombre': 'Planillas y Sueldos',
        'modulo': 'Recursos Humanos',
        'icono': 'file-text',
        'badge_color': 'bg-rose-100 text-rose-800 border-rose-200',
        'model_class': Planilla,
    },
    'asignacionestudiante': {
        'clave': 'asignacionestudiante',
        'nombre': 'Inscripción de Estudiantes',
        'modulo': 'Académico',
        'icono': 'users',
        'badge_color': 'bg-teal-100 text-teal-800 border-teal-200',
        'model_class': AsignacionEstudiante,
    },
    'incidentedisciplinario': {
        'clave': 'incidentedisciplinario',
        'nombre': 'Disciplina y Faltas',
        'modulo': 'Disciplina',
        'icono': 'shield-alert',
        'badge_color': 'bg-purple-100 text-purple-800 border-purple-200',
        'model_class': IncidenteDisciplinario,
    },
    'incidenteconductual': {
        'clave': 'incidentedisciplinario',
        'nombre': 'Disciplina y Faltas',
        'modulo': 'Disciplina',
        'icono': 'shield-alert',
        'badge_color': 'bg-purple-100 text-purple-800 border-purple-200',
        'model_class': IncidenteDisciplinario,
    },
}


class AuditoriaService:
    """Provee métodos estáticos para consultar y procesar registros de auditoría."""

    @staticmethod
    def get_registered_models():
        """Devuelve el catálogo de modelos auditados."""
        return AUDITED_MODELS

    @staticmethod
    def get_model_info(model_key):
        """Devuelve la configuración y metadatos de un modelo auditado."""
        return AUDITED_MODELS.get(model_key.lower())

    @classmethod
    def get_history_records(cls, model_key=None, usuario_id=None, action_type=None, date_from=None, date_to=None, limit=100):
        """
        Recupera y combina los registros de auditoría según los filtros especificados.
        """
        keys_to_query = [model_key.lower()] if model_key and model_key.lower() in AUDITED_MODELS else list(AUDITED_MODELS.keys())
        all_records = []

        # conversion de fechas considerando la zona horaria local
        tz = timezone.get_current_timezone()
        dt_from = timezone.make_aware(datetime.combine(date_from, time.min), tz) if date_from else None
        dt_to = timezone.make_aware(datetime.combine(date_to, time.max), tz) if date_to else None

        for k in keys_to_query:
            cfg = AUDITED_MODELS[k]
            model_cls = cfg['model_class']
            qs = model_cls.history.select_related('history_user').all()

            if usuario_id:
                qs = qs.filter(history_user_id=usuario_id)
            if action_type:
                qs = qs.filter(history_type=action_type)
            if dt_from:
                qs = qs.filter(history_date__gte=dt_from)
            if dt_to:
                qs = qs.filter(history_date__lte=dt_to)

            # limitar registros por modelo antes del ordenamiento global
            for record in qs.order_by('-history_date')[:limit]:
                all_records.append({
                    'history_id': record.history_id,
                    'model_key': k,
                    'modulo': cfg['modulo'],
                    'modelo_nombre': cfg['nombre'],
                    'icono': cfg['icono'],
                    'badge_color': cfg['badge_color'],
                    'history_date': record.history_date,
                    'history_type': record.history_type,
                    'history_type_display': cls.get_action_display(record.history_type),
                    'history_type_badge': cls.get_action_badge(record.history_type),
                    'history_user': record.history_user,
                    'history_change_reason': record.history_change_reason or 'Actualización de datos',
                    'instance_repr': str(record.instance) if hasattr(record, 'instance') and record.instance else f"{cfg['nombre']} #{record.history_id}",
                    'record_obj': record,
                })

        all_records.sort(key=lambda x: x['history_date'], reverse=True)
        return all_records[:limit]

    @staticmethod
    def get_action_display(action_type):
        if action_type == '+':
            return 'Creación'
        elif action_type == '~':
            return 'Modificación'
        elif action_type == '-':
            return 'Eliminación'
        return 'Operación'

    @staticmethod
    def get_action_badge(action_type):
        if action_type == '+':
            return {'label': 'Creación (+)', 'class': 'bg-emerald-50 text-emerald-700 border-emerald-300'}
        elif action_type == '~':
            return {'label': 'Modificación (~)', 'class': 'bg-amber-50 text-amber-700 border-amber-300'}
        elif action_type == '-':
            return {'label': 'Eliminación (-)', 'class': 'bg-rose-50 text-rose-700 border-rose-300'}
        return {'label': 'Registro', 'class': 'bg-slate-50 text-slate-700 border-slate-300'}

    @classmethod
    def get_record_diff(cls, model_key, history_id):
        """
        Obtiene el detalle de diferencias (diff) entre la versión seleccionada
        y su versión predecesora inmediata.
        """
        cfg = cls.get_model_info(model_key)
        if not cfg:
            return None

        model_cls = cfg['model_class']
        try:
            current_record = model_cls.history.get(history_id=history_id)
        except model_cls.history.model.DoesNotExist:
            return None

        prev_record = current_record.prev_record
        if not prev_record and current_record.history_type != '+':
            # busqueda del registro previo en caso de colision de tiempo
            pk_name = model_cls._meta.pk.name
            pk_val = getattr(current_record, pk_name, None)
            if pk_val is not None:
                prev_record = (
                    model_cls.history
                    .filter(**{pk_name: pk_val, 'history_id__lt': current_record.history_id})
                    .order_by('history_id')
                    .last()
                )

        changes = []

        if prev_record:
            delta = current_record.diff_against(prev_record)
            for change in delta.changes:
                # omitir campos tecnicos de auditoria interna
                if change.field in ['actualizado_en', 'history_id', 'history_date', 'history_user', 'history_type', 'history_change_reason']:
                    continue

                changes.append({
                    'field': change.field,
                    'old_value': change.old if change.old is not None else '(Vacío)',
                    'new_value': change.new if change.new is not None else '(Vacío)',
                })
        else:
            for field in current_record._meta.fields:
                if field.name.startswith('history_') or field.name in ['actualizado_en']:
                    continue
                val = getattr(current_record, field.name, None)
                if val not in [None, '']:
                    changes.append({
                        'field': field.verbose_name or field.name,
                        'old_value': '(Registro inicial)',
                        'new_value': str(val),
                    })

        return {
            'record': current_record,
            'prev_record': prev_record,
            'cfg': cfg,
            'changes': changes,
            'history_type_display': cls.get_action_display(current_record.history_type),
            'history_type_badge': cls.get_action_badge(current_record.history_type),
            'instance_repr': str(current_record.instance) if hasattr(current_record, 'instance') and current_record.instance else f"{cfg['nombre']} #{current_record.history_id}",
        }

    @classmethod
    def get_dashboard_metrics(cls):
        """Calcula métricas globales de actividad para el panel de auditoría."""
        ahora = timezone.now()
        hace_24h = ahora - timezone.timedelta(hours=24)
        
        total_hoy = 0
        creaciones_hoy = 0
        modificaciones_hoy = 0
        eliminaciones_hoy = 0
        usuarios_activos = set()

        for cfg in AUDITED_MODELS.values():
            model_cls = cfg['model_class']
            qs = model_cls.history.filter(history_date__gte=hace_24h)
            total_hoy += qs.count()
            creaciones_hoy += qs.filter(history_type='+').count()
            modificaciones_hoy += qs.filter(history_type='~').count()
            eliminaciones_hoy += qs.filter(history_type='-').count()
            
            user_ids = qs.values_list('history_user_id', flat=True)
            for uid in user_ids:
                if uid:
                    usuarios_activos.add(uid)

        return {
            'total_24h': total_hoy,
            'creaciones_24h': creaciones_hoy,
            'modificaciones_24h': modificaciones_hoy,
            'eliminaciones_24h': eliminaciones_hoy,
            'usuarios_activos_count': len(usuarios_activos),
        }
