"""
auditoria/views.py

Vistas y controladores del Centro de Control de Auditoría y Trazabilidad.
Permite a los roles directivos y administrativos supervisar el historial inmutable de cambios,
inspeccionar diffs visuales de registros y monitorear eventos de seguridad.
"""
import csv
from datetime import datetime
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.contrib.auth import get_user_model
from axes.models import AccessAttempt, AccessLog

from APPS.auditoria.servicios import AuditoriaService, AUDITED_MODELS

Usuario = get_user_model()


class AuditoriaPermissionMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restringe el acceso exclusivamente a ADMINISTRADOR y DIRECTOR."""
    
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.rol in ['ADMINISTRADOR', 'DIRECTOR'] or user.is_superuser)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Acceso denegado: El módulo de Auditoría requiere privilegios de Administrador o Dirección.')
        return redirect('core:home')


class AuditoriaDashboardView(AuditoriaPermissionMixin, TemplateView):
    """
    Panel principal de auditoría: Línea de tiempo de cambios inmutables,
    filtros avanzados y métricas operativas de las últimas 24 horas.
    """
    template_name = 'auditoria/panel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET

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

        context.update({
            'page_obj': page_obj,
            'records': page_obj.object_list,
            'metrics': metrics,
            'modelos_auditados': AUDITED_MODELS,
            'usuarios': Usuario.objects.filter(is_active=True).order_by('username'),
            'filtros': {
                'modelo': model_key or '',
                'usuario': usuario_id or '',
                'accion': action_type or '',
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
    los campos que sufrieron modificaciones.
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
            'titulo_pagina': f"Inspección de Registro: {diff_data['cfg']['nombre']}",
        })
        return context


class AuditoriaSeguridadView(AuditoriaPermissionMixin, TemplateView):
    """
    Monitor de seguridad: Inspección de bloqueos de IP, intentos fallidos
    y bitácora de accesos generada por django-axes.
    """
    template_name = 'auditoria/seguridad.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        intentos_activos = AccessAttempt.objects.all().order_by('-failures_since_start')
        logs_recientes = AccessLog.objects.all().order_by('-attempt_time')[:100]

        context.update({
            'intentos_activos': intentos_activos,
            'logs_recientes': logs_recientes,
            'total_bloqueos': intentos_activos.count(),
            'total_accesos_registrados': AccessLog.objects.count(),
            'titulo_pagina': 'Seguridad y Accesos',
        })
        return context


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

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        fecha_str = timezone.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="auditoria_ibacoop_{fecha_str}.csv"'

        # inclusion de bom utf ocho para compatibilidad con excel
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
