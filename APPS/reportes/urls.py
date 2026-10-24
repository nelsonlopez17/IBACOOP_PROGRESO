"""
reportes/urls.py

Rutas del Centro de Reportes y Business Intelligence (BI).
"""
from django.urls import path
from APPS.reportes import views

app_name = 'reportes'

urlpatterns = [
    path('', views.ReportesHubView.as_view(), name='panel'),
    path('panel/', views.ReportesHubView.as_view(), name='hub'),
    path('academico/boleta/<int:estudiante_id>/<int:ciclo_id>/', views.DescargarBoletaCalificacionesPDFView.as_view(), name='academico_boleta_pdf'),
    path('academico/cuadro-honor/', views.ReporteCuadroHonorView.as_view(), name='academico_cuadro_honor'),
    path('academico/sabana/', views.ReporteSabanaNotasView.as_view(), name='academico_sabana'),
    path('academico/alertas/', views.ReporteAlertasTempranasExportView.as_view(), name='academico_alertas'),
    path('financiero/antiguedad-saldos/', views.ReporteAntiguedadSaldosExportView.as_view(), name='financiero_antiguedad'),
    path('financiero/cuadre-caja/', views.ReporteCuadreCajaView.as_view(), name='financiero_cuadre_caja'),
    path('financiero/becas/', views.ReporteBecasExportView.as_view(), name='financiero_becas'),
    path('rrhh/consolidado-planillas/', views.ReporteConsolidadoPlanillasView.as_view(), name='rrhh_consolidado_planillas'),
    path('inventario/fisico-valorado/', views.ReporteInventarioValoradoView.as_view(), name='inventario_valorado'),
    path('asincrono/boletas-zip/iniciar/', views.IniciarDescargaBoletasZipView.as_view(), name='boletas_zip_iniciar'),
    path('asincrono/tarea/<str:task_id>/estado/', views.ConsultarEstadoTareaView.as_view(), name='tarea_estado'),
]
