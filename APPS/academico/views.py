"""
academico/views.py

Vistas para la gestión académica del Instituto El Progreso.

SEGURIDAD:
    Todas las vistas usan LoginRequiredMixin y PermissionRequiredMixin.
    Los permisos se gestionan mediante Groups y Permissions nativos de Django.
    El campo 'rol' del Usuario NO se usa para control de acceso, solo para UI.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic import UpdateView, ListView

from APPS.academico.forms import NotaBloqueForm
from APPS.academico.models import (
    AsignacionDocente,
    CicloEscolar,
    NotaBloque,
)


class IngresoNotasUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para que el docente ingrese o actualice las notas de bloque de sus estudiantes.

    SEGURIDAD IMPLEMENTADA:
    ┌─────────────────────────────────────────────────────────────────┐
    │ 1. LoginRequiredMixin:                                          │
    │    Redirige a LOGIN_URL si el usuario no está autenticado.      │
    │                                                                 │
    │ 2. PermissionRequiredMixin (permission_required):               │
    │    Verifica que el usuario tenga el permiso                     │
    │    'academico.change_notabloque' (asignado a través de Groups). │
    │    raise_exception=True retorna HTTP 403 en vez de redirigir.   │
    │                                                                 │
    │ 3. get_queryset() — Filtrado por propietario:                   │
    │    El docente SOLO puede editar notas de los cursos que         │
    │    él mismo imparte en el ciclo escolar activo.                 │
    │    Si intenta acceder a una nota de otro docente, recibe 404.   │
    └─────────────────────────────────────────────────────────────────┘

    Flujo de la vista:
        GET  /academico/notas/<pk>/editar/ → Muestra el formulario con la nota actual.
        POST /academico/notas/<pk>/editar/ → Valida y guarda la nota actualizada.
    """

    model = NotaBloque
    form_class = NotaBloqueForm
    template_name = 'academico/ingreso_notas.html'
    permission_required = 'academico.change_notabloque'
    raise_exception = True   # HTTP 403 en lugar de redirigir al login

    # ──────────────────────────────────────────────────────────────────────────
    # MÉTODO CRÍTICO: get_queryset()
    # Restringe el queryset para garantizar que el docente SOLO pueda modificar
    # las notas de sus propios cursos en el ciclo activo.
    # Django llama a este método automáticamente para obtener el objeto que
    # será editado — si el pk no existe en este queryset, retorna 404.
    # ──────────────────────────────────────────────────────────────────────────
    def get_queryset(self):
        """
        Retorna solo las NotaBloque que el docente autenticado tiene autorizado editar.

        Lógica:
            1. Obtiene el ciclo escolar activo (único con estado_activo=True).
            2. Busca las AsignacionesDocente del usuario actual en ese ciclo.
            3. Filtra las NotaBloque solo donde:
               - El estudiante pertenece a una sección que el docente imparte.
               - El curso es uno de los cursos que el docente imparte.
               - La asignación pertenece al ciclo escolar activo.
        """
        usuario = self.request.user

        # 1. Ciclo escolar activo (debe ser exactamente uno)
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True)
        except CicloEscolar.DoesNotExist:
            # No hay ciclo activo — el docente no puede ingresar notas
            return NotaBloque.objects.none()
        except CicloEscolar.MultipleObjectsReturned:
            # Error de configuración: hay más de un ciclo activo
            return NotaBloque.objects.none()

        # 2. Asignaciones del docente en el ciclo activo
        asignaciones_docente = AsignacionDocente.objects.filter(
            personal__usuario=usuario,
            ciclo_escolar=ciclo_activo,
        ).select_related('curso', 'seccion')

        if not asignaciones_docente.exists():
            # Este usuario no tiene asignaciones docentes en el ciclo activo
            return NotaBloque.objects.none()

        # 3. Extraer los IDs de cursos y secciones autorizados
        curso_ids = list(asignaciones_docente.values_list('curso_id', flat=True))
        seccion_ids = list(asignaciones_docente.values_list('seccion_id', flat=True))

        # 4. Retornar solo las notas dentro del scope del docente
        return NotaBloque.objects.filter(
            curso_id__in=curso_ids,
            asignacion_estudiante__ciclo_escolar=ciclo_activo,
            asignacion_estudiante__seccion_id__in=seccion_ids,
        ).select_related(
            'asignacion_estudiante__estudiante',
            'asignacion_estudiante__seccion',
            'curso',
            'bloque_academico',
        )

    def get_context_data(self, **kwargs):
        """Agrega información adicional al contexto del template."""
        context = super().get_context_data(**kwargs)
        nota = self.object

        # Información contextual para el template
        context['estudiante'] = nota.asignacion_estudiante.estudiante
        context['seccion'] = nota.asignacion_estudiante.seccion
        context['ciclo'] = nota.bloque_academico.ciclo_escolar
        context['nota_total_actual'] = nota.nota_total
        context['estado_aprobacion'] = nota.estado_aprobado_display
        context['titulo_pagina'] = (
            f"Ingreso de Notas — {nota.curso} / {nota.bloque_academico}"
        )
        return context

    def form_valid(self, form):
        """
        Guarda la nota actualizada registrando el usuario que realizó el cambio.

        El campo usuario_modificacion del ModeloAuditable se actualiza aquí
        para mantener la auditoría de quién realizó el último cambio.
        django-simple-history registrará automáticamente el cambio con el usuario
        del request (via HistoryRequestMiddleware en settings.py).
        """
        nota = form.save(commit=False)
        nota.usuario_modificacion = self.request.user
        nota.save()

        messages.success(
            self.request,
            f'✓ Nota actualizada: {nota.asignacion_estudiante.estudiante} — '
            f'{nota.curso} / {nota.bloque_academico} → '
            f'Zona: {nota.nota_zona}, Examen: {nota.nota_examen}, '
            f'Total: {nota.nota_total} pts ({nota.estado_aprobado_display})'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        """Agrega mensaje de error si el formulario no es válido."""
        messages.error(
            self.request,
            'No se pudo guardar la nota. Por favor revise los valores ingresados.'
        )
        return super().form_invalid(form)

    def get_success_url(self):
        """Redirige de vuelta al formulario de la misma nota tras guardar."""
        return reverse_lazy(
            'academico:ingreso_notas',
            kwargs={'pk': self.object.pk}
        )


# ──────────────────────────────────────────────────────────────────────────────
# VISTA ADICIONAL: Lista de notas del docente (complementaria a la anterior)
# ──────────────────────────────────────────────────────────────────────────────

class DocenteNotasListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista de lista: muestra todas las notas que el docente puede gestionar
    en el ciclo escolar activo. Desde aquí navega a IngresoNotasUpdateView.
    """
    model = NotaBloque
    template_name = 'academico/docente_notas_lista.html'
    context_object_name = 'notas'
    permission_required = 'academico.change_notabloque'
    raise_exception = True
    paginate_by = 30

    def get_queryset(self):
        """Reutiliza la misma lógica de filtrado que IngresoNotasUpdateView."""
        usuario = self.request.user
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True)
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            return NotaBloque.objects.none()

        asignaciones_docente = AsignacionDocente.objects.filter(
            personal__usuario=usuario,
            ciclo_escolar=ciclo_activo,
        )

        curso_ids = list(asignaciones_docente.values_list('curso_id', flat=True))
        seccion_ids = list(asignaciones_docente.values_list('seccion_id', flat=True))

        return NotaBloque.objects.filter(
            curso_id__in=curso_ids,
            asignacion_estudiante__ciclo_escolar=ciclo_activo,
            asignacion_estudiante__seccion_id__in=seccion_ids,
        ).select_related(
            'asignacion_estudiante__estudiante',
            'asignacion_estudiante__seccion__grado',
            'curso',
            'bloque_academico',
        ).order_by(
            'asignacion_estudiante__seccion__grado__orden',
            'asignacion_estudiante__seccion__letra',
            'curso__nombre_curso',
            'asignacion_estudiante__estudiante__apellidos',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['ciclo_activo'] = CicloEscolar.objects.get(estado_activo=True)
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            context['ciclo_activo'] = None
        context['titulo_pagina'] = 'Mis Cursos y Notas'
        return context
