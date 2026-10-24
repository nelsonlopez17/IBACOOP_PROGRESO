"""
reportes/views.py

Vistas y controladores del Centro de Reportes y Business Intelligence (BI).
Gestiona el Hub Centralizado de Reportes y la emisión parametrizada en PDF y CSV.
"""
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import HttpResponse, Http404, JsonResponse
from django.utils import timezone
from APPS.reportes.tareas import (
    iniciar_generacion_boletas_seccion_zip,
    obtener_estado_tarea,
)

from APPS.academico.models import CicloEscolar, Seccion, BloqueAcademico
from APPS.estudiantes.models import Estudiante
from APPS.financiero.models import BecaDescuento
from APPS.reportes.generadores.base_csv import IBACOOPReportCSV

from APPS.reportes.reportes_academicos import (
    generar_pdf_boleta_calificaciones,
    generar_csv_cuadro_honor,
    generar_csv_sabana_notas,
)
from APPS.reportes.reportes_financieros import (
    generar_pdf_antiguedad_saldos,
    generar_csv_antiguedad_saldos,
    generar_csv_cuadre_caja,
)
from APPS.reportes.reportes_rrhh import (
    generar_pdf_consolidado_planillas,
    generar_csv_consolidado_planillas,
)
from APPS.reportes.reportes_inventario import (
    generar_pdf_inventario_valorado,
    generar_csv_inventario_valorado,
)


class ReportesBasePermissionMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin base para el control de acceso con redirección y mensaje amigable."""
    error_message = 'No tiene permisos suficientes para acceder a este reporte institucional.'

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, self.error_message)
        return redirect('core:home')


class ReportesHubPermissionMixin(ReportesBasePermissionMixin):
    """Acceso al Hub central de reportes (Administrador, Dirección, Secretaría y Contabilidad)."""
    
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.rol in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA', 'CONTADOR'] or user.is_superuser
        )


class ReportesAcademicosPermissionMixin(ReportesBasePermissionMixin):
    """Restringe reportes académicos exclusivamente a Dirección, Secretaría y Administración."""
    error_message = 'Acceso denegado: Los reportes académicos están reservados a Dirección y Secretaría.'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.rol in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA'] or user.is_superuser
        )


class ReportesFinancierosPermissionMixin(ReportesBasePermissionMixin):
    """Restringe reportes de cobranza, saldos y caja a Dirección, Contabilidad y Administración."""
    error_message = 'Acceso denegado: Los reportes financieros están reservados a Dirección y Contabilidad.'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.rol in ['ADMINISTRADOR', 'DIRECTOR', 'CONTADOR'] or user.is_superuser
        )


class ReportesRRHHPermissionMixin(ReportesBasePermissionMixin):
    """Restringe planillas de sueldos y salarios a Contabilidad y Dirección (evita acceso no autorizado de secretaría)."""
    error_message = 'Acceso denegado: La planilla de salarios docentes está reservada a Dirección y Contabilidad.'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.rol in ['ADMINISTRADOR', 'DIRECTOR', 'CONTADOR'] or user.is_superuser or user.has_perm('rrhh.view_planilla')
        )


class ReportesInventarioPermissionMixin(ReportesBasePermissionMixin):
    """Acceso a reportes de inventario y bienes institucionales."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.rol in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA', 'CONTADOR'] or user.is_superuser
        )


class ReportesHubView(ReportesHubPermissionMixin, TemplateView):
    """
    Hub Central de Reportes y Business Intelligence:
    Organizado en 4 cuadrantes (Académico, Financiero, RRHH e Inventario)
    con selectores de filtrado paramétrico interactivo.
    """
    template_name = 'reportes/panel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        ciclos = CicloEscolar.objects.filter(esta_eliminado=False).order_by('-anio')
        secciones = Seccion.objects.filter(esta_eliminado=False).select_related('grado').order_by('grado__orden', 'letra')
        estudiantes = Estudiante.objects.filter(esta_eliminado=False).select_related('persona').order_by('persona__apellidos')

        context.update({
            'ciclo_activo': ciclo_activo,
            'ciclos': ciclos,
            'secciones': secciones,
            'estudiantes': estudiantes,
            'hoy': timezone.now().date(),
            'titulo_pagina': 'Centro de Reportes y BI',
        })
        return context



class DescargarBoletaCalificacionesPDFView(ReportesAcademicosPermissionMixin, View):
    """Descarga de la Boleta Oficial de Calificaciones por Estudiante."""

    def get(self, request, estudiante_id, ciclo_id, *args, **kwargs):
        estudiante = get_object_or_404(Estudiante, pk=estudiante_id)
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)
        return generar_pdf_boleta_calificaciones(estudiante, ciclo)


class ReporteCuadroHonorView(ReportesAcademicosPermissionMixin, View):
    """Emisión del Cuadro de Honor / Ranking de la Sección."""

    def get(self, request, *args, **kwargs):
        seccion_id = request.GET.get('seccion_id')
        ciclo_id = request.GET.get('ciclo_id')

        if not seccion_id or not ciclo_id:
            messages.error(request, 'Debe seleccionar una sección y un ciclo escolar.')
            return redirect('reportes:hub')

        seccion = get_object_or_404(Seccion, pk=seccion_id)
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)
        return generar_csv_cuadro_honor(seccion, ciclo)


class ReporteSabanaNotasView(ReportesAcademicosPermissionMixin, View):
    """Emisión de la Sábana Consolidada de Notas (Cuadro MED) de la Sección."""

    def get(self, request, *args, **kwargs):
        seccion_id = request.GET.get('seccion_id')
        ciclo_id = request.GET.get('ciclo_id')

        if not seccion_id or not ciclo_id:
            messages.error(request, 'Debe seleccionar una sección y un ciclo escolar.')
            return redirect('reportes:hub')

        seccion = get_object_or_404(Seccion, pk=seccion_id)
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)
        return generar_csv_sabana_notas(seccion, ciclo)


class ReporteAlertasTempranasExportView(ReportesAcademicosPermissionMixin, View):
    """Exportación a CSV de Alertas Tempranas (estudiantes reprobados)."""

    def get(self, request, *args, **kwargs):
        ciclo_id = request.GET.get('ciclo_id')
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id) if ciclo_id else CicloEscolar.objects.filter(estado_activo=True).first()

        from APPS.academico.models import NotaBloque
        notas_reprobadas = NotaBloque.objects.filter(
            curso__grado__esta_eliminado=False,
            esta_eliminado=False
        ).select_related('asignacion_estudiante__estudiante__persona', 'curso', 'bloque_academico')

        if ciclo:
            notas_reprobadas = notas_reprobadas.filter(bloque_academico__ciclo_escolar=ciclo)

        headers = ['Estudiante', 'CUI / DPI', 'Curso', 'Bloque', 'Zona (Pts)', 'Examen (Pts)', 'Nota Total (Pts)', 'Estado']
        rows = []
        for n in notas_reprobadas:
            if n.nota_total < 60:
                rows.append([
                    n.asignacion_estudiante.estudiante.persona.nombre_completo,
                    n.asignacion_estudiante.estudiante.persona.cui,
                    n.curso.nombre_curso,
                    n.bloque_academico.nombre_bloque,
                    f"{n.nota_zona:.1f}",
                    f"{n.nota_examen:.1f}",
                    f"{n.nota_total:.1f}",
                    "REPROBADO (En Riesgo)"
                ])

        return IBACOOPReportCSV.generate_csv_response('Alertas_Tempranas_Reprobacion', headers, rows)



class ReporteAntiguedadSaldosExportView(ReportesFinancierosPermissionMixin, View):
    """Emisión del reporte de morosidad y antigüedad de saldos en PDF o CSV."""

    def get(self, request, *args, **kwargs):
        formato = request.GET.get('formato', 'pdf').lower()
        ciclo_id = request.GET.get('ciclo_id')
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id) if ciclo_id else None

        if formato == 'csv':
            return generar_csv_antiguedad_saldos(ciclo)
        return generar_pdf_antiguedad_saldos(ciclo)


class ReporteCuadreCajaView(ReportesFinancierosPermissionMixin, View):
    """Emisión del reporte de cuadre y recaudación de caja por fecha."""

    def get(self, request, *args, **kwargs):
        fecha_ini_str = request.GET.get('fecha_inicio')
        fecha_fin_str = request.GET.get('fecha_fin')

        hoy = timezone.now().date()
        try:
            fecha_inicio = datetime.strptime(fecha_ini_str, '%Y-%m-%d').date() if fecha_ini_str else hoy
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else hoy
        except ValueError:
            fecha_inicio = hoy
            fecha_fin = hoy

        return generar_csv_cuadre_caja(fecha_inicio, fecha_fin)


class ReporteBecasExportView(ReportesFinancierosPermissionMixin, View):
    """Exportación a CSV de becas y convenios de descuento."""

    def get(self, request, *args, **kwargs):
        becas = BecaDescuento.objects.filter(esta_eliminado=False).select_related(
            'estudiante', 'estudiante__persona', 'concepto'
        )

        headers = ['Estudiante Beneficiario', 'CUI / DPI', 'Código MINEDUC', 'Concepto Aplica', 'Porcentaje Descuento (%)', 'Monto Descuento Fijo (Q)', 'Motivo']
        rows = []
        for b in becas:
            rows.append([
                b.estudiante.persona.nombre_completo,
                b.estudiante.persona.cui,
                b.estudiante.codigo_mineduc,
                b.concepto.nombre if b.concepto else "Todas las cuotas mensuales",
                f"{b.porcentaje_descuento:.2f}%",
                f"Q {b.monto_descuento_fijo:.2f}",
                b.motivo or "Sin motivo especificado"
            ])

        return IBACOOPReportCSV.generate_csv_response('Padron_Becas_Descuentos', headers, rows)



class ReporteConsolidadoPlanillasView(ReportesRRHHPermissionMixin, View):
    """Emisión del consolidado mensual de planilla de sueldos en PDF o CSV."""

    def get(self, request, *args, **kwargs):
        ciclo_id = request.GET.get('ciclo_id')
        mes = request.GET.get('mes')
        formato = request.GET.get('formato', 'pdf').lower()

        if not ciclo_id or not mes:
            messages.error(request, 'Debe especificar el ciclo escolar y el mes para la planilla.')
            return redirect('reportes:hub')

        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)
        mes = int(mes)

        if formato == 'csv':
            return generar_csv_consolidado_planillas(ciclo, mes)
        return generar_pdf_consolidado_planillas(ciclo, mes)



class ReporteInventarioValoradoView(ReportesInventarioPermissionMixin, View):
    """Emisión del inventario físico institucional en PDF o CSV."""

    def get(self, request, *args, **kwargs):
        formato = request.GET.get('formato', 'pdf').lower()
        if formato == 'csv':
            return generar_csv_inventario_valorado()
        return generar_pdf_inventario_valorado()



class IniciarDescargaBoletasZipView(ReportesAcademicosPermissionMixin, View):
    """
    Inicia el procesamiento en segundo plano para generar
    las boletas de calificaciones de una sección completa y empaquetarlas en ZIP.
    """
    def post(self, request, *args, **kwargs):
        seccion_id = request.POST.get('seccion_id')
        ciclo_id = request.POST.get('ciclo_id')

        if not seccion_id or not ciclo_id:
            return JsonResponse({'success': False, 'error': 'Sección y Ciclo son requeridos.'}, status=400)

        task_id = iniciar_generacion_boletas_seccion_zip(int(seccion_id), int(ciclo_id))
        return JsonResponse({
            'success': True,
            'task_id': task_id,
            'mensaje': 'Tarea de generación iniciada en segundo plano.',
        })


class ConsultarEstadoTareaView(ReportesHubPermissionMixin, View):
    """
    Endpoint de sondeo para consultar el progreso en vivo (0% a 100%)
    de una tarea de generación de boletas.
    """
    def get(self, request, task_id, *args, **kwargs):
        info = obtener_estado_tarea(task_id)

        if not info:
            return JsonResponse({
                'task_id': task_id,
                'state': 'PENDING',
                'percent': 0,
                'mensaje': 'Procesando tarea...',
            })

        data = {
            'task_id': task_id,
            **info
        }
        return JsonResponse(data)

