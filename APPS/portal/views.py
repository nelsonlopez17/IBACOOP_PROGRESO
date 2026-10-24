"""
portal/views.py

Vistas públicas del Portal Web Institucional — Instituto "El Progreso" (IBACOOP).
Implementa la separación entre el portal para visitantes y el sistema ERP interno,
con redirección inteligente para usuarios autenticados.
"""
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView
from django.contrib import messages
from APPS.portal.models import ContenidoWeb, SolicitudContacto
from APPS.portal.forms import SolicitudContactoForm


class PortalIndexView(TemplateView):
    """
    Página de inicio (Landing Page) del portal institucional.
    
    Regla de Redirección Inteligente:
    - Si el visitante es un usuario autenticado (Director, Secretaria, Docente, etc.),
      es redirigido de inmediato al Dashboard ERP ('core:home' -> /dashboard/).
    - Si es un visitante anónimo (padre de familia, prospecto), se le presenta el portal público.
    """
    template_name = 'portal/index.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['noticias_recientes'] = ContenidoWeb.objects.filter(
            publicado=True,
            seccion__in=['NOTICIAS', 'COMUNICADOS', 'EVENTOS']
        ).order_by('-fecha_publicacion')[:3]
        context['form'] = SolicitudContactoForm()
        context['titulo_pagina'] = 'Inicio'
        return context


class NosotrosView(TemplateView):
    """Información institucional: Historia, Misión, Visión, Valores y Cooperativismo."""
    template_name = 'portal/nosotros.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Sobre Nosotros'
        context['articulos_historia'] = ContenidoWeb.objects.filter(
            publicado=True,
            seccion='HISTORIA'
        ).order_by('-fecha_publicacion')
        return context


class OfertaAcademicaView(TemplateView):
    """Oferta educativa para el Nivel Medio - Ciclo de Educación Básica (1ro, 2do y 3ro)."""
    template_name = 'portal/oferta_academica.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Oferta Académica'
        return context


class AdmisionesView(TemplateView):
    """Requisitos de inscripción, papelería oficial MINEDUC y calendario escolar."""
    template_name = 'portal/admisiones.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Admisiones e Inscripciones'
        return context


class ContactoView(CreateView):
    """
    Formulario de contacto para padres de familia y prospectos.
    Permite enviar solicitudes de información que se registran en la base de datos.
    """
    model = SolicitudContacto
    form_class = SolicitudContactoForm
    template_name = 'portal/contacto.html'
    success_url = reverse_lazy('portal:contacto')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Contacto y Ubicación'
        return context

    def form_valid(self, form):
        messages.success(
            self.request,
            '¡Gracias por contactarnos! Su mensaje ha sido enviado exitosamente. '
            'Nuestro equipo de secretaría se comunicará a la brevedad posible.'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)
