"""
APPS/rrhh/urls.py

Rutas del Módulo de Recursos Humanos:
  - Personal del Instituto (CRUD y expedientes)
  - Planillas de Sueldos (Cálculo masivo y Boletas de Pago PDF)
"""
from django.urls import path
from APPS.rrhh.views import (
    PersonalListView,
    PersonalCreateView,
    PersonalDetailView,
    PersonalUpdateView,
    PersonalBajaView,
    PersonalReactivarView,
    descargar_expediente_pdf,
    descargar_credenciales_pdf,
    PlanillaListView,
    PlanillaGenerarMasivaView,
    PlanillaUpdateView,
    PlanillaDetailView,
    descargar_comprobante_planilla_pdf
)

app_name = 'rrhh'

urlpatterns = [
    path('', PersonalListView.as_view(), name='personal_list'),
    path('nuevo/', PersonalCreateView.as_view(), name='personal_create'),

    path('planillas/', PlanillaListView.as_view(), name='planilla_list'),
    path('planillas/nomina/', PlanillaListView.as_view(), name='planilla_nomina_legacy'),
    path('planillas/generar/', PlanillaGenerarMasivaView.as_view(), name='planilla_generar'),
    path('planillas/<int:pk>/detalle/', PlanillaDetailView.as_view(), name='planilla_detail'),
    path('planillas/<int:pk>/ajustar/', PlanillaUpdateView.as_view(), name='planilla_update'),
    path('planillas/<int:pk>/pdf/boleta/', descargar_comprobante_planilla_pdf, name='planilla_pdf'),

    path('<int:pk>/', PersonalDetailView.as_view(), name='personal_detail'),
    path('<int:pk>/editar/', PersonalUpdateView.as_view(), name='personal_update'),
    path('<int:pk>/baja/', PersonalBajaView.as_view(), name='personal_baja'),
    path('<int:pk>/reactivar/', PersonalReactivarView.as_view(), name='personal_reactivar'),
    path('<int:pk>/pdf/expediente/', descargar_expediente_pdf, name='personal_pdf_expediente'),
    path('<int:pk>/pdf/credenciales/', descargar_credenciales_pdf, name='personal_pdf_credenciales'),
]
