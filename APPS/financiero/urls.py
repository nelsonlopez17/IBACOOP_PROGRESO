"""
APPS/financiero/urls.py

Configuración de URLs del Módulo Financiero / Cuentas por Cobrar.
"""
from django.urls import path
from APPS.financiero import views

app_name = 'financiero'

urlpatterns = [
    path('conceptos/', views.ConceptoPagoListView.as_view(), name='concepto_list'),
    path('conceptos/nuevo/', views.ConceptoPagoCreateView.as_view(), name='concepto_create'),
    path('conceptos/<int:pk>/editar/', views.ConceptoPagoUpdateView.as_view(), name='concepto_update'),

    path('cuentas/', views.CuentaPorCobrarListView.as_view(), name='cuentaporcobrar_list'),
    path('cuentas/nuevo/', views.CuentaPorCobrarCreateView.as_view(), name='cuentaporcobrar_create'),
    path('cuentas/cobro-masivo/', views.GenerarCobroMasivoView.as_view(), name='generar_cobro_masivo'),

    path('estudiante/<pk>/cuenta-corriente/', views.EstudianteCuentaCorrienteDetailView.as_view(), name='estudiante_cuenta_corriente'),

    path('abono/nuevo/<cuentaporcobrar_pk>/', views.AbonoCreateView.as_view(), name='abono_create'),
    path('abonos/', views.AbonoListView.as_view(), name='abono_list'),

    path('abono/<int:pk>/recibo/pdf/', views.descargar_recibo_pdf, name='recibo_pdf'),
    path('estudiante/<pk>/solvencia/pdf/', views.descargar_solvencia_pdf, name='solvencia_pdf'),

    path('becas/', views.BecaDescuentoListView.as_view(), name='beca_list'),
    path('becas/nueva/', views.BecaDescuentoCreateView.as_view(), name='beca_create'),
    path('calendario-anual/', views.GenerarCalendarioAnualView.as_view(), name='calendario_anual'),
    path('antiguedad-saldos/', views.AntiguedadSaldosView.as_view(), name='antiguedad_saldos'),

    # planillas de sueldos (desacopladas en gestion financiera)
    path('planillas/', views.PlanillaListView.as_view(), name='planilla_list'),
    path('planillas/generar/', views.PlanillaGenerarMasivaView.as_view(), name='planilla_generar'),
    path('planillas/liquidar-masivo/', views.PlanillaLiquidarMasivoView.as_view(), name='planilla_liquidar_masivo'),
    path('planillas/<int:pk>/detalle/', views.PlanillaDetailView.as_view(), name='planilla_detail'),
    path('planillas/<int:pk>/ajustar/', views.PlanillaUpdateView.as_view(), name='planilla_update'),
    path('planillas/<int:pk>/pdf/boleta/', views.descargar_comprobante_planilla_pdf, name='planilla_pdf'),
]
