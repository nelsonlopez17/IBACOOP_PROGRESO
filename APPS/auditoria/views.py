"""
auditoria/views.py

Vistas y controladores del Centro de Control de Auditoría y Trazabilidad.
Permite a los roles directivos y administrativos supervisar el historial inmutable de cambios,
inspeccionar diffs visuales de registros y monitorear/desbloquear eventos de seguridad.
"""
import csv
from datetime import datetime, timedelta
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404, JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from axes.models import AccessAttempt, AccessLog
from axes.utils import reset

from APPS.auditoria.servicios import AuditoriaService, AUDITED_MODELS
from APPS.auditoria.models import EventoSeguridad, TipoEventoSeguridad, registrar_evento_seguridad

Usuario = get_user_model()


class AuditoriaPermissionMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Acceso restringido a Administradores y Dirección, o usuarios con permiso explícito."""

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(
            user.is_superuser
            or getattr(user, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR']
            or user.groups.filter(name__in=['Administradores', 'Directores']).exists()
            or user.has_perm('auditoria.view_registroauditoria')
        )

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        registrar_evento_seguridad(
            tipo=TipoEventoSeguridad.ACCESO_DENEGADO,
            request=self.request,
            usuario=self.request.user,
            descripcion='Intento de acceso denegado a módulo de auditoría restringido'
        )
        messages.error(self.request, 'Acceso denegado: El módulo de Auditoría requiere privilegios de Administrador o Dirección.')
        return redirect('core:home')


class AuditoriaDashboardView(AuditoriaPermissionMixin, TemplateView):
    """
    Panel principal de auditoría: Línea de tiempo de cambios inmutables,
    filtros avanzados, presets rápidos y métricas operativas de las últimas 24 horas.
    """
    template_name = 'auditoria/panel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET

        model_key = params.get('modelo', '').strip() or None
        usuario_id = params.get('usuario', '').strip() or None
        action_type = params.get('accion', '').strip() or None
        preset = params.get('preset', '').strip().lower()
        date_from_str = params.get('fecha_inicio', '').strip()
        date_to_str = params.get('fecha_fin', '').strip()

        hoy = timezone.localdate()
        date_from = None
        date_to = None

        if preset == 'hoy':
            date_from = hoy
            date_to = hoy
            date_from_str = hoy.strftime('%Y-%m-%d')
            date_to_str = hoy.strftime('%Y-%m-%d')
        elif preset == 'semana':
            date_from = hoy - timedelta(days=7)
            date_to = hoy
            date_from_str = date_from.strftime('%Y-%m-%d')
            date_to_str = hoy.strftime('%Y-%m-%d')
        elif preset == 'mes':
            date_from = hoy.replace(day=1)
            date_to = hoy
            date_from_str = date_from.strftime('%Y-%m-%d')
            date_to_str = hoy.strftime('%Y-%m-%d')
        else:
            try:
                if date_from_str:
                    date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
                if date_to_str:
                    date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        all_records = AuditoriaService.get_history_records(
            model_key=model_key,
            usuario_id=int(usuario_id) if usuario_id and usuario_id.isdigit() else None,
            action_type=action_type if action_type in ['+', '~', '-'] else None,
            date_from=date_from,
            date_to=date_to,
            limit=250
        )

        paginator = Paginator(all_records, 25)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        metrics = AuditoriaService.get_dashboard_metrics()

        # Construir querystring limpio sin el parámetro 'page' para paginación precisa
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        filtro_querystring = query_params.urlencode()

        context.update({
            'page_obj': page_obj,
            'records': page_obj.object_list,
            'metrics': metrics,
            'modelos_auditados': AUDITED_MODELS,
            'usuarios': Usuario.objects.filter(is_active=True).select_related('persona').order_by('username'),
            'filtro_querystring': filtro_querystring,
            'filtros': {
                'modelo': model_key or '',
                'usuario': usuario_id or '',
                'accion': action_type or '',
                'preset': preset or '',
                'fecha_inicio': date_from_str or '',
                'fecha_fin': date_to_str or '',
            },
            'titulo_pagina': 'Auditoría y Trazabilidad',
        })
        return context


class AuditoriaDetalleDiffView(AuditoriaPermissionMixin, TemplateView):
    """
    Visor visual de diferencias (Diff Viewer):
    Compara la versión seleccionada contra la versión anterior resaltando
    los campos que sufrieron modificaciones con soporte para saltar a versiones adyacentes.
    """
    template_name = 'auditoria/diferencia_detalle.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model_key = self.kwargs.get('modelo', '').lower()
        history_id = self.kwargs.get('history_id')

        diff_data = AuditoriaService.get_record_diff(model_key, history_id)
        if not diff_data:
            raise Http404('El registro histórico de auditoría solicitado no existe.')

        context.update({
            'diff_data': diff_data,
            'model_key': model_key,
            'titulo_pagina': f"Inspección de Registro: {diff_data['cfg']['nombre']}",
        })
        return context


class AuditoriaSeguridadView(AuditoriaPermissionMixin, TemplateView):
    """
    Monitor de seguridad: Inspección de bloqueos de IP, intentos fallidos
    y bitácora de accesos generada por django-axes con paginación integrada.
    """
    template_name = 'auditoria/seguridad.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        intentos_activos = AccessAttempt.objects.all().order_by('-failures_since_start')
        total_bloqueados = intentos_activos.filter(failures_since_start__gte=3).count()

        logs_qs = AccessLog.objects.all().order_by('-attempt_time')
        paginator = Paginator(logs_qs, 25)
        page_number = self.request.GET.get('page')
        logs_page = paginator.get_page(page_number)

        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        filtro_querystring = query_params.urlencode()

        eventos_qs = EventoSeguridad.objects.all().select_related('usuario').order_by('-fecha')
        tipo_filtro = self.request.GET.get('tipo_evento', '').strip()
        if tipo_filtro:
            eventos_qs = eventos_qs.filter(tipo=tipo_filtro)
        paginator_eventos = Paginator(eventos_qs, 20)
        eventos_page = paginator_eventos.get_page(self.request.GET.get('page_eventos'))

        context.update({
            'intentos_activos': intentos_activos,
            'logs_recientes': logs_page,
            'page_obj': logs_page,
            'eventos_seguridad': eventos_page,
            'page_eventos_obj': eventos_page,
            'total_eventos_seguridad': eventos_qs.count(),
            'total_accesos_denegados': EventoSeguridad.objects.filter(tipo=TipoEventoSeguridad.ACCESO_DENEGADO).count(),
            'tipos_evento': TipoEventoSeguridad.choices,
            'tipo_filtro_actual': tipo_filtro,
            'filtro_querystring': filtro_querystring,
            'total_bloqueos': total_bloqueados,
            'total_intentos_sospechosos': intentos_activos.count(),
            'total_accesos_registrados': AccessLog.objects.count(),
            'titulo_pagina': 'Seguridad y Accesos',
        })
        return context


class DesbloquearAccesoView(AuditoriaPermissionMixin, View):
    """
    Permite al Administrador desbloquear una cuenta o dirección IP restringida
    por políticas de fuerza bruta en django-axes.
    """

    def post(self, request, attempt_id=None, *args, **kwargs):
        aid = attempt_id or request.POST.get('attempt_id')
        ip_addr = request.POST.get('ip_address')
        username = request.POST.get('username')

        identificador = "el intento"
        if aid:
            attempt = get_object_or_404(AccessAttempt, pk=aid)
            identificador = f"la cuenta o IP '{attempt.username or attempt.ip_address}'"
            reset(ip=attempt.ip_address, username=attempt.username, ip_or_username=True)
            attempt.delete()
        elif ip_addr or username:
            identificador = f"'{username or ip_addr}'"
            reset(ip=ip_addr or None, username=username or None, ip_or_username=True)
            AccessAttempt.objects.filter(
                Q(ip_address=ip_addr) | Q(username=username)
            ).delete()
        else:
            messages.warning(request, 'No se especificó la cuenta o IP a desbloquear.')
            return redirect('auditoria:seguridad')

        messages.success(request, f'Se ha desbloqueado exitosamente {identificador}.')
        registrar_evento_seguridad(
            tipo=TipoEventoSeguridad.DESBLOQUEO_CUENTA,
            request=request,
            usuario=request.user,
            descripcion=f"Desbloqueo administrativo de {identificador}"
        )
        return redirect('auditoria:seguridad')


class ExportarAuditoriaCSVView(AuditoriaPermissionMixin, View):
    """Exporta los registros filtrados de auditoría a formato CSV compatible con Excel."""

    def get(self, request, *args, **kwargs):
        params = request.GET
        model_key = params.get('modelo', '').strip() or None
        usuario_id = params.get('usuario', '').strip() or None
        action_type = params.get('accion', '').strip() or None
        date_from_str = params.get('fecha_inicio', '').strip()
        date_to_str = params.get('fecha_fin', '').strip()

        date_from = None
        date_to = None
        try:
            if date_from_str:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            if date_to_str:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
        except ValueError:
            pass

        records = AuditoriaService.get_history_records(
            model_key=model_key,
            usuario_id=int(usuario_id) if usuario_id and usuario_id.isdigit() else None,
            action_type=action_type if action_type in ['+', '~', '-'] else None,
            date_from=date_from,
            date_to=date_to,
            limit=1000
        )

        registrar_evento_seguridad(
            tipo=TipoEventoSeguridad.DESCARGA_REPORTE,
            request=request,
            usuario=request.user,
            descripcion=f"Exportación de auditoría en CSV. Modelo: {model_key or 'Todos'}, Acción: {action_type or 'Todas'}"
        )

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        fecha_str = timezone.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="auditoria_ibacoop_{fecha_str}.csv"'

        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow([
            'ID Histórico',
            'Fecha y Hora (Local)',
            'Módulo',
            'Entidad / Modelo',
            'Tipo de Acción',
            'Usuario Responsable',
            'Registro Afectado',
            'Motivo / Justificación'
        ])

        def sanitize(val):
            val_str = str(val or '')
            if val_str and val_str[0] in ('=', '+', '-', '@', '\t', '\r'):
                return f"'{val_str}"
            return val_str

        for r in records:
            user_str = r['history_user'].username if r['history_user'] else 'Sistema / Desconocido'
            fecha_local = timezone.localtime(r['history_date']).strftime('%d/%m/%Y %H:%M:%S')
            writer.writerow([
                r['history_id'],
                fecha_local,
                sanitize(r['modulo']),
                sanitize(r['modelo_nombre']),
                sanitize(r['history_type_display']),
                sanitize(user_str),
                sanitize(r['instance_repr']),
                sanitize(r['history_change_reason'])
            ])

        return response
