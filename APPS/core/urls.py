"""
APPS/core/urls.py

Rutas principales del módulo Core (Dashboard ERP).
"""
from django.urls import path
from APPS.core.views import HomeView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('inicio/', HomeView.as_view(), name='dashboard'),
]
