"""
APPS/academico/urls.py

Configuración de URLs del Módulo Académico del Instituto El Progreso.
"""
from django.urls import path
from APPS.academico import views

app_name = 'academico'

urlpatterns = [
    path('configuracion-pensum/', views.ConfiguracionPensumView.as_view(), name='configuracion_pensum'),
    path('ciclo/<int:pk>/activar/', views.activar_ciclo_escolar, name='activar_ciclo'),
    path('ciclo/nuevo/', views.CicloEscolarCreateView.as_view(), name='ciclo_create'),
    path('grado/nuevo/', views.GradoCreateView.as_view(), name='grado_create'),
    path('seccion/nueva/', views.SeccionCreateView.as_view(), name='seccion_create'),
    path('curso/nuevo/', views.CursoCreateView.as_view(), name='curso_create'),

    path('inscripciones/', views.AsignacionEstudianteListView.as_view(), name='asignacion_estudiante_list'),
    path('inscripciones/nueva/', views.AsignacionEstudianteCreateView.as_view(), name='asignacion_estudiante_create'),

    path('carga-docente/', views.AsignacionDocenteListView.as_view(), name='asignacion_docente_list'),
    path('carga-docente/nueva/', views.AsignacionDocenteCreateView.as_view(), name='asignacion_docente_create'),
    path('carga-docente/<int:pk>/editar/', views.AsignacionDocenteUpdateView.as_view(), name='asignacion_docente_update'),

    path('notas/', views.CuadroCalificacionesView.as_view(), name='notas_lista'),
    path('notas/<int:pk>/editar/', views.IngresoNotasUpdateView.as_view(), name='ingreso_notas'),

    path('cierre-ciclo/', views.CierreCicloEscolarView.as_view(), name='cierre_ciclo_escolar'),
    path('reinscripcion-rapida/', views.ReinscripcionRapidaView.as_view(), name='reinscripcion_rapida'),

    path('asistencia/', views.AsistenciaSeccionView.as_view(), name='asistencia'),
    path('asistencia/historial/', views.AsistenciaHistorialListView.as_view(), name='asistencia_historial'),

    path('boleta/<int:pk>/pdf/', views.descargar_boleta_notas_pdf, name='boleta_pdf'),
    path('certificacion/<pk>/pdf/', views.descargar_certificacion_pdf, name='certificacion_pdf'),

    path('alertas-tempranas/', views.AlertasTempranasView.as_view(), name='alertas_tempranas'),
    path('recuperacion/<int:pk>/editar/', views.IngresoNotaRecuperacionView.as_view(), name='ingreso_recuperacion'),
]
