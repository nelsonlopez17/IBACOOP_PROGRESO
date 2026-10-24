"""
portal/urls.py

Rutas del Portal Web Público Institucional del Instituto "El Progreso".
"""
from django.urls import path
from APPS.portal.views import (
    PortalIndexView,
    NosotrosView,
    OfertaAcademicaView,
    AdmisionesView,
    ContactoView,
)

app_name = 'portal'

urlpatterns = [
    path('', PortalIndexView.as_view(), name='index'),
    path('nosotros/', NosotrosView.as_view(), name='nosotros'),
    path('oferta-academica/', OfertaAcademicaView.as_view(), name='oferta_academica'),
    path('admisiones/', AdmisionesView.as_view(), name='admisiones'),
    path('contacto/', ContactoView.as_view(), name='contacto'),
]
