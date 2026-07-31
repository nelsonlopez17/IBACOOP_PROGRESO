"""
APPS/core/views.py

Vistas principales del sistema ERP Escolar — Instituto "El Progreso".
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from APPS.usuarios.models import Usuario


class HomeView(LoginRequiredMixin, TemplateView):
    """
    Vista principal (Dashboard) del sistema.

    Requisitos de seguridad:
        - Protegida obligatoriamente con `LoginRequiredMixin`.
        - Si el usuario no está autenticado, es redirigido automáticamente a LOGIN_URL.

    Contexto:
        - Muestra un resumen general con indicadores (KPIs) y accesos directos
          a la Gestión de Usuarios y otros módulos del sistema.
    """
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Métricas y estadísticas para el Dashboard
        total_usuarios = Usuario.objects.count()
        usuarios_activos = Usuario.objects.filter(is_active=True).count()
        
        # Conteo por rol para resumen en tarjetas del Dashboard
        admin_count = Usuario.objects.filter(rol='ADMINISTRADOR', is_active=True).count()
        director_count = Usuario.objects.filter(rol='DIRECTOR', is_active=True).count()
        secretaria_count = Usuario.objects.filter(rol='SECRETARIA', is_active=True).count()
        contador_count = Usuario.objects.filter(rol='CONTADOR', is_active=True).count()
        docente_count = Usuario.objects.filter(rol='DOCENTE', is_active=True).count()
        estudiante_count = Usuario.objects.filter(rol='ESTUDIANTE', is_active=True).count()
        encargado_count = Usuario.objects.filter(rol='ENCARGADO', is_active=True).count()

        context.update({
            'total_usuarios': total_usuarios,
            'usuarios_activos': usuarios_activos,
            'admin_count': admin_count,
            'director_count': director_count,
            'secretaria_count': secretaria_count,
            'contador_count': contador_count,
            'docente_count': docente_count,
            'estudiante_count': estudiante_count,
            'encargado_count': encargado_count,
            'titulo_pagina': 'Dashboard Principal',
        })
        return context
