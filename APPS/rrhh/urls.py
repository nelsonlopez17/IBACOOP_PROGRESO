from django.urls import path
from APPS.rrhh.views import (
    PersonalListView,
    PersonalCreateView,
    PersonalDetailView,
    PersonalUpdateView,
    descargar_expediente_pdf,
    descargar_credenciales_pdf
)

app_name = 'rrhh'

urlpatterns = [
    path('', PersonalListView.as_view(), name='personal_list'),
    path('nuevo/', PersonalCreateView.as_view(), name='personal_create'),
    path('<pk>/', PersonalDetailView.as_view(), name='personal_detail'),
    path('<pk>/editar/', PersonalUpdateView.as_view(), name='personal_update'),
    path('<pk>/pdf/expediente/', descargar_expediente_pdf, name='personal_pdf_expediente'),
    path('<pk>/pdf/credenciales/', descargar_credenciales_pdf, name='personal_pdf_credenciales'),
]

