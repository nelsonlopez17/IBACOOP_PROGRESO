"""
reportes/views.py

Vistas y controladores del Centro de Reportes y Business Intelligence (BI).
Gestiona el Hub Centralizado de Reportes, APIs de filtrado paramétrico interactivo
y la emisión de documentos oficiales en PDF y Excel (CSV).
"""
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import HttpResponse, Http404, JsonResponse
from django.utils import timezone
from django.db.models import Q, F

from APPS.reportes.tareas import (
    iniciar_generacion_boletas_seccion_zip,
    obtener_estado_tarea,
)

from APPS.academico.models import CicloEscolar, Grado, Seccion, BloqueAcademico, AsignacionEstudiante
from APPS.estudiantes.models import Estudiante
from APPS.financiero.models import BecaDescuento
from APPS.rrhh.models import Planilla
from APPS.reportes.generadores.base_csv import IBACOOPReportCSV

from APPS.reportes.reportes_academicos import (
    generar_pdf_boleta_calificaciones,
    generar_pdf_cuadro_calificaciones,
    generar_csv_cuadro_calificaciones,
    generar_pdf_cuadro_honor,
    generar_csv_cuadro_honor,
    generar_pdf_listado_estudiantes,
    generar_csv_listado_estudiantes,
    generar_pdf_constancia_inscripcion,
    generar_csv_sabana_notas,
)
from APPS.reportes.reportes_financieros import (
    generar_pdf_antiguedad_saldos,
    generar_csv_antiguedad_saldos,
    generar_pdf_cuadre_caja,
    generar_csv_cuadre_caja,
    generar_pdf_estado_cuenta_estudiante,
)
from APPS.reportes.reportes_rrhh import (
    generar_pdf_consolidado_planillas,
    generar_csv_consolidado_planillas,
    generar_pdf_boleta_pago_individual,
    generar_pdf_directorio_personal,
    generar_csv_directorio_personal,
)
from APPS.reportes.reportes_disciplina import (
    generar_pdf_reporte_disciplina,
    generar_csv_reporte_disciplina,
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
        from APPS.auditoria.models import registrar_evento_seguridad, TipoEventoSeguridad
        registrar_evento_seguridad(
            tipo=TipoEventoSeguridad.ACCESO_DENEGADO,
            request=self.request,
            usuario=self.request.user,
            descripcion=f"Acceso denegado a módulo de reportes: {self.request.path}"
        )
        messages.error(self.request, self.error_message)
        return redirect('core:home')


class ReportesHubPermissionMixin(ReportesBasePermissionMixin):
    """Acceso al Hub central de reportes (Administrador, Dirección, Secretaría y Contabilidad, o grupos autorizados)."""

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(
            user.is_superuser
            or getattr(user, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA', 'CONTADOR']
            or user.groups.filter(name__in=['Administradores', 'Directores', 'Secretaría', 'Contabilidad']).exists()
        )


class ReportesAcademicosPermissionMixin(ReportesBasePermissionMixin):
    """Restringe reportes académicos exclusivamente a Dirección, Secretaría y Administración."""
    error_message = 'Acceso denegado: Los reportes académicos están reservados a Dirección y Secretaría.'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(
            user.is_superuser
            or getattr(user, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA', 'DOCENTE']
            or user.groups.filter(name__in=['Administradores', 'Directores', 'Secretaría', 'Docentes']).exists()
            or user.has_perm('academico.view_notabloque')
            or user.has_perm('academico.view_asignacionestudiante')
        )


class ReportesFinancierosPermissionMixin(ReportesBasePermissionMixin):
    """Restringe reportes de cobranza, saldos y caja a Dirección, Contabilidad y Administración."""
    error_message = 'Acceso denegado: Los reportes financieros están reservados a Dirección y Contabilidad.'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(
            user.is_superuser
            or getattr(user, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'CONTADOR']
            or user.groups.filter(name__in=['Administradores', 'Directores', 'Contabilidad']).exists()
            or user.has_perm('financiero.view_cuentaporcobrar')
            or user.has_perm('financiero.view_abono')
        )


class ReportesRRHHPermissionMixin(ReportesBasePermissionMixin):
    """Restringe planillas de sueldos y salarios a Contabilidad y Dirección."""
    error_message = 'Acceso denegado: La planilla de salarios docentes está reservada a Dirección y Contabilidad.'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(
            user.is_superuser
            or getattr(user, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'CONTADOR']
            or user.groups.filter(name__in=['Administradores', 'Directores', 'Contabilidad']).exists()
            or user.has_perm('rrhh.view_planilla')
            or user.has_perm('rrhh.view_personal')
        )


class ReportesInventarioPermissionMixin(ReportesBasePermissionMixin):
    """Acceso a reportes de inventario y bienes institucionales."""
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(
            user.is_superuser
            or getattr(user, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA', 'CONTADOR', 'PERSONAL']
            or user.groups.filter(name__in=['Administradores', 'Directores', 'Secretaría', 'Contabilidad', 'Personal Operativo']).exists()
            or user.has_perm('inventario.view_articuloinventario')
        )


class ReportesDisciplinaPermissionMixin(ReportesBasePermissionMixin):
    """Acceso a reportes de disciplina y convivencia escolar."""
    error_message = 'Acceso denegado: Los reportes de disciplina están reservados a Dirección y Docentes Guías.'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(
            user.is_superuser
            or getattr(user, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA', 'DOCENTE']
            or user.groups.filter(name__in=['Administradores', 'Directores', 'Secretaría', 'Docentes']).exists()
            or user.has_perm('disciplina.view_incidentedisciplinario')
        )


# ==============================================================================
# HUB CENTRAL DE REPORTES
# ==============================================================================

class ReportesHubView(ReportesHubPermissionMixin, TemplateView):
    """
    Hub Central de Reportes y Business Intelligence:
    Catálogo interactivo con filtrado por módulo, búsqueda en tiempo real
    y emisión paramétrica contextual.
    """
    template_name = 'reportes/panel.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        ciclos = CicloEscolar.objects.filter(esta_eliminado=False).order_by('-anio')
        grados = Grado.objects.filter(esta_eliminado=False).order_by('orden')
        secciones = Seccion.objects.filter(esta_eliminado=False).select_related('grado').order_by('grado__orden', 'letra')

        # Cargar planillas recientes para el selector de boletas
        planillas_recientes = Planilla.objects.filter(
            esta_eliminado=False
        ).select_related('personal__persona', 'ciclo_escolar').order_by('-ciclo_escolar__anio', '-mes_pagado')[:40]

        context.update({
            'ciclo_activo': ciclo_activo,
            'ciclos': ciclos,
            'grados': grados,
            'secciones': secciones,
            'planillas_recientes': planillas_recientes,
            'hoy': timezone.now().date(),
            'titulo_pagina': 'Centro de Reportes y Analítica',
        })
        return context


# ==============================================================================
# REPORTES ACADÉMICOS
# ==============================================================================

class DescargarBoletaCalificacionesPDFView(ReportesAcademicosPermissionMixin, View):
    """Descarga de la Boleta Oficial de Calificaciones por Estudiante."""

    def get(self, request, estudiante_id, ciclo_id, *args, **kwargs):
        estudiante = get_object_or_404(Estudiante, pk=estudiante_id)
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)
        return generar_pdf_boleta_calificaciones(estudiante, ciclo)


class ReporteCuadroCalificacionesView(ReportesAcademicosPermissionMixin, View):
    """
    Emisión del Cuadro General de Calificaciones por Sección (PDF y CSV/Excel).
    Corresponde a la sección 'Cuadro de Calificaciones' del módulo de Gestión Académica.
    """

    def get(self, request, *args, **kwargs):
        seccion_id = request.GET.get('seccion_id')
        ciclo_id = request.GET.get('ciclo_id')
        formato = request.GET.get('formato', 'pdf').lower()

        if not seccion_id or not ciclo_id:
            messages.error(request, 'Debe seleccionar una sección y un ciclo escolar.')
            return redirect('reportes:hub')

        seccion = get_object_or_404(Seccion, pk=seccion_id)
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)

        if formato == 'csv' or formato == 'excel':
            return generar_csv_cuadro_calificaciones(seccion, ciclo)
        return generar_pdf_cuadro_calificaciones(seccion, ciclo)


# Alias para retrocompatibilidad con rutas y enlaces previos
ReporteSabanaNotasView = ReporteCuadroCalificacionesView


class ReporteCuadroHonorView(ReportesAcademicosPermissionMixin, View):
    """Emisión del Cuadro de Honor / Ranking de la Sección en PDF y CSV."""

    def get(self, request, *args, **kwargs):
        seccion_id = request.GET.get('seccion_id')
        ciclo_id = request.GET.get('ciclo_id')
        formato = request.GET.get('formato', 'pdf').lower()

        if not seccion_id or not ciclo_id:
            messages.error(request, 'Debe seleccionar una sección y un ciclo escolar.')
            return redirect('reportes:hub')

        seccion = get_object_or_404(Seccion, pk=seccion_id)
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)

        if formato == 'csv' or formato == 'excel':
            return generar_csv_cuadro_honor(seccion, ciclo)
        return generar_pdf_cuadro_honor(seccion, ciclo)


class ReporteListadoEstudiantesView(ReportesAcademicosPermissionMixin, View):
    """Emisión del Listado Oficial de Estudiantes Inscritos por Sección en PDF o CSV."""

    def get(self, request, *args, **kwargs):
        seccion_id = request.GET.get('seccion_id')
        ciclo_id = request.GET.get('ciclo_id')
        formato = request.GET.get('formato', 'pdf').lower()

        if not seccion_id or not ciclo_id:
            messages.error(request, 'Debe seleccionar una sección y un ciclo escolar.')
            return redirect('reportes:hub')

        seccion = get_object_or_404(Seccion, pk=seccion_id)
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)

        if formato == 'csv' or formato == 'excel':
            return generar_csv_listado_estudiantes(seccion, ciclo)
        return generar_pdf_listado_estudiantes(seccion, ciclo)


class ReporteConstanciaInscripcionView(ReportesAcademicosPermissionMixin, View):
    """Emisión de la Constancia Oficial de Inscripción Escolar en PDF."""

    def get(self, request, *args, **kwargs):
        estudiante_id = request.GET.get('estudiante_id') or kwargs.get('estudiante_id')
        ciclo_id = request.GET.get('ciclo_id') or kwargs.get('ciclo_id')

        if not estudiante_id or not ciclo_id:
            messages.error(request, 'Debe seleccionar un estudiante y un ciclo escolar.')
            return redirect('reportes:hub')

        estudiante = get_object_or_404(Estudiante, pk=estudiante_id)
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)
        return generar_pdf_constancia_inscripcion(estudiante, ciclo)


class ReporteAlertasTempranasExportView(ReportesAcademicosPermissionMixin, View):
    """Exportación a CSV de Alertas Tempranas (estudiantes reprobados con nota < 60 pts)."""

    def get(self, request, *args, **kwargs):
        ciclo_id = request.GET.get('ciclo_id')
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id) if ciclo_id else CicloEscolar.objects.filter(estado_activo=True).first()

        from APPS.academico.models import NotaBloque
        # Filtrado optimizado directo en base de datos calculando la suma de zona y examen
        notas_reprobadas = NotaBloque.objects.filter(
            curso__grado__esta_eliminado=False,
            esta_eliminado=False
        ).annotate(
            nota_total_calc=F('nota_zona') + F('nota_examen')
        ).filter(
            nota_total_calc__lt=60
        ).select_related('asignacion_estudiante__estudiante__persona', 'curso', 'bloque_academico')

        if ciclo:
            notas_reprobadas = notas_reprobadas.filter(bloque_academico__ciclo_escolar=ciclo)

        headers = ['Estudiante', 'CUI / DPI', 'Curso', 'Bloque', 'Zona (Pts)', 'Examen (Pts)', 'Nota Total (Pts)', 'Estado']
        rows = []
        for n in notas_reprobadas:
            rows.append([
                n.asignacion_estudiante.estudiante.persona.nombre_completo,
                n.asignacion_estudiante.estudiante.persona.cui or 'N/A',
                n.curso.nombre_curso,
                n.bloque_academico.nombre_bloque,
                f"{n.nota_zona:.1f}",
                f"{n.nota_examen:.1f}",
                f"{n.nota_total:.1f}",
                "REPROBADO (En Riesgo)"
            ])

        return IBACOOPReportCSV.generate_csv_response('Alertas_Tempranas_Reprobacion', headers, rows)


# ==============================================================================
# REPORTES FINANCIEROS Y TESORERÍA
# ==============================================================================

class ReporteAntiguedadSaldosExportView(ReportesFinancierosPermissionMixin, View):
    """Emisión del reporte de morosidad y antigüedad de saldos en PDF o CSV."""

    def get(self, request, *args, **kwargs):
        formato = request.GET.get('formato', 'pdf').lower()
        ciclo_id = request.GET.get('ciclo_id')
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id) if ciclo_id else None

        if formato == 'csv' or formato == 'excel':
            return generar_csv_antiguedad_saldos(ciclo)
        return generar_pdf_antiguedad_saldos(ciclo)


class ReporteCuadreCajaView(ReportesFinancierosPermissionMixin, View):
    """Emisión del reporte de cuadre y recaudación de caja por fecha en PDF o CSV."""

    def get(self, request, *args, **kwargs):
        fecha_ini_str = request.GET.get('fecha_inicio')
        fecha_fin_str = request.GET.get('fecha_fin')
        formato = request.GET.get('formato', 'pdf').lower()

        hoy = timezone.now().date()
        try:
            fecha_inicio = datetime.strptime(fecha_ini_str, '%Y-%m-%d').date() if fecha_ini_str else hoy
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else hoy
        except ValueError:
            fecha_inicio = hoy
            fecha_fin = hoy

        if formato == 'csv' or formato == 'excel':
            return generar_csv_cuadre_caja(fecha_inicio, fecha_fin)
        return generar_pdf_cuadre_caja(fecha_inicio, fecha_fin)


class ReporteEstadoCuentaEstudianteView(ReportesFinancierosPermissionMixin, View):
    """Emisión del Estado de Cuenta y Registro de Pagos por Estudiante en PDF."""

    def get(self, request, *args, **kwargs):
        estudiante_id = request.GET.get('estudiante_id') or kwargs.get('estudiante_id')
        ciclo_id = request.GET.get('ciclo_id') or kwargs.get('ciclo_id')

        if not estudiante_id or not ciclo_id:
            messages.error(request, 'Debe especificar el estudiante y el ciclo escolar.')
            return redirect('reportes:hub')

        estudiante = get_object_or_404(Estudiante, pk=estudiante_id)
        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id)
        return generar_pdf_estado_cuenta_estudiante(estudiante, ciclo)


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
                b.estudiante.persona.cui or 'N/A',
                b.estudiante.codigo_mineduc or 'PENDIENTE',
                b.concepto.nombre if b.concepto else "Todas las cuotas mensuales",
                f"{b.porcentaje_descuento:.2f}%",
                f"Q {b.monto_descuento_fijo:.2f}",
                b.motivo or "Sin motivo especificado"
            ])

        return IBACOOPReportCSV.generate_csv_response('Padron_Becas_Descuentos', headers, rows)


# ==============================================================================
# REPORTES DE RECURSOS HUMANOS Y PLANILLA DE SUELDOS
# ==============================================================================

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

        if formato == 'csv' or formato == 'excel':
            return generar_csv_consolidado_planillas(ciclo, mes)
        return generar_pdf_consolidado_planillas(ciclo, mes)


class ReporteBoletaPagoEmpleadoView(ReportesRRHHPermissionMixin, View):
    """Emisión de la Boleta Oficial de Pago individual por colaborador en PDF."""

    def get(self, request, planilla_id=None, *args, **kwargs):
        pid = planilla_id or request.GET.get('planilla_id')
        if not pid:
            messages.error(request, 'Debe especificar el identificador de la boleta de pago.')
            return redirect('reportes:hub')
        planilla = get_object_or_404(Planilla, pk=pid)
        return generar_pdf_boleta_pago_individual(planilla)


class ReporteDirectorioPersonalView(ReportesRRHHPermissionMixin, View):
    """Emisión del Directorio y Nómina de Personal en PDF o CSV."""

    def get(self, request, *args, **kwargs):
        formato = request.GET.get('formato', 'pdf').lower()
        if formato == 'csv' or formato == 'excel':
            return generar_csv_directorio_personal()
        return generar_pdf_directorio_personal()


# ==============================================================================
# REPORTES DE DISCIPLINA Y CONVIVENCIA ESCOLAR
# ==============================================================================

class ReporteDisciplinaView(ReportesDisciplinaPermissionMixin, View):
    """Emisión del Historial de Incidentes Disciplinarios y Citaciones en PDF o CSV."""

    def get(self, request, *args, **kwargs):
        ciclo_id = request.GET.get('ciclo_id')
        seccion_id = request.GET.get('seccion_id')
        formato = request.GET.get('formato', 'pdf').lower()

        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id) if ciclo_id else CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        seccion = get_object_or_404(Seccion, pk=seccion_id) if seccion_id else None

        if not ciclo:
            messages.error(request, 'No se encontró un ciclo escolar activo.')
            return redirect('reportes:hub')

        if formato == 'csv' or formato == 'excel':
            return generar_csv_reporte_disciplina(ciclo, seccion)
        return generar_pdf_reporte_disciplina(ciclo, seccion)


# ==============================================================================
# REPORTES DE INVENTARIO Y CONTROL DE BIENES
# ==============================================================================

class ReporteInventarioValoradoView(ReportesInventarioPermissionMixin, View):
    """Emisión del inventario físico institucional en PDF o CSV."""

    def get(self, request, *args, **kwargs):
        formato = request.GET.get('formato', 'pdf').lower()
        if formato == 'csv' or formato == 'excel':
            return generar_csv_inventario_valorado()
        return generar_pdf_inventario_valorado()


# ==============================================================================
# PROCESAMIENTO ASÍNCRONO EN SEGUNDO PLANO (CELERY)
# ==============================================================================

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


# ==============================================================================
# APIS PARA SELECTORES DEPENDIENTES EN LA INTERFAZ
# ==============================================================================

class APISeccionesPorGradoView(ReportesHubPermissionMixin, View):
    """Retorna las secciones asociadas a un grado en formato JSON."""

    def get(self, request, grado_id, *args, **kwargs):
        secciones = Seccion.objects.filter(grado_id=grado_id, esta_eliminado=False).order_by('letra')
        data = [{'id': s.id, 'letra': s.letra, 'nombre': f"Sección '{s.letra}'"} for s in secciones]
        return JsonResponse({'secciones': data})


class APIEstudiantesPorSeccionView(ReportesHubPermissionMixin, View):
    """Retorna los estudiantes asignados a una sección y ciclo en formato JSON."""

    def get(self, request, seccion_id, ciclo_id, *args, **kwargs):
        asigs = AsignacionEstudiante.objects.filter(
            seccion_id=seccion_id,
            ciclo_escolar_id=ciclo_id,
            esta_eliminado=False
        ).select_related('estudiante__persona').order_by('estudiante__persona__apellidos', 'estudiante__persona__nombres')

        data = [
            {
                'id': a.estudiante.pk,
                'nombre_completo': a.estudiante.persona.nombre_completo,
                'cui': a.estudiante.persona.cui or 'N/A',
                'codigo_mineduc': a.estudiante.codigo_mineduc or 'PENDIENTE'
            }
            for a in asigs
        ]
        return JsonResponse({'estudiantes': data})
