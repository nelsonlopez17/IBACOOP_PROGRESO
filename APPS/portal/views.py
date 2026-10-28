"""
portal/views.py

Vistas públicas y de administración del Portal Web Institucional del Instituto "El Progreso".
Permite a los visitantes consultar información oficial y a los roles directivos/secretaría
gestionar la configuración, publicaciones, galería de fotos (enlaces externos) y bandeja de contactos.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, CreateView, UpdateView, ListView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q

from APPS.portal.models import (
    ContenidoWeb,
    SolicitudContacto,
    ConfiguracionPortal,
    FotoGaleria,
    CategoriaFotoChoices,
    SeccionPortalChoices,
)
from APPS.portal.forms import (
    SolicitudContactoForm,
    ConfiguracionPortalForm,
    FotoGaleriaForm,
    ContenidoWebForm,
    AtenderSolicitudContactoForm,
)


# ==============================================================================
# VISTAS PÚBLICAS PARA VISITANTES
# ==============================================================================

class PortalIndexView(TemplateView):
    """
    Página de inicio (Landing Page) del portal institucional.
    Accesible tanto para visitantes anónimos como para usuarios autenticados
    que deseen inspeccionar o previsualizar el sitio web público.
    """
    template_name = 'portal/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = ConfiguracionPortal.get_solo()
        context['config'] = config

        # Publicaciones y comunicados vigentes en el portal
        publicaciones_activas = ContenidoWeb.objects.filter(publicado=True).order_by('-fecha_publicacion')
        context['publicaciones_recientes'] = publicaciones_activas[:6]
        context['noticias_recientes'] = context['publicaciones_recientes']
        context['total_publicaciones_publicadas'] = publicaciones_activas.count()

        # Fotos destacadas para portada
        fotos_destacadas = FotoGaleria.objects.filter(activo=True, destacada_portada=True)[:6]
        if not fotos_destacadas.exists():
            fotos_destacadas = FotoGaleria.objects.filter(activo=True)[:6]
        context['fotos_portada'] = fotos_destacadas

        context['form'] = SolicitudContactoForm()
        context['titulo_pagina'] = 'Inicio'
        return context


class PublicacionesPublicaListView(TemplateView):
    """Listado público de todas las publicaciones, noticias y comunicados institucionales."""
    template_name = 'portal/publicaciones_list_publica.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['config'] = ConfiguracionPortal.get_solo()

        seccion = self.request.GET.get('seccion', '').strip()
        busqueda = self.request.GET.get('q', '').strip()

        qs = ContenidoWeb.objects.filter(publicado=True)
        if seccion:
            qs = qs.filter(seccion=seccion)
        if busqueda:
            qs = qs.filter(Q(titulo__icontains=busqueda) | Q(cuerpo__icontains=busqueda))

        paginator = Paginator(qs.order_by('-fecha_publicacion'), 9)
        page_number = self.request.GET.get('page')
        publicaciones_page = paginator.get_page(page_number)

        context.update({
            'publicaciones': publicaciones_page,
            'page_obj': publicaciones_page,
            'is_paginated': publicaciones_page.has_other_pages(),
            'secciones': SeccionPortalChoices.choices,
            'seccion_actual': seccion,
            'busqueda': busqueda,
            'total_publicaciones': qs.count(),
            'titulo_pagina': 'Publicaciones y Comunicados',
        })
        return context


class PublicacionDetallePublicaView(TemplateView):
    """Vista pública de detalle para una publicación, aviso o comunicado."""
    template_name = 'portal/publicacion_detalle.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        publicacion = get_object_or_404(ContenidoWeb, pk=pk, publicado=True)
        context['publicacion'] = publicacion
        context['config'] = ConfiguracionPortal.get_solo()
        context['titulo_pagina'] = publicacion.titulo
        context['otras_publicaciones'] = ContenidoWeb.objects.filter(
            publicado=True
        ).exclude(pk=publicacion.pk).order_by('-fecha_publicacion')[:3]
        return context


class NosotrosView(TemplateView):
    """Información institucional: Historia, Misión, Visión, Valores y Cooperativismo."""
    template_name = 'portal/nosotros.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['config'] = ConfiguracionPortal.get_solo()
        context['titulo_pagina'] = 'Sobre Nosotros'
        context['articulos_historia'] = ContenidoWeb.objects.filter(
            publicado=True,
            seccion='HISTORIA'
        ).order_by('-fecha_publicacion')
        return context


class OfertaAcademicaView(TemplateView):
    """Oferta educativa para el Ciclo de Educación Básica (1ro, 2do y 3ro Básico)."""
    template_name = 'portal/oferta_academica.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['config'] = ConfiguracionPortal.get_solo()
        context['titulo_pagina'] = 'Oferta Académica'
        return context


class AdmisionesView(TemplateView):
    """Requisitos de inscripción, papelería oficial MINEDUC y calendario escolar."""
    template_name = 'portal/admisiones.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['config'] = ConfiguracionPortal.get_solo()
        context['titulo_pagina'] = 'Admisiones e Inscripciones'
        return context


class GaleriaView(TemplateView):
    """Galería pública de fotografías institucionales agrupadas por categorías."""
    template_name = 'portal/galeria.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categoria_filtro = self.request.GET.get('categoria', '').strip()

        fotos_qs = FotoGaleria.objects.filter(activo=True)
        if categoria_filtro:
            fotos_qs = fotos_qs.filter(categoria=categoria_filtro)

        paginator = Paginator(fotos_qs, 12)
        page_number = self.request.GET.get('page')
        fotos_page = paginator.get_page(page_number)

        context.update({
            'fotos': fotos_page,
            'page_obj': fotos_page,
            'categorias': CategoriaFotoChoices.choices,
            'categoria_activa': categoria_filtro,
            'total_fotos': fotos_qs.count(),
            'titulo_pagina': 'Galería de Actividades',
        })
        return context


def get_client_ip(request):
    """Obtiene la dirección IP del visitante para control de tasa y seguridad anti-spam."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


class ContactoView(CreateView):
    """Formulario de contacto para padres de familia o encargados y solicitantes de información."""
    model = SolicitudContacto
    form_class = SolicitudContactoForm
    template_name = 'portal/contacto.html'
    success_url = reverse_lazy('portal:contacto')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['config'] = ConfiguracionPortal.get_solo()
        context['titulo_pagina'] = 'Contacto y Ubicación'
        return context

    def post(self, request, *args, **kwargs):
        ip = get_client_ip(request)
        cache_key = f"portal_contacto_rate_{ip}"
        intentos = cache.get(cache_key, 0)
        if intentos >= 3:
            self.object = None
            messages.error(
                request,
                'Ha superado el límite de consultas permitidas (máximo 3 cada 10 minutos). '
                'Por favor espere unos momentos antes de enviar otro mensaje.'
            )
            form = self.get_form()
            return self.form_invalid(form)

        response = super().post(request, *args, **kwargs)
        if getattr(self, 'object', None) and self.object.pk:
            cache.set(cache_key, intentos + 1, timeout=600)
        return response

    def form_valid(self, form):
        messages.success(
            self.request,
            'Su mensaje ha sido enviado exitosamente. '
            'El equipo de Secretaría revisará su consulta para brindarle atención a la brevedad posible.'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)


# ==============================================================================
# GESTIÓN INTERNA DEL PORTAL (PARA DIRECCIÓN, ADMINISTRACIÓN Y SECRETARÍA)
# ==============================================================================

class PortalPermissionMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Control de acceso: exclusivo para Administradores, Dirección y Secretaría."""

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(
            user.is_superuser
            or getattr(user, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA']
            or user.groups.filter(name__in=['Administradores', 'Directores', 'Secretaría']).exists()
        )

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'No cuenta con autorización para administrar el Portal Web Institucional.')
        return redirect('core:home')


class PortalGestionDashboardView(PortalPermissionMixin, TemplateView):
    """Centro de control del Portal Web: resumen de publicaciones, fotos y solicitudes."""
    template_name = 'portal/gestion/panel_gestion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = ConfiguracionPortal.get_solo()

        solicitudes_pendientes = SolicitudContacto.objects.filter(atendido=False)
        total_fotos = FotoGaleria.objects.count()
        total_publicaciones = ContenidoWeb.objects.count()

        context.update({
            'config': config,
            'total_solicitudes': SolicitudContacto.objects.count(),
            'solicitudes_pendientes': solicitudes_pendientes.count(),
            'solicitudes_recientes': solicitudes_pendientes.order_by('-creado_en')[:5],
            'total_fotos': total_fotos,
            'total_publicaciones': total_publicaciones,
            'ultimas_publicaciones': ContenidoWeb.objects.all().order_by('-fecha_publicacion')[:5],
            'titulo_pagina': 'Gestión del Portal Web',
        })
        return context


class ConfiguracionPortalUpdateView(PortalPermissionMixin, UpdateView):
    """Permite a la Dirección o Secretaría modificar datos de contacto, cuotas y avisos."""
    model = ConfiguracionPortal
    form_class = ConfiguracionPortalForm
    template_name = 'portal/gestion/configuracion_form.html'
    success_url = reverse_lazy('portal:gestion_dashboard')

    def get_object(self, queryset=None):
        return ConfiguracionPortal.get_solo()

    def form_valid(self, form):
        messages.success(self.request, 'La configuración y datos del portal institucional se actualizaron exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Configuración General del Portal'
        return context


# --- GESTIÓN DE GALERÍA DE FOTOS (VÍA ENLACES EXTERNOS) ---

class FotoGaleriaListView(PortalPermissionMixin, ListView):
    """Lista administrativa de fotografías registradas."""
    model = FotoGaleria
    template_name = 'portal/gestion/galeria_list.html'
    context_object_name = 'fotos'
    paginate_by = 15

    def get_queryset(self):
        qs = FotoGaleria.objects.all()
        cat = self.request.GET.get('categoria', '').strip()
        q = self.request.GET.get('q', '').strip()
        if cat:
            qs = qs.filter(categoria=cat)
        if q:
            qs = qs.filter(Q(titulo__icontains=q) | Q(descripcion__icontains=q))
        return qs.order_by('orden', '-fecha')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaFotoChoices.choices
        context['categoria_actual'] = self.request.GET.get('categoria', '')
        context['busqueda'] = self.request.GET.get('q', '')
        context['titulo_pagina'] = 'Gestión de Fotografías (Galería)'
        return context


class FotoGaleriaCreateView(PortalPermissionMixin, CreateView):
    """Agrega una nueva fotografía a la galería mediante enlace de Google Drive u otro servidor."""
    model = FotoGaleria
    form_class = FotoGaleriaForm
    template_name = 'portal/gestion/galeria_form.html'
    success_url = reverse_lazy('portal:galeria_list')

    def form_valid(self, form):
        foto = form.save(commit=False)
        foto.save()
        messages.success(self.request, f"La fotografía '{foto.titulo}' se registró exitosamente en la galería.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Registrar Fotografía en Galería'
        return context


class FotoGaleriaUpdateView(PortalPermissionMixin, UpdateView):
    """Modifica datos o enlace de una fotografía de la galería."""
    model = FotoGaleria
    form_class = FotoGaleriaForm
    template_name = 'portal/gestion/galeria_form.html'
    success_url = reverse_lazy('portal:galeria_list')

    def form_valid(self, form):
        messages.success(self.request, 'La fotografía se actualizó correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Fotografía: {self.object.titulo}"
        return context


class FotoGaleriaDeleteView(PortalPermissionMixin, DeleteView):
    """Elimina el registro de una fotografía de la galería."""
    model = FotoGaleria
    template_name = 'portal/gestion/galeria_confirm_delete.html'
    success_url = reverse_lazy('portal:galeria_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        titulo = obj.titulo
        messages.success(request, f"Se eliminó la fotografía '{titulo}' de la galería.")
        return super().delete(request, *args, **kwargs)


# --- GESTIÓN DE NOTICIAS Y COMUNICADOS ---

class ContenidoWebListView(PortalPermissionMixin, ListView):
    """Listado administrativo de comunicados y noticias publicadas."""
    model = ContenidoWeb
    template_name = 'portal/gestion/publicaciones_list.html'
    context_object_name = 'publicaciones'
    paginate_by = 15

    def get_queryset(self):
        qs = ContenidoWeb.objects.all()
        sec = self.request.GET.get('seccion', '').strip()
        q = self.request.GET.get('q', '').strip()
        if sec:
            qs = qs.filter(seccion=sec)
        if q:
            qs = qs.filter(Q(titulo__icontains=q) | Q(cuerpo__icontains=q))
        return qs.order_by('-fecha_publicacion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secciones'] = SeccionPortalChoices.choices
        context['seccion_actual'] = self.request.GET.get('seccion', '')
        context['busqueda'] = self.request.GET.get('q', '')
        context['titulo_pagina'] = 'Publicaciones y Comunicados'
        return context


class ContenidoWebCreateView(PortalPermissionMixin, CreateView):
    """Redacta y publica un nuevo artículo o comunicado."""
    model = ContenidoWeb
    form_class = ContenidoWebForm
    template_name = 'portal/gestion/publicacion_form.html'
    success_url = reverse_lazy('portal:publicaciones_list')

    def form_valid(self, form):
        pub = form.save(commit=False)
        pub.autor = self.request.user
        pub.save()
        messages.success(self.request, f"El comunicado '{pub.titulo}' fue publicado exitosamente.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Redactar Comunicado o Noticia'
        return context


class ContenidoWebUpdateView(PortalPermissionMixin, UpdateView):
    """Modifica un comunicado o noticia existente."""
    model = ContenidoWeb
    form_class = ContenidoWebForm
    template_name = 'portal/gestion/publicacion_form.html'
    success_url = reverse_lazy('portal:publicaciones_list')

    def form_valid(self, form):
        messages.success(self.request, 'La publicación se actualizó correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Publicación: {self.object.titulo}"
        return context


class ContenidoWebDeleteView(PortalPermissionMixin, DeleteView):
    """Elimina una publicación del portal."""
    model = ContenidoWeb
    template_name = 'portal/gestion/publicacion_confirm_delete.html'
    success_url = reverse_lazy('portal:publicaciones_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        titulo = obj.titulo
        messages.success(request, f"Se eliminó la publicación '{titulo}'.")
        return super().delete(request, *args, **kwargs)


# --- BANDEJA DE SOLICITUDES DE CONTACTO Y MENSAJES DE VISITANTES ---

class BandejaContactoListView(PortalPermissionMixin, ListView):
    """Bandeja de mensajes enviados por padres de familia o encargados desde la web."""
    model = SolicitudContacto
    template_name = 'portal/gestion/solicitudes_list.html'
    context_object_name = 'solicitudes'
    paginate_by = 20

    def get_queryset(self):
        qs = SolicitudContacto.objects.all()
        estado = self.request.GET.get('estado', '').strip()
        q = self.request.GET.get('q', '').strip()

        if estado == 'pendientes':
            qs = qs.filter(atendido=False)
        elif estado == 'atendidos':
            qs = qs.filter(atendido=True)

        if q:
            qs = qs.filter(
                Q(nombre_remitente__icontains=q) |
                Q(correo__icontains=q) |
                Q(telefono__icontains=q) |
                Q(asunto__icontains=q)
            )
        return qs.order_by('-creado_en')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estado_actual'] = self.request.GET.get('estado', '')
        context['busqueda'] = self.request.GET.get('q', '')
        context['total_pendientes'] = SolicitudContacto.objects.filter(atendido=False).count()
        context['titulo_pagina'] = 'Mensajes y Solicitudes de Contacto'
        return context


class AtenderSolicitudContactoView(PortalPermissionMixin, UpdateView):
    """Permite a Secretaría registrar seguimiento y marcar una solicitud como atendida."""
    model = SolicitudContacto
    form_class = AtenderSolicitudContactoForm
    template_name = 'portal/gestion/solicitud_detalle.html'
    success_url = reverse_lazy('portal:solicitudes_list')

    def form_valid(self, form):
        sol = form.save(commit=False)
        if sol.atendido and not sol.atendido_por:
            sol.atendido_por = self.request.user
        sol.save()
        messages.success(self.request, f"Se actualizó el seguimiento para la solicitud de {sol.nombre_remitente}.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Solicitud de Contacto: {self.object.nombre_remitente}"
        return context


class MarcarSolicitudAtendidaRapidoView(PortalPermissionMixin, View):
    """Permite a Dirección o Secretaría marcar una solicitud como atendida rápidamente sin entrar al detalle."""

    def post(self, request, pk):
        solicitud = get_object_or_404(SolicitudContacto, pk=pk)
        solicitud.atendido = True
        if not solicitud.atendido_por:
            solicitud.atendido_por = request.user
        solicitud.save(update_fields=['atendido', 'atendido_por', 'actualizado_en'])
        messages.success(request, f"La consulta de {solicitud.nombre_remitente} fue marcada como atendida.")

        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('portal:solicitudes_list')
        return redirect(next_url)

