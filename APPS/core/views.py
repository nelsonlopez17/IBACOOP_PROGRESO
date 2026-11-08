"""
APPS/core/views.py

Vistas principales del sistema ERP Escolar — Instituto "El Progreso".
Provee un Dashboard adaptativo según el Rol y Grupo de Permisos del usuario autenticado.
"""
from decimal import Decimal
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Sum, Case, When, IntegerField
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import TemplateView
from APPS.usuarios.models import Usuario, RolChoices


class HomeView(LoginRequiredMixin, TemplateView):
    """
    Vista principal (Dashboard) del sistema.
    Adapta su contexto e indicadores según el rol del usuario autenticado:
    - Administración / Dirección / Secretaría / Contabilidad: KPIs institucionales y módulos autorizados.
    - Docente: Carga académica asignada, secciones, calificaciones, asistencia y boletas de pago propias.
    - Estudiante: Portal estudiantil con su grado/sección, calificaciones por bimestre, asistencia y estado de cuenta.
    - Padre de Familia o Encargado: Portal familiar con el resumen académico, disciplinario y financiero de sus hijos/representados.
    - Personal Operativo: Resumen laboral, boletas de pago propias y consulta de inventario.
    """
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        rol = getattr(user, 'rol', '')

        from APPS.academico.models import (
            CicloEscolar, AsignacionEstudiante, AsignacionDocente,
            NotaBloque, NotaFinalCurso, AsistenciaEstudiantil,
        )
        from APPS.estudiantes.models import Estudiante, EstudianteEncargado
        from APPS.rrhh.models import Personal, Planilla
        from APPS.disciplina.models import IncidenteDisciplinario

        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        context['ciclo_activo'] = ciclo_activo

        # contexto para estudiante
        if rol == RolChoices.ESTUDIANTE and not user.is_superuser:
            mi_estudiante = Estudiante.objects.select_related(
                'persona', 'encargado__persona'
            ).filter(persona__usuario=user, esta_eliminado=False).first()

            mi_asignacion = None
            mis_notas_tabla = []
            asistencias_presentes = 0
            asistencias_justificadas = 0
            asistencias_ausentes = 0

            if mi_estudiante:
                mi_asignacion = AsignacionEstudiante.objects.select_related(
                    'seccion__grado', 'ciclo_escolar'
                ).filter(
                    estudiante=mi_estudiante,
                    esta_eliminado=False,
                ).order_by('-ciclo_escolar__anio').first()

                if mi_asignacion:
                    notas_finales = NotaFinalCurso.objects.select_related('curso').filter(
                        asignacion_estudiante=mi_asignacion,
                        esta_eliminado=False,
                    ).order_by('curso__nombre_curso')

                    notas_bloques = NotaBloque.objects.select_related('bloque_academico').filter(
                        asignacion_estudiante=mi_asignacion,
                        esta_eliminado=False,
                    )
                    mapa_bloques = {}
                    for nb in notas_bloques:
                        mapa_bloques.setdefault(nb.curso_id, {})[nb.bloque_academico.nombre_bloque] = nb.nota_total

                    for nf in notas_finales:
                        b_dict = mapa_bloques.get(nf.curso_id, {})
                        mis_notas_tabla.append({
                            'curso': nf.curso.nombre_curso,
                            'b1': b_dict.get('Bimestre I'),
                            'b2': b_dict.get('Bimestre II'),
                            'b3': b_dict.get('Bimestre III'),
                            'b4': b_dict.get('Bimestre IV'),
                            'promedio': nf.nota_definitiva,
                            'aprobado': nf.nota_definitiva >= 60,
                        })

                asist_qs = AsistenciaEstudiantil.objects.filter(
                    asignacion_estudiante__estudiante=mi_estudiante,
                    esta_eliminado=False,
                )
                asistencias_presentes = asist_qs.filter(presente=True).count()
                asistencias_justificadas = asist_qs.filter(presente=False, justificado=True).count()
                asistencias_ausentes = asist_qs.filter(presente=False, justificado=False).count()
                asist_total_est = asistencias_presentes + asistencias_justificadas + asistencias_ausentes
                asistencia_pct = round((asistencias_presentes / asist_total_est * 100), 1) if asist_total_est > 0 else 100.0

            chart_estudiante_cursos = [fila['curso'] for fila in mis_notas_tabla]
            chart_estudiante_notas = [float(fila['promedio'] or 0) for fila in mis_notas_tabla]

            context.update({
                'titulo_pagina': 'Mi Portal Estudiantil',
                'mi_estudiante': mi_estudiante,
                'mi_asignacion': mi_asignacion,
                'mis_notas_tabla': mis_notas_tabla,
                'asistencias_presentes': asistencias_presentes,
                'asistencias_justificadas': asistencias_justificadas,
                'asistencias_ausentes': asistencias_ausentes,
                'asistencia_pct': asistencia_pct,
                'chart_estudiante_cursos_json': json.dumps(chart_estudiante_cursos),
                'chart_estudiante_notas_json': json.dumps(chart_estudiante_notas),
            })
            return context

        # contexto para padre de familia o encargado
        if rol == RolChoices.ENCARGADO and not user.is_superuser:
            ids_rel = EstudianteEncargado.objects.filter(
                encargado__persona__usuario=user,
                esta_eliminado=False,
            ).values_list('estudiante_id', flat=True)

            estudiantes_rep = Estudiante.objects.select_related(
                'persona', 'encargado__persona'
            ).filter(
                Q(encargado__persona__usuario=user) | Q(pk__in=ids_rel),
                esta_eliminado=False,
            ).distinct().order_by('persona__apellidos', 'persona__nombres')

            tarjetas_hijos = []
            for est in estudiantes_rep:
                asig = AsignacionEstudiante.objects.select_related(
                    'seccion__grado', 'ciclo_escolar'
                ).filter(estudiante=est, esta_eliminado=False).order_by('-ciclo_escolar__anio').first()

                asist_qs = AsistenciaEstudiantil.objects.filter(
                    asignacion_estudiante__estudiante=est,
                    esta_eliminado=False,
                )
                incidentes_est = IncidenteDisciplinario.objects.select_related('citacion').filter(
                    estudiante=est,
                    esta_eliminado=False,
                ).order_by('-fecha')[:3]

                tarjetas_hijos.append({
                    'estudiante': est,
                    'asignacion': asig,
                    'presentes': asist_qs.filter(presente=True).count(),
                    'ausentes': asist_qs.filter(presente=False, justificado=False).count(),
                    'incidentes': incidentes_est,
                })

            context.update({
                'titulo_pagina': 'Portal de Padres de Familia o Encargados',
                'tarjetas_hijos': tarjetas_hijos,
            })
            return context

        # contexto para docente
        if rol == RolChoices.DOCENTE and not user.is_superuser:
            mi_personal = Personal.objects.select_related('persona', 'puesto').filter(
                persona__usuario=user,
                esta_eliminado=False,
            ).first()

            mis_asignaciones_doc = AsignacionDocente.objects.select_related(
                'curso__grado', 'seccion__grado', 'ciclo_escolar'
            ).filter(
                personal__persona__usuario=user,
                esta_eliminado=False,
            )
            if ciclo_activo:
                mis_asignaciones_doc = mis_asignaciones_doc.filter(ciclo_escolar=ciclo_activo)

            secciones_ids = list(mis_asignaciones_doc.values_list('seccion_id', flat=True).distinct())
            estudiantes_a_cargo = AsignacionEstudiante.objects.filter(
                seccion_id__in=secciones_ids,
                esta_eliminado=False,
            ).values('estudiante_id').distinct().count() if secciones_ids else 0

            mis_planillas = Planilla.objects.select_related('ciclo_escolar').filter(
                personal__persona__usuario=user,
                esta_eliminado=False,
            ).order_by('-ciclo_escolar__anio', '-mes_pagado')[:6]

            docente_secciones_labels = []
            docente_secciones_data = []
            for asig_doc in mis_asignaciones_doc:
                lbl = f"{asig_doc.seccion.grado.nombre} '{asig_doc.seccion.letra}' - {asig_doc.curso.nombre_curso}"
                if lbl not in docente_secciones_labels:
                    cnt = AsignacionEstudiante.objects.filter(
                        seccion=asig_doc.seccion,
                        ciclo_escolar=ciclo_activo,
                        esta_eliminado=False
                    ).count()
                    docente_secciones_labels.append(lbl)
                    docente_secciones_data.append(cnt)

            context.update({
                'titulo_pagina': 'Panel Docente y Académico',
                'mi_personal': mi_personal,
                'mis_asignaciones_doc': mis_asignaciones_doc,
                'cursos_count': mis_asignaciones_doc.count(),
                'secciones_count': len(secciones_ids),
                'estudiantes_a_cargo': estudiantes_a_cargo,
                'mis_planillas': mis_planillas,
                'chart_docente_labels_json': json.dumps(docente_secciones_labels),
                'chart_docente_data_json': json.dumps(docente_secciones_data),
            })
            return context

        # contexto para personal operativo
        if rol == RolChoices.PERSONAL and not user.is_superuser:
            mi_personal = Personal.objects.select_related('persona', 'puesto').filter(
                persona__usuario=user,
                esta_eliminado=False,
            ).first()
            mis_planillas = Planilla.objects.select_related('ciclo_escolar').filter(
                personal__persona__usuario=user,
                esta_eliminado=False,
            ).order_by('-ciclo_escolar__anio', '-mes_pagado')[:6]

            context.update({
                'titulo_pagina': 'Panel de Personal y Servicios',
                'mi_personal': mi_personal,
                'mis_planillas': mis_planillas,
            })
            return context

        # contexto para personal administrativo (optimizado en 1 sola consulta SQL)
        user_stats = Usuario.objects.aggregate(
            total=Count('id'),
            activos=Count(Case(When(is_active=True, then=1), output_field=IntegerField())),
            admin=Count(Case(When(rol='ADMINISTRADOR', is_active=True, then=1), output_field=IntegerField())),
            director=Count(Case(When(rol='DIRECTOR', is_active=True, then=1), output_field=IntegerField())),
            secretaria=Count(Case(When(rol='SECRETARIA', is_active=True, then=1), output_field=IntegerField())),
            contador=Count(Case(When(rol='CONTADOR', is_active=True, then=1), output_field=IntegerField())),
            docente=Count(Case(When(rol='DOCENTE', is_active=True, then=1), output_field=IntegerField())),
            estudiante=Count(Case(When(rol='ESTUDIANTE', is_active=True, then=1), output_field=IntegerField())),
            encargado=Count(Case(When(rol='ENCARGADO', is_active=True, then=1), output_field=IntegerField())),
        )

        from APPS.academico.models import Grado, Seccion, Curso
        from APPS.financiero.models import CuentaPorCobrar, Abono

        # Estadísticas académicas por grado
        grados_qs = Grado.objects.filter(esta_eliminado=False).annotate(
            total_estudiantes=Count(
                'secciones__asignaciones',
                filter=Q(
                    secciones__asignaciones__ciclo_escolar=ciclo_activo,
                    secciones__asignaciones__esta_eliminado=False,
                    secciones__esta_eliminado=False
                )
            )
        ).order_by('orden')

        chart_grados_labels = [g.nombre for g in grados_qs]
        chart_grados_data = [g.total_estudiantes for g in grados_qs]
        total_estudiantes_matriculados = sum(chart_grados_data)
        total_secciones_activas = Seccion.objects.filter(esta_eliminado=False).count()
        total_cursos_activos = Curso.objects.filter(esta_eliminado=False).count()

        # Finanzas institucionales
        cxc_agg = CuentaPorCobrar.objects.filter(
            ciclo_escolar=ciclo_activo, esta_eliminado=False
        ).aggregate(total=Sum('monto_total')) if ciclo_activo else {'total': Decimal('0.00')}
        total_cxc = float(cxc_agg['total'] or 0)

        abonos_agg = Abono.objects.filter(
            cuenta_por_cobrar__ciclo_escolar=ciclo_activo, esta_eliminado=False
        ).aggregate(total=Sum('monto_pagado')) if ciclo_activo else {'total': Decimal('0.00')}
        total_recaudado = float(abonos_agg['total'] or 0)
        saldo_pendiente = max(0.0, total_cxc - total_recaudado)
        pct_recaudado = round((total_recaudado / total_cxc * 100), 1) if total_cxc > 0 else 0.0

        ultimos_abonos = Abono.objects.select_related(
            'cuenta_por_cobrar__estudiante__persona',
            'cuenta_por_cobrar__concepto'
        ).filter(esta_eliminado=False).order_by('-fecha_pago', '-id')[:6]

        # Asistencia institucional
        asist_stats = AsistenciaEstudiantil.objects.filter(
            asignacion_estudiante__ciclo_escolar=ciclo_activo,
            esta_eliminado=False
        ).aggregate(
            total=Count('id'),
            presentes=Count(Case(When(presente=True, then=1), output_field=IntegerField())),
            justificadas=Count(Case(When(presente=False, justificado=True, then=1), output_field=IntegerField())),
            ausencias=Count(Case(When(presente=False, justificado=False, then=1), output_field=IntegerField())),
        ) if ciclo_activo else {'total': 0, 'presentes': 0, 'justificadas': 0, 'ausencias': 0}

        asist_total = asist_stats['total'] or 0
        asist_presentes = asist_stats['presentes'] or 0
        asist_justificadas = asist_stats['justificadas'] or 0
        asist_ausencias = asist_stats['ausencias'] or 0
        pct_asistencia = round((asist_presentes / asist_total * 100), 1) if asist_total > 0 else 100.0

        # Disciplina
        disciplina_stats = IncidenteDisciplinario.objects.filter(
            ciclo_escolar=ciclo_activo,
            esta_eliminado=False
        ).aggregate(
            total=Count('id'),
            leves=Count(Case(When(tipo_falta='LEVE', then=1), output_field=IntegerField())),
            graves=Count(Case(When(tipo_falta='GRAVE', then=1), output_field=IntegerField())),
            muy_graves=Count(Case(When(tipo_falta='MUY_GRAVE', then=1), output_field=IntegerField())),
        ) if ciclo_activo else {'total': 0, 'leves': 0, 'graves': 0, 'muy_graves': 0}

        # Comunidad de usuarios para gráfico
        comunidad_labels = ['Estudiantes', 'Encargados', 'Docentes', 'Administración']
        admin_y_servicios = (
            (user_stats['admin'] or 0) +
            (user_stats['director'] or 0) +
            (user_stats['secretaria'] or 0) +
            (user_stats['contador'] or 0)
        )
        comunidad_data = [
            user_stats['estudiante'] or 0,
            user_stats['encargado'] or 0,
            user_stats['docente'] or 0,
            admin_y_servicios
        ]

        context.update({
            'total_usuarios': user_stats['total'] or 0,
            'usuarios_activos': user_stats['activos'] or 0,
            'admin_count': user_stats['admin'] or 0,
            'director_count': user_stats['director'] or 0,
            'secretaria_count': user_stats['secretaria'] or 0,
            'contador_count': user_stats['contador'] or 0,
            'docente_count': user_stats['docente'] or 0,
            'estudiante_count': user_stats['estudiante'] or 0,
            'encargado_count': user_stats['encargado'] or 0,
            'titulo_pagina': 'Dashboard Principal',

            # Nuevas métricas y datos para gráficos
            'total_estudiantes_matriculados': total_estudiantes_matriculados,
            'total_secciones_activas': total_secciones_activas,
            'total_cursos_activos': total_cursos_activos,
            'total_cxc': total_cxc,
            'total_recaudado': total_recaudado,
            'saldo_pendiente': saldo_pendiente,
            'pct_recaudado': pct_recaudado,
            'ultimos_abonos': ultimos_abonos,
            'asist_total': asist_total,
            'asist_presentes': asist_presentes,
            'asist_justificadas': asist_justificadas,
            'asist_ausencias': asist_ausencias,
            'pct_asistencia': pct_asistencia,
            'disciplina_stats': disciplina_stats,

            # JSON para Chart.js
            'chart_grados_labels_json': json.dumps(chart_grados_labels),
            'chart_grados_data_json': json.dumps(chart_grados_data),
            'chart_finanzas_data_json': json.dumps([total_recaudado, saldo_pendiente]),
            'chart_asistencia_data_json': json.dumps([asist_presentes, asist_justificadas, asist_ausencias]),
            'chart_comunidad_labels_json': json.dumps(comunidad_labels),
            'chart_comunidad_data_json': json.dumps(comunidad_data),
        })
        return context


def error_403(request, exception=None):
    """
    redirecciona al dashboard si el usuario esta autenticado
    o al portal del visitante si no tiene sesion iniciada.
    """
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'error': 'acceso no autorizado. permiso denegado.'}, status=403)

    if request.user.is_authenticated:
        messages.warning(
            request,
            'No cuenta con los permisos necesarios para acceder a este módulo institucional.'
        )
        return redirect('core:home')

    messages.info(
        request,
        'Debe iniciar sesión para acceder al módulo solicitado.'
    )
    return redirect('portal:index')

