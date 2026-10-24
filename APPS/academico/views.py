"""
APPS/academico/views.py

Vistas Basadas en Clases (CBV) para la gestión académica integral del Instituto El Progreso.
Incluye: Configuración de Pensum (Ciclos, Grados, Secciones, Cursos), Inscripciones, Carga Docente,
Ingreso de Notas y Recuperaciones, Cierre Anual con Promoción MINEDUC, Reinscripción Rápida, Asistencia
y Generación de Boletas de Calificaciones en PDF.
"""
import operator
from functools import reduce
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q, Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, FormView, View

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
@require_POST
def activar_ciclo_escolar(request, pk):
    """Activa un ciclo escolar y desactiva los demás (garantiza ciclo activo único)."""
    ciclo = get_object_or_404(CicloEscolar, pk=pk, esta_eliminado=False)

    with transaction.atomic():
        CicloEscolar.objects.filter(esta_eliminado=False).update(estado_activo=False)
        ciclo.estado_activo = True
        ciclo.save(update_fields=['estado_activo', 'actualizado_en'])

        # asegurar que existan los cuatro bloques academicos
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

        # generar automaticamente los bloques academicos por defecto
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



class AsignacionEstudianteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista las asignaciones/inscripciones de estudiantes por sección y ciclo."""

    model = AsignacionEstudiante
    template_name = 'academico/asignacion_estudiante_list.html'
    context_object_name = 'asignaciones'
    permission_required = 'academico.view_asignacionestudiante'
    raise_exception = True
    paginate_by = 25

    def get_queryset(self):
        qs = AsignacionEstudiante.objects.filter(
            esta_eliminado=False,
            estudiante__estado_estudiante='ACTIVO'
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
            # mostrar el ciclo escolar activo por defecto
            try:
                ciclo_activo = CicloEscolar.objects.get(estado_activo=True, esta_eliminado=False)
                qs = qs.filter(ciclo_escolar=ciclo_activo)
            except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
                pass

        # mostrar unicamente estudiantes asignados a las secciones del docente
        usuario = self.request.user
        if getattr(usuario, 'rol', None) == 'DOCENTE' and not usuario.is_superuser:
            secciones_docente = AsignacionDocente.objects.filter(
                personal__persona__usuario=usuario,
                esta_eliminado=False
            ).values_list('seccion_id', flat=True)
            qs = qs.filter(
                Q(seccion_id__in=secciones_docente) |
                Q(seccion__docente_guia__persona__usuario=usuario)
            ).distinct()

        return qs.order_by('seccion__grado__orden', 'seccion__letra', 'estudiante__persona__apellidos')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Inscripciones Académicas'
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

        # generar registros iniciales de notas finales y casilleros de notas bimestrales para los cursos del pensum
        cursos = Curso.objects.filter(grado=asignacion.seccion.grado, esta_eliminado=False)
        bloques = BloqueAcademico.objects.filter(ciclo_escolar=asignacion.ciclo_escolar, esta_eliminado=False)
        for curso in cursos:
            NotaFinalCurso.objects.get_or_create(
                asignacion_estudiante=asignacion,
                curso=curso
            )
            for bloque in bloques:
                NotaBloque.objects.get_or_create(
                    asignacion_estudiante=asignacion,
                    curso=curso,
                    bloque_academico=bloque,
                    defaults={
                        'nota_zona': Decimal('0.00'),
                        'nota_examen': Decimal('0.00'),
                    }
                )

        # generar los cobros de inscripcion correspondientes al ciclo escolar
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
            f'✓ Estudiante {asignacion.estudiante.persona.nombre_completo} inscrito exitosamente en {asignacion.seccion}.'
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

        usuario = self.request.user
        if getattr(usuario, 'rol', None) == 'DOCENTE' and not usuario.is_superuser:
            qs = qs.filter(personal__persona__usuario=usuario)

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        import json
        curso_grados = {c.id: c.grado_id for c in Curso.objects.filter(esta_eliminado=False)}
        seccion_grados = {s.id: s.grado_id for s in Seccion.objects.filter(esta_eliminado=False)}
        context['curso_grados_json'] = json.dumps(curso_grados)
        context['seccion_grados_json'] = json.dumps(seccion_grados)
        return context

    def form_valid(self, form):
        asig = form.save()
        messages.success(
            self.request,
            f'Docente {asig.personal.persona.nombre_completo} asignado a {asig.curso.nombre_curso} ({asig.seccion}).'
        )
        return super().form_valid(form)


class AsignacionDocenteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Permite modificar o reasignar una materia y sección a otro docente."""

    model = AsignacionDocente
    form_class = AsignacionDocenteForm
    template_name = 'academico/asignacion_docente_form.html'
    permission_required = 'academico.change_asignaciondocente'
    raise_exception = True
    success_url = reverse_lazy('academico:asignacion_docente_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        import json
        curso_grados = {c.id: c.grado_id for c in Curso.objects.filter(esta_eliminado=False)}
        seccion_grados = {s.id: s.grado_id for s in Seccion.objects.filter(esta_eliminado=False)}
        context['curso_grados_json'] = json.dumps(curso_grados)
        context['seccion_grados_json'] = json.dumps(seccion_grados)
        context['es_edicion'] = True
        return context

    def form_valid(self, form):
        asig = form.save()
        messages.success(
            self.request,
            f'Materia {asig.curso.nombre_curso} ({asig.seccion}) reasignada exitosamente al docente {asig.personal.persona.nombre_completo}.'
        )
        return super().form_valid(form)



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
                asignacion_estudiante__estudiante__estado_estudiante='ACTIVO',
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
            Q(asignacion_estudiante__ciclo_escolar=ciclo_activo)
            & Q(asignacion_estudiante__estudiante__estado_estudiante='ACTIVO')
            & filtro_pares
            & Q(esta_eliminado=False)
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

        # recalcular la nota final del curso
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


class CuadroCalificacionesView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Cuadro de Calificaciones Masivo (Guatemala):
    Permite el ingreso consolidado y ágil de calificaciones por Curso, Sección y Bimestre
    (Zona 60 pts + Examen 40 pts = Total 100 pts) para todos los estudiantes de la sección.
    """

    template_name = 'academico/docente_notas_lista.html'
    permission_required = 'academico.change_notabloque'
    raise_exception = True

    def get_ciclo_activo(self):
        return CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()

    def get_filtros_usuario(self, usuario, ciclo_activo):
        es_admin = usuario.is_superuser or getattr(usuario, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA']
        if es_admin:
            grados = Grado.objects.filter(esta_eliminado=False).order_by('orden')
            secciones_base = Seccion.objects.filter(esta_eliminado=False).select_related('grado').order_by('grado__orden', 'letra')
            cursos_base = Curso.objects.filter(esta_eliminado=False).select_related('grado').order_by('grado__orden', 'nombre_curso')
            return grados, secciones_base, cursos_base, True
        else:
            asigs = AsignacionDocente.objects.filter(
                personal__persona__usuario=usuario,
                ciclo_escolar=ciclo_activo,
                esta_eliminado=False
            ).select_related('seccion__grado', 'curso__grado')

            grados_ids = asigs.values_list('seccion__grado_id', flat=True).distinct()
            grados = Grado.objects.filter(id__in=grados_ids, esta_eliminado=False).order_by('orden')

            secciones_ids = asigs.values_list('seccion_id', flat=True).distinct()
            secciones_base = Seccion.objects.filter(id__in=secciones_ids, esta_eliminado=False).select_related('grado').order_by('grado__orden', 'letra')

            cursos_ids = asigs.values_list('curso_id', flat=True).distinct()
            cursos_base = Curso.objects.filter(id__in=cursos_ids, esta_eliminado=False).select_related('grado').order_by('grado__orden', 'nombre_curso')
            return grados, secciones_base, cursos_base, False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user
        ciclo_activo = self.get_ciclo_activo()
        context['ciclo_activo'] = ciclo_activo
        context['titulo_pagina'] = 'Cuadro de Calificaciones Masivo'

        if not ciclo_activo:
            context['grados'] = []
            context['secciones'] = []
            context['cursos'] = []
            context['bloques'] = []
            context['notas'] = []
            return context

        grados, secciones_base, cursos_base, es_admin = self.get_filtros_usuario(usuario, ciclo_activo)
        context['grados'] = grados
        context['es_admin'] = es_admin

        # 1. Grado seleccionado
        grado_id = self.request.GET.get('grado') or self.request.POST.get('grado')
        seccion_id = self.request.GET.get('seccion') or self.request.POST.get('seccion')
        curso_id = self.request.GET.get('curso') or self.request.POST.get('curso')
        bloque_id = self.request.GET.get('bloque') or self.request.POST.get('bloque')

        grado_sel = None
        if grado_id:
            grado_sel = grados.filter(pk=grado_id).first()
        elif seccion_id:
            sec_temp = secciones_base.filter(pk=seccion_id).first()
            if sec_temp:
                grado_sel = grados.filter(pk=sec_temp.grado_id).first()

        if not grado_sel and grados.exists():
            grado_sel = grados.first()

        context['grado_sel'] = grado_sel

        # 2. Secciones del Grado seleccionado
        if grado_sel:
            secciones = secciones_base.filter(grado=grado_sel).order_by('letra')
        else:
            secciones = Seccion.objects.none()

        context['secciones'] = secciones

        seccion_sel = None
        if seccion_id:
            seccion_sel = secciones.filter(pk=seccion_id).first()
        if not seccion_sel and secciones.exists():
            seccion_sel = secciones.first()

        context['seccion_sel'] = seccion_sel

        # 3. Cursos del Grado y Sección seleccionados
        if grado_sel and seccion_sel:
            if es_admin:
                cursos = cursos_base.filter(grado=grado_sel).order_by('nombre_curso')
            else:
                asig_curso_ids = AsignacionDocente.objects.filter(
                    personal__persona__usuario=usuario,
                    ciclo_escolar=ciclo_activo,
                    seccion=seccion_sel,
                    esta_eliminado=False
                ).values_list('curso_id', flat=True).distinct()
                cursos = cursos_base.filter(id__in=asig_curso_ids, grado=grado_sel).order_by('nombre_curso')
        else:
            cursos = Curso.objects.none()

        context['cursos'] = cursos

        curso_sel = None
        if curso_id:
            curso_sel = cursos.filter(pk=curso_id).first()
        if not curso_sel and cursos.exists():
            curso_sel = cursos.first()

        context['curso_sel'] = curso_sel

        # 4. Bimestres / Bloques
        bloques = BloqueAcademico.objects.filter(ciclo_escolar=ciclo_activo, esta_eliminado=False).order_by('orden')
        context['bloques'] = bloques

        bloque_sel = None
        if bloque_id:
            bloque_sel = bloques.filter(pk=bloque_id).first()
        if not bloque_sel and bloques.exists():
            bloque_sel = bloques.first()

        context['bloque_sel'] = bloque_sel

        # 5. Si tenemos sección, curso y bloque seleccionados, cargamos/aseguramos las notas
        if seccion_sel and curso_sel and bloque_sel:
            inscripciones = AsignacionEstudiante.objects.filter(
                seccion=seccion_sel,
                ciclo_escolar=ciclo_activo,
                estudiante__estado_estudiante='ACTIVO',
                esta_eliminado=False
            ).select_related('estudiante__persona').order_by(
                'estudiante__persona__apellidos',
                'estudiante__persona__nombres'
            )

            # Auto-generar casilleros de notas bimestrales y notas finales si hicieran falta
            for asig in inscripciones:
                NotaFinalCurso.objects.get_or_create(
                    asignacion_estudiante=asig,
                    curso=curso_sel
                )
                NotaBloque.objects.get_or_create(
                    asignacion_estudiante=asig,
                    curso=curso_sel,
                    bloque_academico=bloque_sel,
                    defaults={
                        'nota_zona': Decimal('0.00'),
                        'nota_examen': Decimal('0.00'),
                    }
                )

            notas = NotaBloque.objects.filter(
                asignacion_estudiante__seccion=seccion_sel,
                asignacion_estudiante__ciclo_escolar=ciclo_activo,
                asignacion_estudiante__estudiante__estado_estudiante='ACTIVO',
                curso=curso_sel,
                bloque_academico=bloque_sel,
                esta_eliminado=False
            ).select_related(
                'asignacion_estudiante__estudiante__persona',
                'asignacion_estudiante__seccion__grado'
            ).order_by(
                'asignacion_estudiante__estudiante__persona__apellidos',
                'asignacion_estudiante__estudiante__persona__nombres'
            )

            context['notas'] = notas
            total_est = notas.count()
            aprobados = sum(1 for n in notas if n.nota_total >= Decimal('60.00'))
            reprobados = total_est - aprobados
            promedio_sec = round(sum(n.nota_total for n in notas) / Decimal(str(total_est)), 2) if total_est > 0 else Decimal('0.00')

            context['total_estudiantes'] = total_est
            context['aprobados_count'] = aprobados
            context['reprobados_count'] = reprobados
            context['promedio_seccion'] = promedio_sec
        else:
            context['notas'] = []
            context['total_estudiantes'] = 0
            context['aprobados_count'] = 0
            context['reprobados_count'] = 0
            context['promedio_seccion'] = Decimal('0.00')

        return context

    def post(self, request, *args, **kwargs):
        usuario = request.user
        ciclo_activo = self.get_ciclo_activo()
        if not ciclo_activo:
            messages.error(request, 'No hay un ciclo escolar activo configurado.')
            return redirect('academico:notas_lista')

        grados, secciones_base, cursos_base, es_admin = self.get_filtros_usuario(usuario, ciclo_activo)

        seccion_id = request.POST.get('seccion')
        curso_id = request.POST.get('curso')
        bloque_id = request.POST.get('bloque')

        seccion = get_object_or_404(Seccion, pk=seccion_id, esta_eliminado=False)
        curso = get_object_or_404(Curso, pk=curso_id, esta_eliminado=False)
        bloque = get_object_or_404(BloqueAcademico, pk=bloque_id, esta_eliminado=False)

        # Validación de que el curso pertenezca al grado de la sección
        if curso.grado_id != seccion.grado_id:
            messages.error(request, f'El curso "{curso.nombre_curso}" no corresponde al grado de la sección "{seccion}".')
            return redirect(f"{reverse('academico:notas_lista')}?grado={seccion.grado_id}&seccion={seccion.id}")

        # Validación de permisos para docentes
        if not es_admin:
            tiene_permiso = AsignacionDocente.objects.filter(
                personal__persona__usuario=usuario,
                ciclo_escolar=ciclo_activo,
                seccion=seccion,
                curso=curso,
                esta_eliminado=False
            ).exists()
            if not tiene_permiso:
                messages.error(request, 'No tiene autorización para calificar este curso en la sección seleccionada.')
                return redirect('academico:notas_lista')

        notas = NotaBloque.objects.filter(
            asignacion_estudiante__seccion=seccion,
            asignacion_estudiante__ciclo_escolar=ciclo_activo,
            asignacion_estudiante__estudiante__estado_estudiante='ACTIVO',
            curso=curso,
            bloque_academico=bloque,
            esta_eliminado=False
        ).select_related('asignacion_estudiante')

        actualizados_count = 0
        with transaction.atomic():
            for nb in notas:
                zona_str = request.POST.get(f'zona_{nb.id}')
                examen_str = request.POST.get(f'examen_{nb.id}')
                if zona_str is not None and examen_str is not None:
                    try:
                        zona = Decimal(zona_str.strip())
                        examen = Decimal(examen_str.strip())
                        if Decimal('0.00') <= zona <= Decimal('60.00') and Decimal('0.00') <= examen <= Decimal('40.00'):
                            nb.nota_zona = zona
                            nb.nota_examen = examen
                            nb.usuario_modificacion = usuario
                            nb.save(update_fields=['nota_zona', 'nota_examen', 'actualizado_en', 'usuario_modificacion'])

                            # Recalcular nota final del curso
                            nf, _ = NotaFinalCurso.objects.get_or_create(
                                asignacion_estudiante=nb.asignacion_estudiante,
                                curso=nb.curso
                            )
                            nf.calcular_nota_final()
                            actualizados_count += 1
                    except (InvalidOperation, ValueError):
                        continue

        messages.success(
            request,
            f'✓ Cuadro de Calificaciones guardado: {actualizados_count} estudiantes calificados para '
            f'"{curso.nombre_curso}" — {seccion} ({bloque.nombre_bloque}).'
        )
        return redirect(f"{reverse('academico:notas_lista')}?grado={seccion.grado_id}&seccion={seccion.id}&curso={curso.id}&bloque={bloque.id}")


# Alias para retrocompatibilidad
DocenteNotasListView = CuadroCalificacionesView


@login_required
def descargar_boleta_notas_pdf(request, pk):
    """Servicio HTTP para descargar la Tarjeta/Boleta de Calificaciones en PDF."""
    asignacion = get_object_or_404(
        AsignacionEstudiante.objects.select_related(
            'estudiante__persona', 'seccion__grado', 'ciclo_escolar'
        ),
        pk=pk,
        esta_eliminado=False
    )
    from APPS.usuarios.permisos import es_titular_o_encargado_de_estudiante
    if not (request.user.has_perm('academico.view_asignacionestudiante') or es_titular_o_encargado_de_estudiante(request.user, asignacion.estudiante)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("No tiene autorización para descargar la Boleta de Calificaciones de este estudiante.")
    return generar_pdf_boleta_notas(asignacion)


@login_required
def descargar_certificacion_pdf(request, pk):
    """Servicio HTTP para descargar la Certificación de Estudios (Kardex Acumulado) en PDF."""
    estudiante = get_object_or_404(Estudiante, pk=pk, persona__esta_eliminado=False)
    from APPS.usuarios.permisos import es_titular_o_encargado_de_estudiante
    if not (request.user.has_perm('academico.view_asignacionestudiante') or es_titular_o_encargado_de_estudiante(request.user, estudiante)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("No tiene autorización para descargar la Certificación de Estudios de este estudiante.")
    return generar_pdf_certificacion_estudios(estudiante)



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

            # recalculo preliminar de notas para la seccion
            promovidos = 0
            retenidos = 0
            estudiantes_con_reprobadas = []

            for asig in inscripciones.select_related('estudiante__persona', 'seccion__grado'):
                notas = list(NotaFinalCurso.objects.filter(asignacion_estudiante=asig, esta_eliminado=False).select_related('curso'))
                if notas:
                    reprobadas = [n for n in notas if not n.esta_promocionado]
                    if not reprobadas:
                        promovidos += 1
                    else:
                        retenidos += 1
                        estudiantes_con_reprobadas.append({
                            'asignacion': asig,
                            'total_reprobadas': len(reprobadas),
                            'aplica_recuperacion': 1 <= len(reprobadas) <= 3,
                            'notas_reprobadas': reprobadas,
                        })

            context['promovidos_count'] = promovidos
            context['retenidos_count'] = retenidos
            context['estudiantes_con_reprobadas'] = estudiantes_con_reprobadas

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

                    # actualizar estado academico en el expediente del estudiante
                    estudiante = asig.estudiante
                    if aprobado_pensum:
                        promovidos_total += 1

                    evaluados_count += 1

        messages.success(
            request,
            f'✓ Cierre del Ciclo Lectivo {ciclo_activo.anio} ejecutado con éxito. '
            f'Total evaluados: {evaluados_count} estudiantes ({promovidos_total} Promovidos).'
        )
        return redirect('academico:reinscripcion_rapida')


class ReinscripcionRapidaView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista de Reinscripción Rápida para el nuevo ciclo lectivo.
    Sugiere automáticamente promover al grado superior o retener al estudiante.
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
            # consulta de estudiantes activos del ciclo previo para sugerencia
            inscripciones = AsignacionEstudiante.objects.filter(
                ciclo_escolar=ciclo_activo,
                estudiante__estado_estudiante='ACTIVO',
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
                    # determinacion de la seccion sugerida para el siguiente ciclo
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
                            # generar notas finales iniciales y casilleros de notas bimestrales para el nuevo grado
                            cursos = Curso.objects.filter(grado=seccion_dest.grado, esta_eliminado=False)
                            bloques = BloqueAcademico.objects.filter(ciclo_escolar=nuevo_ciclo, esta_eliminado=False)
                            for curso in cursos:
                                NotaFinalCurso.objects.get_or_create(
                                    asignacion_estudiante=nueva_asig,
                                    curso=curso
                                )
                                for bloque in bloques:
                                    NotaBloque.objects.get_or_create(
                                        asignacion_estudiante=nueva_asig,
                                        curso=curso,
                                        bloque_academico=bloque,
                                        defaults={
                                            'nota_zona': Decimal('0.00'),
                                            'nota_examen': Decimal('0.00'),
                                        }
                                    )

                            # generar cobros de inscripcion para el nuevo ciclo escolar
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
            f'✓ Reinscripción rápida completada: {reinscritos_count} estudiantes inscritos en el Ciclo Lectivo {nuevo_ciclo.anio}.'
        )
        return redirect('academico:asignacion_estudiante_list')



class AsistenciaSeccionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Control diario masivo de asistencia estudiantil por Grado, Sección, Curso y Fecha.
    Filtro jerárquico estricto: Grado -> Secciones del Grado -> Cursos del Grado.
    """

    permission_required = 'academico.add_asistenciaestudiantil'
    raise_exception = True
    template_name = 'academico/asistencia_seccion.html'

    def get_ciclo_activo(self):
        return CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()

    def get_filtros_usuario(self, usuario, ciclo_activo):
        es_admin = usuario.is_superuser or getattr(usuario, 'rol', None) in ['ADMINISTRADOR', 'DIRECTOR', 'SECRETARIA']
        if es_admin:
            grados = Grado.objects.filter(esta_eliminado=False).order_by('orden')
            secciones_base = Seccion.objects.filter(esta_eliminado=False).select_related('grado').order_by('grado__orden', 'letra')
            cursos_base = Curso.objects.filter(esta_eliminado=False).select_related('grado').order_by('grado__orden', 'nombre_curso')
            return grados, secciones_base, cursos_base, True
        else:
            asigs = AsignacionDocente.objects.filter(
                personal__persona__usuario=usuario,
                ciclo_escolar=ciclo_activo,
                esta_eliminado=False
            ).select_related('seccion__grado', 'curso__grado')

            grados_ids = asigs.values_list('seccion__grado_id', flat=True).distinct()
            grados = Grado.objects.filter(id__in=grados_ids, esta_eliminado=False).order_by('orden')

            secciones_ids = asigs.values_list('seccion_id', flat=True).distinct()
            secciones_base = Seccion.objects.filter(id__in=secciones_ids, esta_eliminado=False).select_related('grado').order_by('grado__orden', 'letra')

            cursos_ids = asigs.values_list('curso_id', flat=True).distinct()
            cursos_base = Curso.objects.filter(id__in=cursos_ids, esta_eliminado=False).select_related('grado').order_by('grado__orden', 'nombre_curso')
            return grados, secciones_base, cursos_base, False

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        context = {}
        usuario = self.request.user
        ciclo_activo = self.get_ciclo_activo()
        context['ciclo_activo'] = ciclo_activo
        context['titulo_pagina'] = 'Control Diario de Asistencia Estudiantil'

        if not ciclo_activo:
            context['grados'] = []
            context['secciones'] = []
            context['cursos'] = []
            context['listado_estudiantes'] = []
            return context

        grados, secciones_base, cursos_base, es_admin = self.get_filtros_usuario(usuario, ciclo_activo)
        context['grados'] = grados
        context['es_admin'] = es_admin

        # 1. Grado
        grado_id = self.request.GET.get('grado') or self.request.POST.get('grado')
        seccion_id = self.request.GET.get('seccion') or self.request.POST.get('seccion')
        curso_id = self.request.GET.get('curso') or self.request.POST.get('curso')
        fecha = self.request.GET.get('fecha') or timezone.localdate().isoformat()
        context['fecha_sel'] = fecha

        grado_sel = None
        if grado_id:
            grado_sel = grados.filter(pk=grado_id).first()
        elif seccion_id:
            sec_temp = secciones_base.filter(pk=seccion_id).first()
            if sec_temp:
                grado_sel = grados.filter(pk=sec_temp.grado_id).first()

        if not grado_sel and grados.exists():
            grado_sel = grados.first()

        context['grado_sel'] = grado_sel

        # 2. Secciones del Grado
        if grado_sel:
            secciones = secciones_base.filter(grado=grado_sel).order_by('letra')
        else:
            secciones = Seccion.objects.none()

        context['secciones'] = secciones

        seccion_sel = None
        if seccion_id:
            seccion_sel = secciones.filter(pk=seccion_id).first()
        if not seccion_sel and secciones.exists():
            seccion_sel = secciones.first()

        context['seccion_sel'] = seccion_sel

        # 3. Cursos del Grado y Sección
        if grado_sel and seccion_sel:
            if es_admin:
                cursos = cursos_base.filter(grado=grado_sel).order_by('nombre_curso')
            else:
                asig_curso_ids = AsignacionDocente.objects.filter(
                    personal__persona__usuario=usuario,
                    ciclo_escolar=ciclo_activo,
                    seccion=seccion_sel,
                    esta_eliminado=False
                ).values_list('curso_id', flat=True).distinct()
                cursos = cursos_base.filter(id__in=asig_curso_ids, grado=grado_sel).order_by('nombre_curso')
        else:
            cursos = Curso.objects.none()

        context['cursos'] = cursos

        curso_sel = None
        if curso_id:
            curso_sel = cursos.filter(pk=curso_id).first()
        if not curso_sel and cursos.exists():
            curso_sel = cursos.first()

        context['curso_sel'] = curso_sel

        # 4. Estudiantes y Asistencias registradas
        if seccion_sel and curso_sel:
            inscritos = AsignacionEstudiante.objects.filter(
                seccion=seccion_sel,
                ciclo_escolar=ciclo_activo,
                estudiante__estado_estudiante='ACTIVO',
                esta_eliminado=False
            ).select_related('estudiante__persona').order_by(
                'estudiante__persona__apellidos',
                'estudiante__persona__nombres'
            )

            asistencias_existentes = {
                a.asignacion_estudiante_id: a
                for a in AsistenciaEstudiantil.objects.filter(
                    asignacion_estudiante__in=inscritos,
                    curso=curso_sel,
                    fecha=fecha,
                    esta_eliminado=False
                )
            }

            listado_estudiantes = []
            for asig in inscritos:
                reg = asistencias_existentes.get(asig.pk)
                if reg:
                    if reg.presente:
                        estado = 'presente'
                    elif reg.justificado:
                        estado = 'justificado'
                    else:
                        estado = 'ausente'
                else:
                    estado = 'presente'

                listado_estudiantes.append({
                    'asignacion': asig,
                    'estado': estado,
                    'presente': (estado == 'presente'),
                    'justificado': (estado == 'justificado'),
                    'ausente': (estado == 'ausente'),
                    'observaciones': reg.observaciones if reg else '',
                })

            context['listado_estudiantes'] = listado_estudiantes
            context['total_estudiantes'] = len(listado_estudiantes)
            context['presentes_count'] = sum(1 for e in listado_estudiantes if e['estado'] == 'presente')
            context['ausentes_count'] = sum(1 for e in listado_estudiantes if e['estado'] == 'ausente')
            context['justificados_count'] = sum(1 for e in listado_estudiantes if e['estado'] == 'justificado')
        else:
            context['listado_estudiantes'] = []
            context['total_estudiantes'] = 0
            context['presentes_count'] = 0
            context['ausentes_count'] = 0
            context['justificados_count'] = 0

        return context

    def post(self, request, *args, **kwargs):
        seccion_id = request.POST.get('seccion')
        curso_id = request.POST.get('curso')
        grado_id = request.POST.get('grado')
        fecha = request.POST.get('fecha')
        asig_ids = request.POST.getlist('asig_ids')

        if not (seccion_id and curso_id and fecha):
            messages.error(request, 'Debe especificar grado, sección, curso y fecha para guardar la asistencia.')
            return redirect('academico:asistencia')

        seccion = get_object_or_404(Seccion, pk=seccion_id, esta_eliminado=False)
        curso = get_object_or_404(Curso, pk=curso_id, esta_eliminado=False)

        # Validación FNBC: el curso debe ser del mismo grado que la sección
        if curso.grado_id != seccion.grado_id:
            messages.error(request, f'El curso "{curso.nombre_curso}" no pertenece al grado de la sección "{seccion}".')
            return redirect(f"{reverse('academico:asistencia')}?grado={seccion.grado_id}&seccion={seccion.id}")

        asistencia_count = 0
        with transaction.atomic():
            for aid in asig_ids:
                estado = request.POST.get(f'estado_{aid}')
                if estado == 'presente':
                    presente = True
                    justificado = False
                elif estado == 'justificado':
                    presente = False
                    justificado = True
                elif estado == 'ausente':
                    presente = False
                    justificado = False
                else:
                    # Fallback para garantizar exclusión mutua
                    chk_p = request.POST.get(f'presente_{aid}') == 'on'
                    chk_j = request.POST.get(f'justificado_{aid}') == 'on'
                    if chk_p:
                        presente = True
                        justificado = False
                    elif chk_j:
                        presente = False
                        justificado = True
                    else:
                        presente = False
                        justificado = False

                obs = request.POST.get(f'obs_{aid}', '').strip()[:255]

                asig = AsignacionEstudiante.objects.filter(pk=aid).first()
                if asig:
                    AsistenciaEstudiantil.objects.update_or_create(
                        asignacion_estudiante=asig,
                        curso=curso,
                        fecha=fecha,
                        defaults={
                            'presente': presente,
                            'justificado': justificado,
                            'observaciones': obs
                        }
                    )
                    asistencia_count += 1

        messages.success(
            request,
            f'✓ Asistencia registrada: {asistencia_count} estudiantes evaluados para {seccion} en "{curso.nombre_curso}" ({fecha}).'
        )
        return redirect(f"{reverse('academico:asistencia')}?grado={seccion.grado_id}&seccion={seccion.id}&curso={curso.id}&fecha={fecha}")


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
        grado_id = self.request.GET.get('grado')
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

        if grado_id:
            qs = qs.filter(asignacion_estudiante__seccion__grado_id=grado_id)

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
        
        grado_id = self.request.GET.get('grado', '')
        seccion_id = self.request.GET.get('seccion', '')
        curso_id = self.request.GET.get('curso', '')
        context['grado_sel'] = grado_id
        context['seccion_sel'] = seccion_id
        context['curso_sel'] = curso_id
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')
        context['estado_sel'] = self.request.GET.get('estado', '')

        grados = Grado.objects.filter(esta_eliminado=False).order_by('orden')
        context['grados'] = grados

        if grado_id:
            context['secciones'] = Seccion.objects.filter(grado_id=grado_id, esta_eliminado=False).order_by('letra')
            context['cursos'] = Curso.objects.filter(grado_id=grado_id, esta_eliminado=False).order_by('nombre_curso')
        elif seccion_id:
            sec = Seccion.objects.filter(pk=seccion_id, esta_eliminado=False).first()
            if sec:
                context['secciones'] = Seccion.objects.filter(grado=sec.grado, esta_eliminado=False).order_by('letra')
                context['cursos'] = Curso.objects.filter(grado=sec.grado, esta_eliminado=False).order_by('nombre_curso')
                context['grado_sel'] = str(sec.grado_id)
            else:
                context['secciones'] = Seccion.objects.filter(esta_eliminado=False).select_related('grado')
                context['cursos'] = Curso.objects.none()
        else:
            context['secciones'] = Seccion.objects.filter(esta_eliminado=False).select_related('grado')
            context['cursos'] = Curso.objects.none()

        return context



class AlertasTempranasView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Tablero de Detección Temprana de Estudiantes en Riesgo Académico y de Asistencia."""

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

        # identificar estudiantes con materias reprobadas segun normativa
        inscritos = AsignacionEstudiante.objects.filter(
            ciclo_escolar=ciclo_activo,
            estudiante__estado_estudiante='ACTIVO',
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

        # identificar estudiantes con inasistencias injustificadas
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

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.aplica_recuperacion:
            if obj.total_materias_reprobadas > 3:
                messages.error(
                    request,
                    f'El estudiante {obj.asignacion_estudiante.estudiante.persona.nombre_completo} reprobó '
                    f'{obj.total_materias_reprobadas} asignaturas en el ciclo lectivo. '
                    f'Conforme al Acuerdo Ministerial 1171-2010 (Art. 26 y 27), el límite legal máximo es de 3 materias para optar a recuperación. '
                    f'El estudiante no tiene derecho a examen de recuperación y debe repetir el grado.'
                )
            else:
                messages.warning(
                    request,
                    f'El curso {obj.curso.nombre_curso} no aplica a examen de recuperación para este estudiante.'
                )
            return redirect('academico:cierre_ciclo_escolar')
        return super().dispatch(request, *args, **kwargs)

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
