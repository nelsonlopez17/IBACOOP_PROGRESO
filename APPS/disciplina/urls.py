"""
APPS/disciplina/urls.py

Rutas URL para el Módulo de Disciplina y Convivencia Escolar.
"""
from django.urls import path
from APPS.disciplina import views

app_name = 'disciplina'

urlpatterns = [
    path('', views.DisciplinaDashboardView.as_view(), name='panel'),
    path('panel/', views.DisciplinaDashboardView.as_view(), name='dashboard'),
    path('incidentes/nuevo/', views.IncidenteCreateView.as_view(), name='incidente_crear'),
    path('incidentes/crear/', views.IncidenteCreateView.as_view(), name='incidente_create'),
    path('incidentes/<int:pk>/', views.IncidenteDetailView.as_view(), name='incidente_detalle'),
    path('incidentes/<int:pk>/ver/', views.IncidenteDetailView.as_view(), name='incidente_detail'),
    path('incidentes/<int:pk>/editar/', views.IncidenteUpdateView.as_view(), name='incidente_editar'),
    path('incidentes/<int:pk>/modificar/', views.IncidenteUpdateView.as_view(), name='incidente_update'),
    path('incidentes/<int:incidente_id>/citacion/nueva/', views.CitacionCreateView.as_view(), name='citacion_crear'),
    path('incidentes/<int:incidente_id>/citacion/crear/', views.CitacionCreateView.as_view(), name='citacion_create'),
    path('citaciones/<int:pk>/editar/', views.CitacionUpdateView.as_view(), name='citacion_editar'),
    path('citaciones/<int:pk>/modificar/', views.CitacionUpdateView.as_view(), name='citacion_update'),
    path('citaciones/<int:pk>/pdf/', views.DescargarCitacionPDFView.as_view(), name='citacion_pdf'),
    path('citaciones/<int:pk>/acta-pdf/', views.DescargarActaCompromisoPDFView.as_view(), name='acta_pdf'),
]
