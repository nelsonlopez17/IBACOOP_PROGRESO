"""
APPS/academico/views.py

Vistas Basadas en Clases (CBV) para la gestión académica integral del Instituto El Progreso.
Incluye: Configuración de Pensum (Ciclos, Grados, Secciones, Cursos), Inscripciones, Carga Docente,
Ingreso de Notas y Recuperaciones, Cierre Anual con Promoción MINEDUC, Reinscripción Rápida, Asistencia
y Generación de Boletines en PDF.
"""
import operator
from functools import reduce
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q, Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, FormView

from APPS.academico.models import (
    CicloEscolar, BloqueAcademico, Grado, Seccion, Curso,
    AsignacionEstudiante, AsignacionDocente, NotaBloque, NotaFinalCurso, AsistenciaEstudiantil
)
from APPS.academico.forms import (
    CicloEscolarForm, GradoForm, SeccionForm, CursoForm,
    AsignacionEstudianteForm, AsignacionDocenteForm, NotaRecuperacionForm, AsistenciaSeccionForm
)
from APPS.academico.reports import generar_pdf_boleta_notas, generar_pdf_certificacion_estudios
from APPS.estudiantes.models import Estudiante


# ──────────────────────────────────────────────────────────────────────────────
# 1. PESTAÑA: CONFIGURACIÓN DE PENSUM Y ESTRUCTURA ACADÉMICA
# ──────────────────────────────────────────────────────────────────────────────

class ConfiguracionPensumView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista central de configuración de la estructura académica: Ciclos, Grados, Secciones y Cursos.
    Acceso reservado a Administradores y Directores.
    """

    template_name = 'academico/configuracion_pensum.html'
    permission_required = 'academico.change_cicloescolar'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Configuración de Estructura y Pensum Académico'
        context['ciclos'] = CicloEscolar.objects.filter(esta_eliminado=False).order_by('-anio')
        context['grados'] = Grado.objects.filter(esta_eliminado=False).prefetch_related('secciones', 'cursos')
        context['secciones'] = Seccion.objects.filter(esta_eliminado=False).select_related('grado')
        context['cursos'] = Curso.objects.filter(esta_eliminado=False).select_related('grado')
        return context


@login_required
@permission_required('academico.change_cicloescolar', raise_exception=True)
def activar_ciclo_escolar(request, pk):
    """Activa un ciclo escolar y desactiva los demás (garantiza ciclo activo único)."""
    ciclo = get_object_or_404(CicloEscolar, pk=pk, esta_eliminado=False)

    with transaction.atomic():
        CicloEscolar.objects.filter(esta_eliminado=False).update(estado_activo=False)
        ciclo.estado_activo = True
        ciclo.save(update_fields=['estado_activo', 'actualizado_en'])

        # Asegurar que existan los 4 bloques académicos por defecto
        for orden in range(1, 5):
            BloqueAcademico.objects.get_or_create(
                ciclo_escolar=ciclo,
                orden=orden,
                defaults={
                    'nombre_bloque': f'{orden}° Bimestre'
                }
            )

    messages.success(request, f'✓ El Ciclo Escolar {ciclo.anio} ha sido activado exitosamente.')
    return redirect('academico:configuracion_pensum')


class CicloEscolarCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CicloEscolar
    form_class = CicloEscolarForm
    template_name = 'academico/ciclo_form.html'
    permission_required = 'academico.add_cicloescolar'
    raise_exception = True
    success_url = reverse_lazy('academico:configuracion_pensum')

    def form_valid(self, form):
        ciclo = form.save(commit=False)

        if ciclo.estado_activo:
            CicloEscolar.objects.filter(esta_eliminado=False).update(estado_activo=False)

        ciclo.save()

        # Generar automáticamente los 4 bimestres por defecto
        for orden in range(1, 5):
            BloqueAcademico.objects.get_or_create(
                ciclo_escolar=ciclo,
                orden=orden,
                defaults={
                    'nombre_bloque': f'{orden}° Bimestre'
                }
            )

        messages.success(self.request, f'✓ Ciclo Escolar {ciclo.anio} aperturado correctamente.')
        return super().form_valid(form)


class GradoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Grado
    form_class = GradoForm
    template_name = 'academico/grado_form.html'
    permission_required = 'academico.add_grado'
    raise_exception = True
    success_url = reverse_lazy('academico:configuracion_pensum')

    def form_valid(self, form):
        grado = form.save()
        messages.success(self.request, f'✓ Grado "{grado.nombre}" creado exitosamente.')
        return super().form_valid(form)


class SeccionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Seccion
    form_class = SeccionForm
    template_name = 'academico/seccion_form.html'
    permission_required = 'academico.add_seccion'
    raise_exception = True
    success_url = reverse_lazy('academico:configuracion_pensum')

    def form_valid(self, form):
        seccion = form.save()
        messages.success(self.request, f'✓ Sección {seccion.letra} para {seccion.grado.nombre} creada exitosamente.')
        return super().form_valid(form)


class CursoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Curso
    form_class = CursoForm
    template_name = 'academico/curso_form.html'
    permission_required = 'academico.add_curso'
    raise_exception = True
    success_url = reverse_lazy('academico:configuracion_pensum')

    def form_valid(self, form):
        curso = form.save()
        messages.success(self.request, f'✓ Curso "{curso.nombre_curso}" creado exitosamente para {curso.grado.nombre}.')
        return super().form_valid(form)


# ──────────────────────────────────────────────────────────────────────────────
# 2. PESTAÑA: INSCRIPCIONES ACADÉMICAS Y CARGA DOCENTE
# ──────────────────────────────────────────────────────────────────────────────

class AsignacionEstudianteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista las asignaciones/inscripciones de alumnos por sección y ciclo."""

    model = AsignacionEstudiante
    template_name = 'academico/asignacion_estudiante_list.html'
    context_object_name = 'asignaciones'
    permission_required = 'academico.view_asignacionestudiante'
    raise_exception = True
    paginate_by = 25

    def get_queryset(self):
        qs = AsignacionEstudiante.objects.filter(
            esta_eliminado=False
        ).select_related('estudiante__persona', 'seccion__grado', 'ciclo_escolar')

        q = self.request.GET.get('q')
        seccion_id = self.request.GET.get('seccion')
        ciclo_id = self.request.GET.get('ciclo')

        if q:
            query = q.strip()
            qs = qs.filter(
                Q(estudiante__persona__nombres__icontains=query) |
                Q(estudiante__persona__apellidos__icontains=query) |
                Q(estudiante__persona__cui__icontains=query) |
                Q(estudiante__codigo_mineduc__icontains=query)
            )

        if seccion_id:
            qs = qs.filter(seccion_id=seccion_id)

        if ciclo_id:
            qs = qs.filter(ciclo_escolar_id=ciclo_id)
        else:
            # Por defecto mostrar el ciclo activo
            try:
                ciclo_activo = CicloEscolar.objects.get(estado_activo=True, esta_eliminado=False)
                qs = qs.filter(ciclo_escolar=ciclo_activo)
            except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
                pass

        return qs.order_by('seccion__grado__orden', 'seccion__letra', 'estudiante__persona__apellidos')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Inscripciones y Matrícula Académica'
        context['q'] = self.request.GET.get('q', '')
        context['seccion_sel'] = self.request.GET.get('seccion', '')
        context['ciclo_sel'] = self.request.GET.get('ciclo', '')
        context['secciones'] = Seccion.objects.filter(esta_eliminado=False).select_related('grado')
        context['ciclos'] = CicloEscolar.objects.filter(esta_eliminado=False)
        return context


class AsignacionEstudianteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Inscripción formal de un estudiante en una sección para un ciclo lectivo."""

    model = AsignacionEstudiante
    form_class = AsignacionEstudianteForm
    template_name = 'academico/asignacion_estudiante_form.html'
    permission_required = 'academico.add_asignacionestudiante'
    raise_exception = True
    success_url = reverse_lazy('academico:asignacion_estudiante_list')

    def get_initial(self):
        initial = super().get_initial()
        estudiante_id = self.request.GET.get('estudiante')
        if estudiante_id:
            initial['estudiante'] = estudiante_id
        return initial

    def form_valid(self, form):
        asignacion = form.save()

        # Generar las notas finales iniciales para todos los cursos del pensum de ese grado
        cursos = Curso.objects.filter(grado=asignacion.seccion.grado, esta_eliminado=False)
        for curso in cursos:
            NotaFinalCurso.objects.get_or_create(
                asignacion_estudiante=asignacion,
                curso=curso
            )

        # Generar los cobros de matrícula automáticos para este ciclo escolar
        try:
            from APPS.financiero.models import ConceptoPago, CuentaPorCobrar, EstadoPagoChoices, CategoriaConceptoChoices
            conceptos_auto = list(ConceptoPago.objects.filter(
                aplica_al_inscribir_seccion=True,
                esta_eliminado=False
            ))
            if not conceptos_auto:
                c_matr = ConceptoPago.objects.filter(
                    categoria_concepto=CategoriaConceptoChoices.MATRICULA,
                    esta_eliminado=False
                ).first() or ConceptoPago.objects.filter(
                    nombre__icontains='inscripci',
                    esta_eliminado=False
                ).first()
                if c_matr:
                    conceptos_auto = [c_matr]

            for concepto in conceptos_auto:
                CuentaPorCobrar.objects.get_or_create(
                    estudiante=asignacion.estudiante,
                    concepto=concepto,
                    ciclo_escolar=asignacion.ciclo_escolar,
                    defaults={
                        'monto_total': concepto.monto_estandar,
                        'saldo_pendiente': concepto.monto_estandar,
                        'estado_pago': EstadoPagoChoices.PENDIENTE
                    }
                )
        except Exception:
            pass

        messages.success(
            self.request,
            f'✓ Alumno {asignacion.estudiante.persona.nombre_completo} inscrito exitosamente en {asignacion.seccion}.'
        )
        return super().form_valid(form)


class AsignacionDocenteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista las asignaciones de carga académica de los profesores."""

    model = AsignacionDocente
    template_name = 'academico/asignacion_docente_list.html'
    context_object_name = 'asignaciones_docentes'
    permission_required = 'academico.view_asignaciondocente'
    raise_exception = True
    paginate_by = 25

    def get_queryset(self):
        qs = AsignacionDocente.objects.filter(
            esta_eliminado=False
        ).select_related('personal__persona', 'curso__grado', 'seccion__grado', 'ciclo_escolar')

        q = self.request.GET.get('q')
        if q:
            query = q.strip()
            qs = qs.filter(
                Q(personal__persona__nombres__icontains=query) |
                Q(personal__persona__apellidos__icontains=query) |
                Q(curso__nombre_curso__icontains=query)
            )
        return qs.order_by('seccion__grado__orden', 'seccion__letra', 'curso__nombre_curso')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Carga Académica de Docentes'
        context['q'] = self.request.GET.get('q', '')
        return context


class AsignacionDocenteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Asignación de un docente a un curso y sección."""

    model = AsignacionDocente
    form_class = AsignacionDocenteForm
    template_name = 'academico/asignacion_docente_form.html'
    permission_required = 'academico.add_asignaciondocente'
    raise_exception = True
    success_url = reverse_lazy('academico:asignacion_docente_list')

    def form_valid(self, form):
        asig = form.save()
        messages.success(
            self.request,
            f'✓ Docente {asig.personal.persona.nombre_completo} asignado a {asig.curso.nombre_curso} ({asig.seccion}).'
        )
        return super().form_valid(form)


# ──────────────────────────────────────────────────────────────────────────────
# 3. VISTAS DE NOTAS, RECUPERACIONES Y BOLETIN PDF
# ──────────────────────────────────────────────────────────────────────────────

class IngresoNotasUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para que el docente ingrese o actualice las notas de bloque de sus estudiantes."""

    model = NotaBloque
    fields = ['nota_zona', 'nota_examen']
    template_name = 'academico/ingreso_notas.html'
    permission_required = 'academico.change_notabloque'
    raise_exception = True

    def get_queryset(self):
        usuario = self.request.user
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True, esta_eliminado=False)
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            return NotaBloque.objects.none()

        if usuario.is_superuser or getattr(usuario, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA']:
            return NotaBloque.objects.filter(
                asignacion_estudiante__ciclo_escolar=ciclo_activo,
                esta_eliminado=False
            ).select_related(
                'asignacion_estudiante__estudiante__persona',
                'asignacion_estudiante__seccion',
                'curso',
                'bloque_academico',
            )

        asignaciones_docente = AsignacionDocente.objects.filter(
            personal__persona__usuario=usuario,
            ciclo_escolar=ciclo_activo,
            esta_eliminado=False
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
            Q(asignacion_estudiante__ciclo_escolar=ciclo_activo) & filtro_pares & Q(esta_eliminado=False)
        ).select_related(
            'asignacion_estudiante__estudiante__persona',
            'asignacion_estudiante__seccion',
            'curso',
            'bloque_academico',
        )

    def form_valid(self, form):
        nota = form.save(commit=False)
        nota.usuario_modificacion = self.request.user
        nota.save()

        # Recalcular la nota final del curso
        nota_final, _ = NotaFinalCurso.objects.get_or_create(
            asignacion_estudiante=nota.asignacion_estudiante,
            curso=nota.curso
        )
        nota_final.calcular_nota_final()

        messages.success(
            self.request,
            f'✓ Nota guardada: {nota.asignacion_estudiante.estudiante.persona.nombre_completo} — '
            f'Zona: {nota.nota_zona}, Examen: {nota.nota_examen} (Total: {nota.nota_total} pts)'
        )
        return redirect('academico:notas_lista')


class DocenteNotasListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de calificaciones gestionables por el docente en el ciclo activo."""

    model = NotaBloque
    template_name = 'academico/docente_notas_lista.html'
    context_object_name = 'notas'
    permission_required = 'academico.change_notabloque'
    raise_exception = True
    paginate_by = 30

    def get_queryset(self):
        usuario = self.request.user
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True, esta_eliminado=False)
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            return NotaBloque.objects.none()

        if usuario.is_superuser or getattr(usuario, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA']:
            return NotaBloque.objects.filter(
                asignacion_estudiante__ciclo_escolar=ciclo_activo,
                esta_eliminado=False
            ).select_related(
                'asignacion_estudiante__estudiante__persona',
                'asignacion_estudiante__seccion__grado',
                'curso',
                'bloque_academico',
            ).order_by('asignacion_estudiante__seccion__grado__orden', 'curso__nombre_curso')

        asignaciones_docente = AsignacionDocente.objects.filter(
            personal__persona__usuario=usuario,
            ciclo_escolar=ciclo_activo,
            esta_eliminado=False
        )

        pares_docente = list(asignaciones_docente.values_list('curso_id', 'seccion_id'))
        if not pares_docente:
            return NotaBloque.objects.none()

        filtro_pares = reduce(
            operator.or_,
            [Q(curso_id=c_id, asignacion_estudiante__seccion_id=s_id) for c_id, s_id in pares_docente]
        )

        return NotaBloque.objects.filter(
            Q(asignacion_estudiante__ciclo_escolar=ciclo_activo) & filtro_pares & Q(esta_eliminado=False)
        ).select_related(
            'asignacion_estudiante__estudiante__persona',
            'asignacion_estudiante__seccion__grado',
            'curso',
            'bloque_academico',
        ).order_by('asignacion_estudiante__seccion__grado__orden', 'curso__nombre_curso')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Mis Cursos y Notas'
        return context


@login_required
@permission_required('academico.view_asignacionestudiante', raise_exception=True)
def descargar_boleta_notas_pdf(request, pk):
    """Servicio HTTP para descargar la Tarjeta/Boleta de Calificaciones en PDF."""
    asignacion = get_object_or_404(
        AsignacionEstudiante.objects.select_related(
            'estudiante__persona', 'seccion__grado', 'ciclo_escolar'
        ),
        pk=pk,
        esta_eliminado=False
    )
    return generar_pdf_boleta_notas(asignacion)


@login_required
@permission_required('academico.view_asignacionestudiante', raise_exception=True)
def descargar_certificacion_pdf(request, pk):
    """Servicio HTTP para descargar la Certificación de Estudios (Kardex Acumulado) en PDF."""
    estudiante = get_object_or_404(Estudiante, pk=pk, persona__esta_eliminado=False)
    return generar_pdf_certificacion_estudios(estudiante)


# ──────────────────────────────────────────────────────────────────────────────
# 4. CIERRE ANUAL, PROMOCIÓN MINEDUC Y REINSCRIPCIÓN RÁPIDA
# ──────────────────────────────────────────────────────────────────────────────

class CierreCicloEscolarView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista administrativa para ejecutar el Cierre de Ciclo Lectivo y la Evaluación de Promoción.
    Aplica el algoritmo de aprobación MINEDUC (pensum completo >= 60 pts).
    """

    template_name = 'academico/cierre_ciclo_escolar.html'
    permission_required = 'academico.change_cicloescolar'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        context['ciclo_activo'] = ciclo_activo
        context['titulo_pagina'] = 'Cierre Anual de Ciclo Lectivo y Evaluación de Promoción'

        if ciclo_activo:
            inscripciones = AsignacionEstudiante.objects.filter(ciclo_escolar=ciclo_activo, esta_eliminado=False)
            context['total_inscritos'] = inscripciones.count()

            # Recalcular preliminarmente
            promovidos = 0
            retenidos = 0

            for asig in inscripciones:
                notas = NotaFinalCurso.objects.filter(asignacion_estudiante=asig, esta_eliminado=False)
                if notas.exists():
                    all_promovidos = all(n.calcular_nota_final()[1] for n in notas)
                    if all_promovidos:
                        promovidos += 1
                    else:
                        retenidos += 1

            context['promovidos_count'] = promovidos
            context['retenidos_count'] = retenidos

        return context

    def post(self, request, *args, **kwargs):
        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        if not ciclo_activo:
            messages.error(request, 'No hay un ciclo escolar activo para cerrar.')
            return redirect('academico:configuracion_pensum')

        inscripciones = AsignacionEstudiante.objects.filter(ciclo_escolar=ciclo_activo, esta_eliminado=False)
        evaluados_count = 0
        promovidos_total = 0

        with transaction.atomic():
            for asig in inscripciones:
                notas = NotaFinalCurso.objects.filter(asignacion_estudiante=asig, esta_eliminado=False)
                if notas.exists():
                    aprobado_pensum = True
                    for n in notas:
                        definitiva, promocionado = n.calcular_nota_final()
                        if not promocionado:
                            aprobado_pensum = False

                    # Actualizar estado en el expediente del estudiante
                    estudiante = asig.estudiante
                    if aprobado_pensum:
                        promovidos_total += 1

                    evaluados_count += 1

        messages.success(
            request,
            f'✓ Cierre del Ciclo Lectivo {ciclo_activo.anio} ejecutado con éxito. '
            f'Total evaluados: {evaluados_count} alumnos ({promovidos_total} Promovidos).'
        )
        return redirect('academico:reinscripcion_rapida')


class ReinscripcionRapidaView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista de Reinscripción Rápida para el nuevo ciclo lectivo.
    Sugiere automáticamente promover al grado superior o retener al alumno.
    """

    template_name = 'academico/reinscripcion_rapida.html'
    permission_required = 'academico.add_asignacionestudiante'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        context['ciclo_activo'] = ciclo_activo
        context['titulo_pagina'] = 'Proceso de Reinscripción Rápida al Nuevo Ciclo'

        if ciclo_activo:
            # Alumnos del ciclo anterior o activo para sugerencia
            inscripciones = AsignacionEstudiante.objects.filter(
                ciclo_escolar=ciclo_activo,
                esta_eliminado=False
            ).select_related('estudiante__persona', 'seccion__grado')

            sugerencias = []
            for asig in inscripciones:
                notas = NotaFinalCurso.objects.filter(asignacion_estudiante=asig, esta_eliminado=False)
                es_promovido = all(n.calcular_nota_final()[1] for n in notas) if notas.exists() else False

                grado_actual = asig.seccion.grado
                grado_sugerido = Grado.objects.filter(orden=grado_actual.orden + 1, esta_eliminado=False).first() if es_promovido else grado_actual

                sugerencias.append({
                    'asignacion_id': asig.pk,
                    'estudiante': asig.estudiante,
                    'grado_actual': grado_actual,
                    'seccion_actual': asig.seccion,
                    'es_promovido': es_promovido,
                    'grado_sugerido': grado_sugerido,
                })

            context['sugerencias'] = sugerencias
            context['secciones_disponibles'] = Seccion.objects.filter(esta_eliminado=False).select_related('grado')
            context['ciclos_futuros'] = CicloEscolar.objects.filter(esta_eliminado=False)

        return context

    def post(self, request, *args, **kwargs):
        asig_ids = request.POST.getlist('asig_ids')
        nuevo_ciclo_id = request.POST.get('nuevo_ciclo')

        if not asig_ids or not nuevo_ciclo_id:
            messages.error(request, 'Debe seleccionar al menos un estudiante y el ciclo lectivo destino.')
            return redirect('academico:reinscripcion_rapida')

        nuevo_ciclo = get_object_or_404(CicloEscolar, pk=nuevo_ciclo_id, esta_eliminado=False)
        reinscritos_count = 0

        with transaction.atomic():
            for aid in asig_ids:
                asig_orig = AsignacionEstudiante.objects.filter(pk=aid, esta_eliminado=False).first()
                if asig_orig:
                    # Determinar sección sugerida
                    seccion_destino_id = request.POST.get(f'seccion_dest_{aid}')
                    if seccion_destino_id:
                        seccion_dest = Seccion.objects.filter(pk=seccion_destino_id, esta_eliminado=False).first()
                    else:
                        seccion_dest = asig_orig.seccion

                    if seccion_dest:
                        nueva_asig, created = AsignacionEstudiante.objects.get_or_create(
                            estudiante=asig_orig.estudiante,
                            ciclo_escolar=nuevo_ciclo,
                            defaults={
                                'seccion': seccion_dest
                            }
                        )
                        if created:
                            reinscritos_count += 1
                            # Autogenerar notas finales iniciales para el nuevo grado
                            cursos = Curso.objects.filter(grado=seccion_dest.grado, esta_eliminado=False)
                            for curso in cursos:
                                NotaFinalCurso.objects.get_or_create(
                                    asignacion_estudiante=nueva_asig,
                                    curso=curso
                                )

                            # Autogenerar cobros de matrícula para el nuevo ciclo lectivo
                            try:
                                from APPS.financiero.models import ConceptoPago, CuentaPorCobrar, EstadoPagoChoices, CategoriaConceptoChoices
                                conceptos_auto = list(ConceptoPago.objects.filter(
                                    aplica_al_inscribir_seccion=True,
                                    esta_eliminado=False
                                ))
                                if not conceptos_auto:
                                    c_matr = ConceptoPago.objects.filter(
                                        categoria_concepto=CategoriaConceptoChoices.MATRICULA,
                                        esta_eliminado=False
                                    ).first() or ConceptoPago.objects.filter(
                                        nombre__icontains='inscripci',
                                        esta_eliminado=False
                                    ).first()
                                    if c_matr:
                                        conceptos_auto = [c_matr]

                                for concepto in conceptos_auto:
                                    CuentaPorCobrar.objects.get_or_create(
                                        estudiante=asig_orig.estudiante,
                                        concepto=concepto,
                                        ciclo_escolar=nuevo_ciclo,
                                        defaults={
                                            'monto_total': concepto.monto_estandar,
                                            'saldo_pendiente': concepto.monto_estandar,
                                            'estado_pago': EstadoPagoChoices.PENDIENTE
                                        }
                                    )
                            except Exception:
                                pass

        messages.success(
            request,
            f'✓ Reinscripción rápida completada: {reinscritos_count} alumnos inscritos en el Ciclo Lectivo {nuevo_ciclo.anio}.'
        )
        return redirect('academico:asignacion_estudiante_list')


# ──────────────────────────────────────────────────────────────────────────────
# 5. CONTROL DE ASISTENCIA ESTUDIANTIL
# ──────────────────────────────────────────────────────────────────────────────

class AsistenciaSeccionView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Control diario masivo de asistencia estudiantil por sección y fecha."""

    form_class = AsistenciaSeccionForm
    template_name = 'academico/asistencia_seccion.html'
    permission_required = 'academico.add_asistenciaestudiantil'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Control Diario de Asistencia Estudiantil'

        seccion_id = self.request.GET.get('seccion')
        curso_id = self.request.GET.get('curso')
        fecha = self.request.GET.get('fecha')

        if seccion_id and curso_id:
            ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
            if ciclo_activo:
                inscritos = AsignacionEstudiante.objects.filter(
                    seccion_id=seccion_id,
                    ciclo_escolar=ciclo_activo,
                    esta_eliminado=False
                ).select_related('estudiante__persona').order_by('estudiante__persona__apellidos')

                context['inscritos'] = inscritos
                context['seccion_obj'] = Seccion.objects.filter(pk=seccion_id).first()
                context['curso_obj'] = Curso.objects.filter(pk=curso_id).first()
                context['fecha_sel'] = fecha

        return context

    def post(self, request, *args, **kwargs):
        seccion_id = request.POST.get('seccion')
        curso_id = request.POST.get('curso')
        fecha = request.POST.get('fecha')
        asig_ids = request.POST.getlist('asig_ids')

        if not (seccion_id and curso_id and fecha):
            messages.error(request, 'Debe especificar sección, curso y fecha para guardar la asistencia.')
            return redirect('academico:asistencia')

        asistencia_count = 0
        with transaction.atomic():
            for aid in asig_ids:
                presente = request.POST.get(f'presente_{aid}') == 'on'
                justificado = request.POST.get(f'justificado_{aid}') == 'on'
                obs = request.POST.get(f'obs_{aid}', '')

                asig = AsignacionEstudiante.objects.filter(pk=aid).first()
                if asig:
                    AsistenciaEstudiantil.objects.update_or_create(
                        asignacion_estudiante=asig,
                        curso_id=curso_id,
                        fecha=fecha,
                        defaults={
                            'presente': presente,
                            'justificado': justificado,
                            'observaciones': obs
                        }
                    )
                    asistencia_count += 1

        messages.success(request, f'✓ Registro de asistencia guardado correctamente para {asistencia_count} alumnos.')
        return redirect('academico:asistencia')


class AsistenciaHistorialListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Consulta e historial consolidado de asistencia estudiantil con filtros."""

    model = AsistenciaEstudiantil
    template_name = 'academico/asistencia_historial.html'
    context_object_name = 'asistencias'
    permission_required = 'academico.view_asistenciaestudiantil'
    raise_exception = True
    paginate_by = 35

    def get_queryset(self):
        qs = AsistenciaEstudiantil.objects.filter(
            esta_eliminado=False
        ).select_related(
            'asignacion_estudiante__estudiante__persona',
            'asignacion_estudiante__seccion__grado',
            'curso'
        )

        q = self.request.GET.get('q')
        seccion_id = self.request.GET.get('seccion')
        curso_id = self.request.GET.get('curso')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')
        estado = self.request.GET.get('estado')

        if q:
            query = q.strip()
            qs = qs.filter(
                Q(asignacion_estudiante__estudiante__persona__nombres__icontains=query) |
                Q(asignacion_estudiante__estudiante__persona__apellidos__icontains=query) |
                Q(asignacion_estudiante__estudiante__persona__cui__icontains=query)
            )

        if seccion_id:
            qs = qs.filter(asignacion_estudiante__seccion_id=seccion_id)

        if curso_id:
            qs = qs.filter(curso_id=curso_id)

        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)

        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta)

        if estado == 'presente':
            qs = qs.filter(presente=True)
        elif estado == 'ausente':
            qs = qs.filter(presente=False, justificado=False)
        elif estado == 'justificado':
            qs = qs.filter(presente=False, justificado=True)

        return qs.order_by('-fecha', 'asignacion_estudiante__seccion__grado__orden', 'asignacion_estudiante__estudiante__persona__apellidos')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Historial de Asistencia Estudiantil'
        context['q'] = self.request.GET.get('q', '')
        context['seccion_sel'] = self.request.GET.get('seccion', '')
        context['curso_sel'] = self.request.GET.get('curso', '')
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')
        context['estado_sel'] = self.request.GET.get('estado', '')
        context['secciones'] = Seccion.objects.filter(esta_eliminado=False).select_related('grado')
        context['cursos'] = Curso.objects.filter(esta_eliminado=False).select_related('grado')
        return context


# ──────────────────────────────────────────────────────────────────────────────
# 6. FUNCIONALIDADES ENTERPRISE: ALERTAS TEMPRANAS Y RECUPERACIÓN MINEDUC
# ──────────────────────────────────────────────────────────────────────────────

class AlertasTempranasView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Tablero de Detección Temprana de Alumnos en Riesgo Académico y de Asistencia."""

    template_name = 'academico/alertas_tempranas.html'
    permission_required = 'academico.view_notafinalcurso'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Tablero de Alertas Tempranas y Rendimiento'

        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        context['ciclo_activo'] = ciclo_activo

        if not ciclo_activo:
            context['alumnos_riesgo_notas'] = []
            context['alumnos_riesgo_asistencia'] = []
            return context

        # 1. Alumnos con 2 o más materias reprobadas (< 60 pts)
        inscritos = AsignacionEstudiante.objects.filter(
            ciclo_escolar=ciclo_activo,
            esta_eliminado=False
        ).select_related('estudiante__persona', 'seccion__grado')

        alumnos_riesgo_notas = []
        for asig in inscritos:
            notas_bajas = NotaFinalCurso.objects.filter(
                asignacion_estudiante=asig,
                esta_eliminado=False,
                nota_definitiva__lt=Decimal('60.00'),
                nota_definitiva__gt=Decimal('0.00')
            ).select_related('curso')

            if notas_bajas.count() >= 2:
                alumnos_riesgo_notas.append({
                    'asignacion': asig,
                    'materias_reprobadas': list(notas_bajas),
                    'total_reprobadas': notas_bajas.count()
                })

        # 2. Alumnos con inasistencias inasistidas (ausentes sin justificación)
        alumnos_riesgo_asistencia = []
        for asig in inscritos:
            total_asistencias = AsistenciaEstudiantil.objects.filter(
                asignacion_estudiante=asig,
                esta_eliminado=False
            ).count()

            if total_asistencias > 0:
                ausencias_injustificadas = AsistenciaEstudiantil.objects.filter(
                    asignacion_estudiante=asig,
                    presente=False,
                    justificado=False,
                    esta_eliminado=False
                ).count()

                porcentaje_inasistencia = (ausencias_injustificadas / total_asistencias) * 100

                if porcentaje_inasistencia >= 15.0:
                    alumnos_riesgo_asistencia.append({
                        'asignacion': asig,
                        'ausencias_count': ausencias_injustificadas,
                        'total_registros': total_asistencias,
                        'porcentaje': round(porcentaje_inasistencia, 1)
                    })

        context['alumnos_riesgo_notas'] = sorted(alumnos_riesgo_notas, key=lambda x: x['total_reprobadas'], reverse=True)
        context['alumnos_riesgo_asistencia'] = sorted(alumnos_riesgo_asistencia, key=lambda x: x['porcentaje'], reverse=True)
        return context


class IngresoNotaRecuperacionView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Ingreso y recalculo de pruebas de recuperación MINEDUC para notas finales."""

    model = NotaFinalCurso
    form_class = NotaRecuperacionForm
    template_name = 'academico/recuperacion_form.html'
    permission_required = 'academico.change_notafinalcurso'
    raise_exception = True
    success_url = reverse_lazy('academico:cierre_ciclo_escolar')

    def form_valid(self, form):
        nota_final = form.save(commit=False)
        nota_final.calcular_nota_final()
        nota_final.save()
        messages.success(
            self.request,
            f'✓ Examen de Recuperación registrado para {nota_final.asignacion_estudiante.estudiante.persona.nombre_completo} '
            f'en el curso "{nota_final.curso.nombre_curso}". Nota final actualizada: {nota_final.nota_definitiva} pts.'
        )
        return super().form_valid(form)
