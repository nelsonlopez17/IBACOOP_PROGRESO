"""
auditoria/urls.py

Rutas del módulo de Auditoría y Trazabilidad Empresarial.
"""
from django.urls import path
from APPS.auditoria import views

app_name = 'auditoria'

urlpatterns = [
    path('', views.AuditoriaDashboardView.as_view(), name='panel'),
    path('panel/', views.AuditoriaDashboardView.as_view(), name='dashboard'),
    path('detalle/<str:modelo>/<int:history_id>/', views.AuditoriaDetalleDiffView.as_view(), name='detalle_diferencia'),
    path('diff/<str:modelo>/<int:history_id>/', views.AuditoriaDetalleDiffView.as_view(), name='diff_detail'),
    path('seguridad/', views.AuditoriaSeguridadView.as_view(), name='seguridad'),
    path('exportar/csv/', views.ExportarAuditoriaCSVView.as_view(), name='exportar_csv'),
]

