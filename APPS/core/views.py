"""
APPS/core/views.py

Vistas principales del sistema ERP Escolar — Instituto "El Progreso".
Provee un Dashboard adaptativo según el Rol y Grupo de Permisos del usuario autenticado.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
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

            context.update({
                'titulo_pagina': 'Mi Portal Estudiantil',
                'mi_estudiante': mi_estudiante,
                'mi_asignacion': mi_asignacion,
                'mis_notas_tabla': mis_notas_tabla,
                'asistencias_presentes': asistencias_presentes,
                'asistencias_justificadas': asistencias_justificadas,
                'asistencias_ausentes': asistencias_ausentes,
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

            context.update({
                'titulo_pagina': 'Panel Docente y Académico',
                'mi_personal': mi_personal,
                'mis_asignaciones_doc': mis_asignaciones_doc,
                'cursos_count': mis_asignaciones_doc.count(),
                'secciones_count': len(secciones_ids),
                'estudiantes_a_cargo': estudiantes_a_cargo,
                'mis_planillas': mis_planillas,
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

        # contexto para personal administrativo
        total_usuarios = Usuario.objects.count()
        usuarios_activos = Usuario.objects.filter(is_active=True).count()
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
