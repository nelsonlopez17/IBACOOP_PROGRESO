"""
reportes/urls.py

Rutas del Centro de Reportes y Business Intelligence (BI) de IBACOOP.
"""
from django.urls import path
from APPS.reportes import views

app_name = 'reportes'

urlpatterns = [
    # hub central de reportes
    path('', views.ReportesHubView.as_view(), name='panel'),
    path('panel/', views.ReportesHubView.as_view(), name='hub'),

    # reportes academicos y evaluacion
    path('academico/boleta/<int:estudiante_id>/<int:ciclo_id>/', views.DescargarBoletaCalificacionesPDFView.as_view(), name='academico_boleta_pdf'),
    path('academico/cuadro-calificaciones/', views.ReporteCuadroCalificacionesView.as_view(), name='academico_cuadro_calificaciones'),
    path('academico/sabana/', views.ReporteSabanaNotasView.as_view(), name='academico_sabana'),
    path('academico/cuadro-honor/', views.ReporteCuadroHonorView.as_view(), name='academico_cuadro_honor'),
    path('academico/listado-estudiantes/', views.ReporteListadoEstudiantesView.as_view(), name='academico_listado_estudiantes'),
    path('academico/constancia-inscripcion/', views.ReporteConstanciaInscripcionView.as_view(), name='academico_constancia_inscripcion'),
    path('academico/constancia-inscripcion/<int:estudiante_id>/<int:ciclo_id>/', views.ReporteConstanciaInscripcionView.as_view(), name='academico_constancia_inscripcion_param'),
    path('academico/alertas/', views.ReporteAlertasTempranasExportView.as_view(), name='academico_alertas'),

    # reportes financieros y tesoreria
    path('financiero/antiguedad-saldos/', views.ReporteAntiguedadSaldosExportView.as_view(), name='financiero_antiguedad'),
    path('financiero/cuadre-caja/', views.ReporteCuadreCajaView.as_view(), name='financiero_cuadre_caja'),
    path('financiero/estado-cuenta/', views.ReporteEstadoCuentaEstudianteView.as_view(), name='financiero_estado_cuenta'),
    path('financiero/estado-cuenta/<int:estudiante_id>/<int:ciclo_id>/', views.ReporteEstadoCuentaEstudianteView.as_view(), name='financiero_estado_cuenta_param'),
    path('financiero/becas/', views.ReporteBecasExportView.as_view(), name='financiero_becas'),

    # reportes de recursos humanos y planilla
    path('rrhh/consolidado-planillas/', views.ReporteConsolidadoPlanillasView.as_view(), name='rrhh_consolidado_planillas'),
    path('rrhh/boleta-pago/', views.ReporteBoletaPagoEmpleadoView.as_view(), name='rrhh_boleta_pago'),
    path('rrhh/boleta-pago/<int:planilla_id>/', views.ReporteBoletaPagoEmpleadoView.as_view(), name='rrhh_boleta_pago_param'),
    path('rrhh/directorio/', views.ReporteDirectorioPersonalView.as_view(), name='rrhh_directorio'),

    # reportes de disciplina y convivencia escolar
    path('disciplina/historial/', views.ReporteDisciplinaView.as_view(), name='disciplina_historial'),

    # reportes de inventario y control de bienes
    path('inventario/fisico-valorado/', views.ReporteInventarioValoradoView.as_view(), name='inventario_valorado'),

    # procesamiento asincrono en segundo plano
    path('asincrono/boletas-zip/iniciar/', views.IniciarDescargaBoletasZipView.as_view(), name='boletas_zip_iniciar'),
    path('asincrono/tarea/<str:task_id>/estado/', views.ConsultarEstadoTareaView.as_view(), name='tarea_estado'),

    # apis para selectores dinamicos del frontend
    path('api/secciones-por-grado/<int:grado_id>/', views.APISeccionesPorGradoView.as_view(), name='api_secciones_por_grado'),
    path('api/estudiantes-por-seccion/<int:seccion_id>/<int:ciclo_id>/', views.APIEstudiantesPorSeccionView.as_view(), name='api_estudiantes_por_seccion'),
]
