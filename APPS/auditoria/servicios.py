"""
auditoria/servicios.py

Servicio unificado para la consulta, agregación y cálculo de diferencias (diffs)
de la pista de auditoría empresarial basada en django-simple-history.
"""
from datetime import datetime, time
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Count, Case, When, IntegerField

from APPS.academico.models import NotaBloque, AsignacionEstudiante
from APPS.financiero.models import Abono, CuentaPorCobrar
from APPS.inventario.models import ArticuloInventario
from APPS.rrhh.models import Planilla
from APPS.disciplina.models import IncidenteDisciplinario, CitacionPadre
from APPS.portal.models import ConfiguracionPortal, ContenidoWeb, FotoGaleria, SolicitudContacto

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
    'asignacionestudiante': {
        'clave': 'asignacionestudiante',
        'nombre': 'Inscripción de Estudiantes',
        'modulo': 'Académico',
        'icono': 'users',
        'badge_color': 'bg-teal-100 text-teal-800 border-teal-200',
        'model_class': AsignacionEstudiante,
    },
    'abono': {
        'clave': 'abono',
        'nombre': 'Pagos y Boletas de Abono',
        'modulo': 'Financiero',
        'icono': 'receipt',
        'badge_color': 'bg-blue-100 text-blue-800 border-blue-200',
        'model_class': Abono,
    },
    'cuentaporcobrar': {
        'clave': 'cuentaporcobrar',
        'nombre': 'Cuentas por Cobrar (Cuotas)',
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
        'nombre': 'Planilla de Sueldos',
        'modulo': 'Recursos Humanos',
        'icono': 'file-text',
        'badge_color': 'bg-rose-100 text-rose-800 border-rose-200',
        'model_class': Planilla,
    },
    'incidentedisciplinario': {
        'clave': 'incidentedisciplinario',
        'nombre': 'Incidentes Disciplinarios',
        'modulo': 'Disciplina y Convivencia',
        'icono': 'shield-alert',
        'badge_color': 'bg-purple-100 text-purple-800 border-purple-200',
        'model_class': IncidenteDisciplinario,
    },
    'citacionpadre': {
        'clave': 'citacionpadre',
        'nombre': 'Citaciones a Encargados',
        'modulo': 'Disciplina y Convivencia',
        'icono': 'mail',
        'badge_color': 'bg-violet-100 text-violet-800 border-violet-200',
        'model_class': CitacionPadre,
    },
    'usuario': {
        'clave': 'usuario',
        'nombre': 'Cuentas y Usuarios del Sistema',
        'modulo': 'Seguridad y Acceso',
        'icono': 'user-check',
        'badge_color': 'bg-sky-100 text-sky-800 border-sky-200',
        'model_class': Usuario,
    },
    'configuracionportal': {
        'clave': 'configuracionportal',
        'nombre': 'Ajustes del Portal Web',
        'modulo': 'Portal Web',
        'icono': 'sliders',
        'badge_color': 'bg-emerald-100 text-emerald-800 border-emerald-200',
        'model_class': ConfiguracionPortal,
    },
    'contenidoweb': {
        'clave': 'contenidoweb',
        'nombre': 'Publicaciones y Comunicados',
        'modulo': 'Portal Web',
        'icono': 'newspaper',
        'badge_color': 'bg-blue-100 text-blue-800 border-blue-200',
        'model_class': ContenidoWeb,
    },
    'fotogaleria': {
        'clave': 'fotogaleria',
        'nombre': 'Galería de Fotos',
        'modulo': 'Portal Web',
        'icono': 'image',
        'badge_color': 'bg-purple-100 text-purple-800 border-purple-200',
        'model_class': FotoGaleria,
    },
    'solicitudcontacto': {
        'clave': 'solicitudcontacto',
        'nombre': 'Mensajes de Contacto (Web)',
        'modulo': 'Portal Web',
        'icono': 'inbox',
        'badge_color': 'bg-amber-100 text-amber-800 border-amber-200',
        'model_class': SolicitudContacto,
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
        return AUDITED_MODELS.get(model_key.lower()) if model_key else None

    @classmethod
    def get_history_records(cls, model_key=None, usuario_id=None, action_type=None, date_from=None, date_to=None, limit=100):
        """
        Recupera y combina los registros de auditoría según los filtros especificados.
        """
        keys_to_query = [model_key.lower()] if model_key and model_key.lower() in AUDITED_MODELS else list(AUDITED_MODELS.keys())
        all_records = []

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
        y su versión predecesora inmediata, traduciendo campos técnicos a nombres legibles.
        """
        cfg = cls.get_model_info(model_key)
        if not cfg:
            return None

        model_cls = cfg['model_class']
        try:
            current_record = model_cls.history.get(history_id=history_id)
        except model_cls.history.model.DoesNotExist:
            return None

        pk_name = model_cls._meta.pk.name
        pk_val = getattr(current_record, pk_name, None)

        prev_id = None
        next_id = None
        if pk_val is not None:
            instancia_historial = list(
                model_cls.history
                .filter(**{pk_name: pk_val})
                .order_by('history_id')
                .values_list('history_id', flat=True)
            )
            if current_record.history_id in instancia_historial:
                cur_idx = instancia_historial.index(current_record.history_id)
                if cur_idx > 0:
                    prev_id = instancia_historial[cur_idx - 1]
                if cur_idx < len(instancia_historial) - 1:
                    next_id = instancia_historial[cur_idx + 1]

        prev_record = current_record.prev_record
        if not prev_record and current_record.history_type != '+' and prev_id:
            try:
                prev_record = model_cls.history.get(history_id=prev_id)
            except model_cls.history.model.DoesNotExist:
                pass

        # mapeo de verbose_name de los campos del modelo original
        field_verbose_map = {}
        for f in model_cls._meta.get_fields():
            if hasattr(f, 'verbose_name'):
                field_verbose_map[f.name] = str(f.verbose_name)

        changes = []

        if prev_record:
            delta = current_record.diff_against(prev_record)
            for change in delta.changes:
                if change.field in ['actualizado_en', 'creado_en', 'history_id', 'history_date', 'history_user', 'history_type', 'history_change_reason']:
                    continue

                label = field_verbose_map.get(change.field, change.field.replace('_', ' ').capitalize())
                old_val = change.old
                new_val = change.new

                changes.append({
                    'field_name': change.field,
                    'field': label,
                    'old_value': cls._format_diff_val(old_val),
                    'new_value': cls._format_diff_val(new_val),
                })
        else:
            for field in current_record._meta.fields:
                if field.name.startswith('history_') or field.name in ['actualizado_en', 'creado_en']:
                    continue
                val = getattr(current_record, field.name, None)
                if val not in [None, '']:
                    label = field_verbose_map.get(field.name, getattr(field, 'verbose_name', field.name))
                    changes.append({
                        'field_name': field.name,
                        'field': label,
                        'old_value': '(Registro inicial)',
                        'new_value': cls._format_diff_val(val),
                    })

        return {
            'record': current_record,
            'prev_record': prev_record,
            'prev_id': prev_id,
            'next_id': next_id,
            'cfg': cfg,
            'changes': changes,
            'history_type_display': cls.get_action_display(current_record.history_type),
            'history_type_badge': cls.get_action_badge(current_record.history_type),
            'instance_repr': str(current_record.instance) if hasattr(current_record, 'instance') and current_record.instance else f"{cfg['nombre']} #{current_record.history_id}",
        }

    @staticmethod
    def _format_diff_val(val):
        if val is None or val == '':
            return '(Vacío)'
        if isinstance(val, bool):
            return 'Sí' if val else 'No'
        return str(val)

    @classmethod
    def get_dashboard_metrics(cls):
        """Calcula métricas globales de actividad para el panel de auditoría de forma agregada."""
        ahora = timezone.now()
        hace_24h = ahora - timezone.timedelta(hours=24)

        total_hoy = 0
        creaciones_hoy = 0
        modificaciones_hoy = 0
        eliminaciones_hoy = 0
        usuarios_activos = set()

        for cfg in AUDITED_MODELS.values():
            model_cls = cfg['model_class']
            agg = model_cls.history.filter(history_date__gte=hace_24h).aggregate(
                total=Count('history_id'),
                creaciones=Count(Case(When(history_type='+', then=1), output_field=IntegerField())),
                modificaciones=Count(Case(When(history_type='~', then=1), output_field=IntegerField())),
                eliminaciones=Count(Case(When(history_type='-', then=1), output_field=IntegerField())),
            )
            total_hoy += agg['total'] or 0
            creaciones_hoy += agg['creaciones'] or 0
            modificaciones_hoy += agg['modificaciones'] or 0
            eliminaciones_hoy += agg['eliminaciones'] or 0

            if agg['total']:
                user_ids = model_cls.history.filter(
                    history_date__gte=hace_24h,
                    history_user__isnull=False
                ).values_list('history_user_id', flat=True).distinct()
                usuarios_activos.update(user_ids)

        return {
            'total_24h': total_hoy,
            'creaciones_24h': creaciones_hoy,
            'modificaciones_24h': modificaciones_hoy,
            'eliminaciones_24h': eliminaciones_hoy,
            'usuarios_activos_count': len(usuarios_activos),
        }
