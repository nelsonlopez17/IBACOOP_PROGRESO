"""
APPS/usuarios/permisos.py

Definición centralizada de Grupos de Permisos (RBAC) por Rol Institucional
para el Instituto Diversificado por Cooperativa El Progreso (IBACOOP).

Garantiza que cada usuario tenga asignado exactamente el Grupo de Django y
los permisos que corresponden a su rol operativo, además de proveer validadores
de propiedad (anti-IDOR) para Estudiantes, Padres de Familia o Encargados y Personal.
"""
from django.contrib.auth.models import Group, Permission
from APPS.usuarios.models import RolChoices


# mapeo de rol hacia grupo en el sistema de autenticacion
NOMBRE_GRUPO_POR_ROL = {
    RolChoices.ADMINISTRADOR: 'Administradores',
    RolChoices.DIRECTOR: 'Directores',
    RolChoices.SECRETARIA: 'Secretaría',
    RolChoices.CONTADOR: 'Contabilidad',
    RolChoices.DOCENTE: 'Docentes',
    RolChoices.ESTUDIANTE: 'Estudiantes',
    RolChoices.ENCARGADO: 'Padres de Familia o Encargados',
    RolChoices.PERSONAL: 'Personal Operativo',
}

# matriz de permisos por rol institucional
MATRIZ_PERMISOS_POR_ROL = {
    RolChoices.ADMINISTRADOR: '__all__',
    RolChoices.DIRECTOR: {
        'usuarios': ['view_usuario', 'add_usuario', 'change_usuario'],
        'core': ['view_persona', 'add_persona', 'change_persona'],
        'rrhh': [
            'view_puesto', 'add_puesto', 'change_puesto',
            'view_personal', 'add_personal', 'change_personal',
            'view_planilla', 'add_planilla', 'change_planilla',
        ],
        'estudiantes': [
            'view_estudiante', 'add_estudiante', 'change_estudiante',
            'view_encargado', 'add_encargado', 'change_encargado',
            'view_estudianteencargado', 'add_estudianteencargado', 'change_estudianteencargado',
        ],
        'academico': [
            'view_cicloescolar', 'add_cicloescolar', 'change_cicloescolar',
            'view_bloqueacademico', 'add_bloqueacademico', 'change_bloqueacademico',
            'view_grado', 'add_grado', 'change_grado',
            'view_seccion', 'add_seccion', 'change_seccion',
            'view_curso', 'add_curso', 'change_curso',
            'view_asignaciondocente', 'add_asignaciondocente', 'change_asignaciondocente',
            'view_asignacionestudiante', 'add_asignacionestudiante', 'change_asignacionestudiante',
            'view_notabloque', 'add_notabloque', 'change_notabloque',
            'view_notafinalcurso', 'add_notafinalcurso', 'change_notafinalcurso',
            'view_asistenciaestudiantil', 'add_asistenciaestudiantil', 'change_asistenciaestudiantil',
        ],
        'financiero': [
            'view_conceptopago', 'add_conceptopago', 'change_conceptopago',
            'view_cuentaporcobrar', 'add_cuentaporcobrar', 'change_cuentaporcobrar',
            'view_abono', 'add_abono', 'change_abono',
            'view_becadescuento', 'add_becadescuento', 'change_becadescuento',
        ],
        'inventario': [
            'view_articuloinventario', 'add_articuloinventario', 'change_articuloinventario',
            'view_movimientoinventario', 'add_movimientoinventario',
        ],
        'disciplina': [
            'view_incidentedisciplinario', 'add_incidentedisciplinario', 'change_incidentedisciplinario',
            'view_citacionpadre', 'add_citacionpadre', 'change_citacionpadre',
        ],
        'portal': [
            'view_contenidoweb', 'add_contenidoweb', 'change_contenidoweb',
            'view_solicitudcontacto', 'change_solicitudcontacto',
        ],
        'auditoria': ['view_registroauditoria'],
    },
    RolChoices.SECRETARIA: {
        'core': ['view_persona', 'add_persona', 'change_persona'],
        'estudiantes': [
            'view_estudiante', 'add_estudiante', 'change_estudiante',
            'view_encargado', 'add_encargado', 'change_encargado',
            'view_estudianteencargado', 'add_estudianteencargado', 'change_estudianteencargado',
        ],
        'academico': [
            'view_cicloescolar', 'view_bloqueacademico', 'view_grado', 'view_seccion', 'view_curso',
            'view_asignaciondocente',
            'view_asignacionestudiante', 'add_asignacionestudiante', 'change_asignacionestudiante',
            'view_notabloque', 'view_notafinalcurso',
            'view_asistenciaestudiantil', 'add_asistenciaestudiantil',
        ],
        'disciplina': [
            'view_incidentedisciplinario', 'add_incidentedisciplinario', 'change_incidentedisciplinario',
            'view_citacionpadre', 'add_citacionpadre', 'change_citacionpadre',
        ],
        'rrhh': [
            'view_personal',
        ],
        'financiero': [
            'view_cuentaporcobrar', 'view_abono',
        ],
        'inventario': [
            'view_articuloinventario', 'add_articuloinventario', 'change_articuloinventario',
            'view_movimientoinventario', 'add_movimientoinventario',
        ],
        'portal': [
            'view_contenidoweb', 'change_contenidoweb',
            'view_solicitudcontacto', 'change_solicitudcontacto',
        ],
    },
    RolChoices.CONTADOR: {
        'core': ['view_persona', 'add_persona', 'change_persona'],
        'financiero': [
            'view_conceptopago', 'add_conceptopago', 'change_conceptopago',
            'view_cuentaporcobrar', 'add_cuentaporcobrar', 'change_cuentaporcobrar',
            'view_abono', 'add_abono', 'change_abono',
            'view_becadescuento', 'add_becadescuento', 'change_becadescuento',
        ],
        'rrhh': [
            'view_puesto',
            'view_personal', 'add_personal', 'change_personal',
            'view_planilla', 'add_planilla', 'change_planilla',
        ],
        'inventario': [
            'view_articuloinventario', 'add_articuloinventario', 'change_articuloinventario',
            'view_movimientoinventario', 'add_movimientoinventario',
        ],
        'estudiantes': [
            'view_estudiante', 'view_encargado',
        ],
    },
    RolChoices.DOCENTE: {
        'academico': [
            'view_cicloescolar', 'view_bloqueacademico', 'view_grado', 'view_seccion', 'view_curso',
            'view_asignaciondocente', 'view_asignacionestudiante',
            'view_notabloque', 'add_notabloque', 'change_notabloque',
            'view_notafinalcurso', 'change_notafinalcurso',
            'view_asistenciaestudiantil', 'add_asistenciaestudiantil', 'change_asistenciaestudiantil',
        ],
        'disciplina': [
            'view_incidentedisciplinario', 'add_incidentedisciplinario', 'change_incidentedisciplinario',
            'view_citacionpadre', 'add_citacionpadre',
        ],
    },
    # acceso directo por titularidad para estudiantes y encargados
    RolChoices.ESTUDIANTE: {},
    RolChoices.ENCARGADO: {},
    RolChoices.PERSONAL: {
        'inventario': ['view_articuloinventario'],
    },
}

APPS_SISTEMA = [
    'usuarios', 'core', 'rrhh', 'estudiantes', 'academico',
    'financiero', 'inventario', 'disciplina', 'portal', 'auditoria', 'reportes',
]


def configurar_grupos_y_permisos() -> dict[str, Group]:
    """
    Crea o actualiza los 8 Grupos de Permisos oficiales del sistema de acuerdo
    con la matriz de control de acceso basado en roles (RBAC).
    """
    grupos_creados = {}

    for rol, nombre_grupo in NOMBRE_GRUPO_POR_ROL.items():
        grupo, _ = Group.objects.get_or_create(name=nombre_grupo)
        regla = MATRIZ_PERMISOS_POR_ROL.get(rol, {})

        if regla == '__all__':
            permisos = Permission.objects.filter(content_type__app_label__in=APPS_SISTEMA)
            grupo.permissions.set(permisos)
        else:
            permisos_ids = []
            for app_label, codenames in regla.items():
                perms = Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename__in=codenames,
                ).values_list('id', flat=True)
                permisos_ids.extend(perms)
            grupo.permissions.set(permisos_ids)

        grupos_creados[rol] = grupo

    return grupos_creados


def sincronizar_grupo_usuario(usuario) -> None:
    """
    Asigna automáticamente al usuario el Grupo de Django correspondiente a su `rol`
    y limpia cualquier grupo de otro rol anterior para evitar escalación de privilegios.
    """
    if not usuario or not getattr(usuario, 'pk', None) or not getattr(usuario, 'rol', None):
        return

    nombre_grupo = NOMBRE_GRUPO_POR_ROL.get(usuario.rol)
    if not nombre_grupo:
        return

    # asegurar existencia del grupo con sus permisos correspondientes
    grupo = Group.objects.filter(name=nombre_grupo).first()
    if not grupo or not grupo.permissions.exists():
        grupos = configurar_grupos_y_permisos()
        grupo = grupos.get(usuario.rol)

    if grupo:
        nombres_oficiales = list(NOMBRE_GRUPO_POR_ROL.values())
        otros_grupos = usuario.groups.filter(name__in=nombres_oficiales).exclude(pk=grupo.pk)
        if otros_grupos.exists():
            usuario.groups.remove(*otros_grupos)
        if not usuario.groups.filter(pk=grupo.pk).exists():
            usuario.groups.add(grupo)


def es_titular_o_encargado_de_estudiante(usuario, estudiante) -> bool:
    """
    Verifica si el usuario autenticado es el propio Estudiante titular o su
    Padre de Familia o Encargado registrado (principal o en relación M:N).
    """
    if not usuario or not usuario.is_authenticated or not estudiante:
        return False

    # verificar si el usuario es el estudiante
    if getattr(estudiante, 'persona_id', None) and getattr(estudiante.persona, 'usuario_id', None) == usuario.id:
        return True

    # verificar si es el encargado principal
    if getattr(estudiante, 'encargado_id', None) and getattr(estudiante.encargado.persona, 'usuario_id', None) == usuario.id:
        return True

    # verificar si figura en la relacion de encargados
    from APPS.estudiantes.models import EstudianteEncargado
    return EstudianteEncargado.objects.filter(
        estudiante=estudiante,
        encargado__persona__usuario=usuario,
        esta_eliminado=False,
    ).exists()
