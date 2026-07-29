from django.urls import path
from APPS.academico import views

app_name = 'academico'

urlpatterns = [
    # Docente — lista de notas
    path(
        'notas/',
        views.DocenteNotasListView.as_view(),
        name='notas_lista',
    ),
    # Docente — ingreso/actualización de una nota específica
    path(
        'notas/<int:pk>/editar/',
        views.IngresoNotasUpdateView.as_view(),
        name='ingreso_notas',
    ),
]
