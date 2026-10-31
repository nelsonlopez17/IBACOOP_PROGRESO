"""
APPS/disciplina/views.py

Vistas y controladores del Módulo de Disciplina y Convivencia Escolar.
Gestiona el panel general de convivencia, registro de incidentes, derecho de audiencia,
emisión de citatorios y actas de compromiso en PDF.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Count, Q
from django.core.paginator import Paginator

from django.core.exceptions import PermissionDenied
from APPS.disciplina.models import IncidenteDisciplinario, CitacionPadre, TipoFaltaChoices, EstadoCitacionChoices
from APPS.disciplina.forms import IncidenteDisciplinarioForm, CitacionPadreForm
from APPS.disciplina.reportes import generar_pdf_citacion_padre, generar_pdf_acta_compromiso
from APPS.estudiantes.models import Estudiante
from APPS.academico.models import CicloEscolar, Grado, Seccion
from APPS.usuarios.permisos import es_titular_o_encargado_de_estudiante


class DisciplinaDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Panel central de control disciplinario y convivencia pacífica.
    Muestra estadísticas globales, semáforos de conducta y listado filtrable de incidentes.
    """
    template_name = 'disciplina/panel.html'
    permission_required = 'disciplina.view_incidentedisciplinario'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True).first()
        qs = IncidenteDisciplinario.objects.select_related(
            'estudiante__persona', 'reportado_por', 'ciclo_escolar'
        ).prefetch_related('citacion')

        if ciclo_activo:
            qs = qs.filter(ciclo_escolar=ciclo_activo)

        # Si el usuario es DOCENTE, acotar exclusivamente a faltas de estudiantes a los que imparte clases
        usuario = self.request.user
        secciones_docente_ids = []
        if getattr(usuario, 'rol', None) == 'DOCENTE' and not usuario.is_superuser:
            from APPS.academico.models import AsignacionDocente, AsignacionEstudiante
            secciones_docente_ids = list(AsignacionDocente.objects.filter(
                personal__persona__usuario=usuario,
                ciclo_escolar=ciclo_activo,
                esta_eliminado=False
            ).values_list('seccion_id', flat=True).distinct())

            estudiantes_docente_ids = AsignacionEstudiante.objects.filter(
                seccion_id__in=secciones_docente_ids,
                ciclo_escolar=ciclo_activo,
                esta_eliminado=False
            ).values_list('estudiante_id', flat=True)

            qs = qs.filter(estudiante_id__in=estudiantes_docente_ids)

        q_search = self.request.GET.get('q', '').strip()
        tipo_falta = self.request.GET.get('tipo_falta', '').strip()
        resuelto = self.request.GET.get('resuelto', '').strip()
        seccion_id = self.request.GET.get('seccion', '').strip()

        if q_search:
            qs = qs.filter(
                Q(estudiante__persona__nombres__icontains=q_search) |
                Q(estudiante__persona__apellidos__icontains=q_search) |
                Q(estudiante__codigo_mineduc__icontains=q_search) |
                Q(descripcion_hechos__icontains=q_search)
            )
        if tipo_falta:
            qs = qs.filter(tipo_falta=tipo_falta)
        if resuelto == 'si':
            qs = qs.filter(esta_resuelto=True)
        elif resuelto == 'no':
            qs = qs.filter(esta_resuelto=False)
        if seccion_id:
            qs = qs.filter(
                estudiante__asignaciones__seccion_id=seccion_id,
                estudiante__asignaciones__esta_eliminado=False
            )

        citaciones_pendientes_qs = CitacionPadre.objects.filter(
            estado=EstadoCitacionChoices.PENDIENTE,
            incidente__in=qs
        )

        metricas = {
            'total_incidentes': qs.count(),
            'faltas_leves': qs.filter(tipo_falta=TipoFaltaChoices.LEVE).count(),
            'faltas_graves': qs.filter(tipo_falta__in=[TipoFaltaChoices.GRAVE, TipoFaltaChoices.MUY_GRAVE]).count(),
            'citaciones_pendientes': citaciones_pendientes_qs.count(),
        }

        # paginacion limpia de incidentes
        paginator = Paginator(qs, 25)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['incidentes'] = page_obj
        context['page_obj'] = page_obj
        context['total_registros'] = qs.count()
        context['metricas'] = metricas
        context['ciclo_activo'] = ciclo_activo
        context['tipos_falta'] = TipoFaltaChoices.choices
        if getattr(usuario, 'rol', None) == 'DOCENTE' and not usuario.is_superuser:
            context['secciones'] = Seccion.objects.filter(id__in=secciones_docente_ids, esta_eliminado=False).select_related('grado').order_by('grado__orden', 'letra')
            context['es_vista_docente'] = True
        else:
            context['secciones'] = Seccion.objects.select_related('grado').all().order_by('grado__orden', 'letra')
            context['es_vista_docente'] = False
        context['filtros'] = {
            'q': q_search,
            'tipo_falta': tipo_falta,
            'resuelto': resuelto,
            'seccion': seccion_id,
        }
        return context


class IncidenteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Permite a docentes o personal registrar un nuevo incidente disciplinario."""
    model = IncidenteDisciplinario
    form_class = IncidenteDisciplinarioForm
    template_name = 'disciplina/incidente_formulario.html'
    permission_required = 'disciplina.add_incidentedisciplinario'
    raise_exception = True

    def get_initial(self):
        initial = super().get_initial()
        estudiante_id = self.request.GET.get('estudiante')
        if estudiante_id:
            initial['estudiante'] = estudiante_id
        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True).first()
        if ciclo_activo:
            initial['ciclo_escolar'] = ciclo_activo
        return initial

    def form_valid(self, form):
        form.instance.reportado_por = self.request.user
        incidente = form.save()
        messages.success(self.request, f'Falta disciplinaria registrada exitosamente para {incidente.estudiante.persona.nombre_completo}.')
        if incidente.requiere_citacion and not hasattr(incidente, 'citacion'):
            return redirect('disciplina:citacion_create', incidente_id=incidente.id)
        return redirect('disciplina:incidente_detail', pk=incidente.id)


class IncidenteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Muestra el expediente completo del incidente, descargos y citaciones asociadas."""
    model = IncidenteDisciplinario
    template_name = 'disciplina/incidente_detalle.html'
    context_object_name = 'incidente'
    permission_required = 'disciplina.view_incidentedisciplinario'
    raise_exception = True

    def has_permission(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or getattr(user, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA']:
            return True
        incidente = self.get_object()
        if getattr(user, 'rol', None) == 'DOCENTE':
            from APPS.academico.models import AsignacionDocente, AsignacionEstudiante
            secciones_docente = AsignacionDocente.objects.filter(
                personal__persona__usuario=user,
                ciclo_escolar=incidente.ciclo_escolar,
                esta_eliminado=False
            ).values_list('seccion_id', flat=True)
            return AsignacionEstudiante.objects.filter(
                estudiante=incidente.estudiante,
                seccion_id__in=secciones_docente,
                ciclo_escolar=incidente.ciclo_escolar,
                esta_eliminado=False
            ).exists()
        try:
            return es_titular_o_encargado_de_estudiante(user, incidente.estudiante)
        except Exception:
            return False


class IncidenteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Permite editar el incidente, registrar el descargo del estudiante o cerrar el caso."""
    model = IncidenteDisciplinario
    form_class = IncidenteDisciplinarioForm
    template_name = 'disciplina/incidente_formulario.html'
    permission_required = 'disciplina.change_incidentedisciplinario'
    raise_exception = True

    def form_valid(self, form):
        incidente = form.save()
        messages.success(self.request, 'Falta disciplinaria actualizada exitosamente.')
        if incidente.requiere_citacion and not hasattr(incidente, 'citacion'):
            messages.info(self.request, 'Este incidente requiere citación al padre de familia o encargado. Puede programarla a continuación.')
            return redirect('disciplina:citacion_create', incidente_id=incidente.id)
        return redirect('disciplina:incidente_detail', pk=incidente.id)


class CitacionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Genera la citación formal al padre de familia vinculada al incidente."""
    model = CitacionPadre
    form_class = CitacionPadreForm
    template_name = 'disciplina/citacion_formulario.html'
    permission_required = 'disciplina.add_citacionpadre'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        incidente = get_object_or_404(IncidenteDisciplinario, id=self.kwargs['incidente_id'])
        if hasattr(incidente, 'citacion'):
            messages.info(request, 'Este incidente ya cuenta con una citación oficial programada.')
            return redirect('disciplina:citacion_update', pk=incidente.citacion.id)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        incidente = get_object_or_404(IncidenteDisciplinario, id=self.kwargs['incidente_id'])
        initial['motivo_citacion'] = f"Comparecencia por {incidente.get_tipo_falta_display()}: {incidente.get_categoria_display()}"
        initial['atendido_por'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['incidente'] = get_object_or_404(IncidenteDisciplinario, id=self.kwargs['incidente_id'])
        return context

    def form_valid(self, form):
        incidente = get_object_or_404(IncidenteDisciplinario, id=self.kwargs['incidente_id'])
        form.instance.incidente = incidente
        citacion = form.save()
        # sincronizar indicador de citacion en el incidente
        if not incidente.requiere_citacion:
            incidente.requiere_citacion = True
            incidente.save()
        messages.success(self.request, 'Citación a padre de familia o encargado programada y registrada exitosamente.')
        return redirect('disciplina:incidente_detail', pk=incidente.id)


class CitacionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Registra la asistencia del padre de familia, acuerdos firmados y observaciones."""
    model = CitacionPadre
    form_class = CitacionPadreForm
    template_name = 'disciplina/citacion_formulario.html'
    permission_required = 'disciplina.change_citacionpadre'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['incidente'] = self.object.incidente
        return context

    def form_valid(self, form):
        citacion = form.save()
        # si la citacion fue debidamente atendida con compromisos, resolver y cerrar el caso automaticamente
        if citacion.estado == EstadoCitacionChoices.ATENDIDA:
            incidente = citacion.incidente
            if not incidente.esta_resuelto:
                incidente.esta_resuelto = True
                incidente.save()
                messages.info(self.request, 'El caso disciplinario ha sido cerrado y marcado como Resuelto tras registrar los compromisos mutuos.')

        messages.success(self.request, 'Datos de la citación actualizados exitosamente.')
        return redirect('disciplina:incidente_detail', pk=citacion.incidente.id)


class DescargarCitacionPDFView(LoginRequiredMixin, View):
    """Descarga el citatorio oficial en formato PDF para entregar al padre o encargado."""
    def get(self, request, pk):
        if getattr(request.user, 'rol', None) == 'ESTUDIANTE':
            raise PermissionDenied("Los estudiantes no tienen autorización para descargar citatorios oficiales en PDF.")
        citacion = get_object_or_404(CitacionPadre, pk=pk)
        if getattr(request.user, 'rol', None) == 'DOCENTE':
            from APPS.academico.models import AsignacionDocente, AsignacionEstudiante
            secciones_docente = AsignacionDocente.objects.filter(
                personal__persona__usuario=request.user,
                ciclo_escolar=citacion.incidente.ciclo_escolar,
                esta_eliminado=False
            ).values_list('seccion_id', flat=True)
            if not AsignacionEstudiante.objects.filter(
                estudiante=citacion.incidente.estudiante,
                seccion_id__in=secciones_docente,
                ciclo_escolar=citacion.incidente.ciclo_escolar,
                esta_eliminado=False
            ).exists():
                raise PermissionDenied("No tiene autorización para descargar este citatorio.")
        if not (request.user.has_perm('disciplina.view_citacionpadre') or es_titular_o_encargado_de_estudiante(request.user, citacion.incidente.estudiante)):
            raise PermissionDenied("No tiene autorización para descargar este citatorio.")
        pdf_bytes = generar_pdf_citacion_padre(citacion)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        apellidos_slug = slugify(citacion.incidente.estudiante.persona.apellidos) or "estudiante"
        filename = f"Citacion_{citacion.id}_{apellidos_slug}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class DescargarActaCompromisoPDFView(LoginRequiredMixin, View):
    """Descarga el Acta Oficial de Compromiso y Convivencia Escolar en PDF."""
    def get(self, request, pk):
        if getattr(request.user, 'rol', None) == 'ESTUDIANTE':
            raise PermissionDenied("Los estudiantes no tienen autorización para descargar actas de compromiso oficiales en PDF.")
        citacion = get_object_or_404(CitacionPadre, pk=pk)
        if getattr(request.user, 'rol', None) == 'DOCENTE':
            from APPS.academico.models import AsignacionDocente, AsignacionEstudiante
            secciones_docente = AsignacionDocente.objects.filter(
                personal__persona__usuario=request.user,
                ciclo_escolar=citacion.incidente.ciclo_escolar,
                esta_eliminado=False
            ).values_list('seccion_id', flat=True)
            if not AsignacionEstudiante.objects.filter(
                estudiante=citacion.incidente.estudiante,
                seccion_id__in=secciones_docente,
                ciclo_escolar=citacion.incidente.ciclo_escolar,
                esta_eliminado=False
            ).exists():
                raise PermissionDenied("No tiene autorización para descargar esta acta de compromiso.")
        if not (request.user.has_perm('disciplina.view_citacionpadre') or es_titular_o_encargado_de_estudiante(request.user, citacion.incidente.estudiante)):
            raise PermissionDenied("No tiene autorización para descargar esta acta de compromiso.")
        pdf_bytes = generar_pdf_acta_compromiso(citacion)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        apellidos_slug = slugify(citacion.incidente.estudiante.persona.apellidos) or "estudiante"
        filename = f"Acta_Compromiso_{citacion.id}_{apellidos_slug}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
