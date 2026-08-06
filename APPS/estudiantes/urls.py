from django.urls import path
from APPS.estudiantes.views import (
    EstudianteListView,
    EstudianteCreateView,
    EstudianteDetailView,
    EstudianteUpdateView,
    EncargadoCreateView,
    buscar_encargado_api,
    descargar_expediente_pdf,
    descargar_credenciales_pdf,
    descargar_credenciales_encargado_pdf
)

app_name = 'estudiantes'

urlpatterns = [
    path('', EstudianteListView.as_view(), name='estudiante_list'),
    path('crear/', EstudianteCreateView.as_view(), name='estudiante_create'),
    path('buscar-encargado/', buscar_encargado_api, name='buscar_encargado_api'),
    path('<pk>/', EstudianteDetailView.as_view(), name='estudiante_detail'),
    path('<pk>/editar/', EstudianteUpdateView.as_view(), name='estudiante_update'),
    path('<pk>/pdf/expediente/', descargar_expediente_pdf, name='estudiante_pdf_expediente'),
    path('<pk>/pdf/credenciales/', descargar_credenciales_pdf, name='estudiante_pdf_credenciales'),
    path('encargado/crear/', EncargadoCreateView.as_view(), name='encargado_create'),
    path('encargado/<pk>/pdf/credenciales/', descargar_credenciales_encargado_pdf, name='encargado_pdf_credenciales'),
]
