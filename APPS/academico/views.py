"""
academico/views.py

Vistas para la gestión académica del Instituto El Progreso.

SEGURIDAD:
    Todas las vistas usan LoginRequiredMixin y PermissionRequiredMixin.
    Los permisos se gestionan mediante Groups y Permissions nativos de Django.
    El campo 'rol' del Usuario NO se usa para control de acceso, solo para UI.
"""
import operator
from functools import reduce
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic import UpdateView, ListView

from APPS.academico.forms import NotaBloqueForm
from APPS.academico.models import (
    AsignacionDocente,
    CicloEscolar,
    NotaBloque,
    NotaFinalCurso,
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
    raise_exception = True   # Muestra una pantalla de acceso denegado si no tiene permiso

    # ──────────────────────────────────────────────────────────────────────────
    # Filtrado de seguridad:
    # Garantiza que el profesor solo pueda ver y modificar las notas de las materias
    # y secciones que tiene asignadas en el año escolar actual.
    # ──────────────────────────────────────────────────────────────────────────
    def get_queryset(self):
        """
        Retorna solo las calificaciones que el profesor tiene autorizado editar.

        Evita el producto cartesiano filtrando por las combinaciones exactas
        de (curso_id, seccion_id) que el docente imparte en el ciclo activo.
        """
        usuario = self.request.user

        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True)
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            return NotaBloque.objects.none()

        asignaciones_docente = AsignacionDocente.objects.filter(
            personal__usuario=usuario,
            ciclo_escolar=ciclo_activo,
        )

        if not asignaciones_docente.exists():
            return NotaBloque.objects.none()

        pares_docente = list(asignaciones_docente.values_list('curso_id', 'seccion_id'))
        if not pares_docente:
            return NotaBloque.objects.none()

        filtro_pares = reduce(
            operator.or_,
            [Q(curso_id=c_id, asignacion_estudiante__seccion_id=s_id) for c_id, s_id in pares_docente]
        )

        return NotaBloque.objects.filter(
            Q(asignacion_estudiante__ciclo_escolar=ciclo_activo) & filtro_pares
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

        context['estudiante'] = nota.asignacion_estudiante.estudiante
        context['seccion'] = nota.asignacion_estudiante.seccion
        context['ciclo'] = nota.bloque_academico.ciclo_escolar
        context['nota_total_actual'] = nota.nota_total
        context['titulo_pagina'] = (
            f"Ingreso de Notas — {nota.curso} / {nota.bloque_academico}"
        )
        return context

    def form_valid(self, form):
        """
        Guarda la nota actualizada registrando el usuario que realizó el cambio
        y actualiza la NotaFinalCurso del estudiante.
        """
        nota = form.save(commit=False)
        nota.usuario_modificacion = self.request.user
        nota.save()

        # Actualiza o genera dinámicamente la nota final acumulada del curso
        nota_final, _ = NotaFinalCurso.objects.get_or_create(
            asignacion_estudiante=nota.asignacion_estudiante,
            curso=nota.curso,
            defaults={'usuario_creacion': self.request.user}
        )
        promedio_actual, promocionado = nota_final.calcular_nota_final()

        estado_texto = "Promocionado" if promocionado else "En evaluación"
        messages.success(
            self.request,
            f'✓ Nota actualizada: {nota.asignacion_estudiante.estudiante} — '
            f'{nota.curso} / {nota.bloque_academico} → '
            f'Zona: {nota.nota_zona}, Examen: {nota.nota_examen}, '
            f'Total Bloque: {nota.nota_total} pts (Promedio acumulado actual: {promedio_actual} pts - {estado_texto})'
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
    en el ciclo escolar activo.
    """
    model = NotaBloque
    template_name = 'academico/docente_notas_lista.html'
    context_object_name = 'notas'
    permission_required = 'academico.change_notabloque'
    raise_exception = True
    paginate_by = 30

    def get_queryset(self):
        """Filtra únicamente por las combinaciones exactas (curso, seccion) asignadas al docente."""
        usuario = self.request.user
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True)
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            return NotaBloque.objects.none()

        asignaciones_docente = AsignacionDocente.objects.filter(
            personal__usuario=usuario,
            ciclo_escolar=ciclo_activo,
        )

        pares_docente = list(asignaciones_docente.values_list('curso_id', 'seccion_id'))
        if not pares_docente:
            return NotaBloque.objects.none()

        filtro_pares = reduce(
            operator.or_,
            [Q(curso_id=c_id, asignacion_estudiante__seccion_id=s_id) for c_id, s_id in pares_docente]
        )

        return NotaBloque.objects.filter(
            Q(asignacion_estudiante__ciclo_escolar=ciclo_activo) & filtro_pares
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
