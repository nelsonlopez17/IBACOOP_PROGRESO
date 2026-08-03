from django.urls import path
from APPS.estudiantes.views import EstudianteListView, EstudianteCreateView, EncargadoCreateView

app_name = 'estudiantes'

urlpatterns = [
    path('', EstudianteListView.as_view(), name='estudiante_list'),
    path('crear/', EstudianteCreateView.as_view(), name='estudiante_create'),
    path('encargado/crear/', EncargadoCreateView.as_view(), name='encargado_create'),
]
