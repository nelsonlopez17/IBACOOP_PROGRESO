"""
APPS/core/urls.py

Rutas principales del módulo Core (Dashboard).
"""
from django.urls import path
from APPS.core.views import HomeView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', HomeView.as_view(), name='dashboard'),
]
