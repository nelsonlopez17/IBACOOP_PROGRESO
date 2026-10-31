"""
APPS/usuarios/permisos.py

Definición centralizada de Grupos de Permisos (RBAC) por Rol Institucional
para el Instituto Básico por Cooperativa El Progreso (IBACOOP).

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
        'auditoria': ['view_eventoseguridad'],
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
            'view_asignaciondocente',
            'view_notabloque', 'add_notabloque', 'change_notabloque',
            'view_notafinalcurso', 'change_notafinalcurso',
            'view_asistenciaestudiantil', 'add_asistenciaestudiantil', 'change_asistenciaestudiantil',
        ],
        'disciplina': [
            'view_incidentedisciplinario', 'view_citacionpadre',
        ],
    },
    # acceso directo por titularidad para estudiantes, encargados y personal operativo
    RolChoices.ESTUDIANTE: {},
    RolChoices.ENCARGADO: {},
    RolChoices.PERSONAL: {},
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
    if not grupo:
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




# interfaz intuitiva de gestion de roles y permisos


GRUPOS_BASE_PROTEGIDOS = set(NOMBRE_GRUPO_POR_ROL.values())


def es_grupo_base_protegido(nombre_grupo: str) -> bool:
    """Indica si un grupo pertenece a los roles base institucionales del sistema."""
    return nombre_grupo in GRUPOS_BASE_PROTEGIDOS


DEFINICION_MODULOS_SISTEMA = [
    {
        'codigo': 'academico',
        'nombre': 'Gestión Académica',
        'icono': 'graduation-cap',
        'descripcion': 'Ciclos escolares, grados, secciones, cursos, asignación de docentes y calificaciones.',
        'modelos': [
            ('cicloescolar', 'Ciclos Escolares'),
            ('grado', 'Grados Académicos'),
            ('seccion', 'Secciones'),
            ('curso', 'Cursos y Asignaturas'),
            ('bloqueacademico', 'Bloques Académicos (Bimestres)'),
            ('asignaciondocente', 'Asignación de Catedráticos'),
            ('asignacionestudiante', 'Inscripción y Asignación de Estudiantes'),
            ('notabloque', 'Calificaciones de Bloque'),
            ('notafinalcurso', 'Calificaciones Finales de Curso'),
            ('asistenciaestudiantil', 'Asistencia Estudiantil'),
        ]
    },
    {
        'codigo': 'estudiantes',
        'nombre': 'Estudiantes y Familias',
        'icono': 'users',
        'descripcion': 'Expedientes de estudiantes, padres de familia o encargados y vínculos familiares.',
        'modelos': [
            ('estudiante', 'Estudiantes'),
            ('encargado', 'Padres de Familia o Encargados'),
            ('estudianteencargado', 'Vínculo Estudiante - Encargado'),
        ]
    },
    {
        'codigo': 'financiero',
        'nombre': 'Finanzas y Pagos',
        'icono': 'receipt',
        'descripcion': 'Conceptos de cuotas escolares, cuentas por cobrar, abonos y becas o descuentos.',
        'modelos': [
            ('conceptopago', 'Conceptos de Cobro y Cuotas'),
            ('cuentaporcobrar', 'Cuentas por Cobrar y Cuotas Mensuales'),
            ('abono', 'Abonos y Boletas de Pago'),
            ('becadescuento', 'Becas y Descuentos'),
        ]
    },
    {
        'codigo': 'rrhh',
        'nombre': 'Recursos Humanos y Planilla',
        'icono': 'briefcase',
        'descripcion': 'Personal docente y administrativo, puestos institucionales, planilla de sueldos y asistencia.',
        'modelos': [
            ('personal', 'Expedientes de Personal'),
            ('puesto', 'Puestos Institucionales'),
            ('planilla', 'Planilla de Sueldos y Salarios'),
            ('asistenciapersonal', 'Asistencia del Personal'),
        ]
    },
    {
        'codigo': 'disciplina',
        'nombre': 'Disciplina y Convivencia',
        'icono': 'shield-alert',
        'descripcion': 'Registro de incidentes disciplinarios y citaciones a padres de familia o encargados.',
        'modelos': [
            ('incidentedisciplinario', 'Incidentes Disciplinarios'),
            ('citacionpadre', 'Citaciones a Encargados'),
        ]
    },
    {
        'codigo': 'inventario',
        'nombre': 'Inventario y Bienes',
        'icono': 'package',
        'descripcion': 'Control de bienes escolares, catálogo de artículos e historial de movimientos.',
        'modelos': [
            ('articuloinventario', 'Artículos de Inventario'),
            ('movimientoinventario', 'Movimientos de Entrada y Salida'),
        ]
    },
    {
        'codigo': 'portal',
        'nombre': 'Portal Web Institucional',
        'icono': 'globe',
        'descripcion': 'Publicación de contenidos escolares, noticias institucionales y solicitudes de contacto.',
        'modelos': [
            ('contenidoweb', 'Publicaciones y Noticias Web'),
            ('solicitudcontacto', 'Solicitudes de Contacto y Admisión'),
        ]
    },
    {
        'codigo': 'usuarios',
        'nombre': 'Control de Accesos y Usuarios',
        'icono': 'user-cog',
        'descripcion': 'Cuentas institucionales de usuario y credenciales de acceso al sistema.',
        'modelos': [
            ('usuario', 'Cuentas de Usuarios'),
        ]
    },
    {
        'codigo': 'core',
        'nombre': 'Datos Base Institucionales',
        'icono': 'building-2',
        'descripcion': 'Registros de personas (CUI), información de contacto y documentos del expediente.',
        'modelos': [
            ('persona', 'Personas y Datos de CUI'),
            ('contactopersona', 'Medios de Contacto'),
            ('documentoexpediente', 'Expedientes y Documentos Digitales'),
        ]
    },
    {
        'codigo': 'auth_axes',
        'nombre': 'Seguridad y Auditoría TI',
        'icono': 'shield-check',
        'descripcion': 'Grupos de roles y permisos, intentos de acceso y bloqueos de seguridad.',
        'modelos': [
            ('group', 'Grupos y Roles de Permisos'),
            ('eventoseguridad', 'Bitácora de Eventos de Seguridad'),
            ('accessattempt', 'Intentos de Acceso Bloqueados'),
            ('accesslog', 'Registros de Auditoría de Sesiones'),
        ]
    },
]


def obtener_matriz_permisos_ui(grupo=None) -> list[dict]:
    """
    Construye una estructura de datos jerárquica con todos los permisos del sistema,
    organizados por módulo institucional y modelo, indicando si están asignados al grupo.
    """
    ids_asignados = set(grupo.permissions.values_list('id', flat=True)) if grupo and getattr(grupo, 'pk', None) else set()

    todos_permisos = Permission.objects.select_related('content_type').exclude(
        content_type__model__startswith='historical'
    ).exclude(
        content_type__app_label__in=['contenttypes', 'sessions']
    )

    permisos_por_modelo = {}
    for p in todos_permisos:
        app_label = p.content_type.app_label
        model_name = p.content_type.model
        key = (app_label, model_name)
        if key not in permisos_por_modelo:
            permisos_por_modelo[key] = {}

        if p.codename.startswith('view_'):
            action = 'view'
        elif p.codename.startswith('add_'):
            action = 'add'
        elif p.codename.startswith('change_'):
            action = 'change'
        elif p.codename.startswith('delete_'):
            action = 'delete'
        else:
            action = p.codename

        permisos_por_modelo[key][action] = {
            'id': p.id,
            'codename': p.codename,
            'nombre': p.name,
            'asignado': p.id in ids_asignados,
        }

    matriz = []
    modelos_procesados = set()

    for mod in DEFINICION_MODULOS_SISTEMA:
        app_label = mod['codigo']
        modelos_data = []
        total_modulo = 0
        asignados_modulo = 0

        for model_code, nombre_legible in mod['modelos']:
            target_app = 'auth' if model_code == 'group' else ('auditoria' if model_code == 'eventoseguridad' else ('axes' if model_code in ['accessattempt', 'accesslog'] else app_label))
            key = (target_app, model_code)
            modelos_procesados.add(key)

            perms_dict = permisos_por_modelo.get(key, {})
            for p_info in perms_dict.values():
                total_modulo += 1
                if p_info['asignado']:
                    asignados_modulo += 1

            modelos_data.append({
                'model_code': model_code,
                'nombre_legible': nombre_legible,
                'permiso_view': perms_dict.get('view'),
                'permiso_add': perms_dict.get('add'),
                'permiso_change': perms_dict.get('change'),
                'permiso_delete': perms_dict.get('delete'),
                'otros': [v for k, v in perms_dict.items() if k not in ('view', 'add', 'change', 'delete')],
            })

        matriz.append({
            'codigo': mod['codigo'],
            'nombre': mod['nombre'],
            'icono': mod['icono'],
            'descripcion': mod['descripcion'],
            'modelos': modelos_data,
            'total_permisos': total_modulo,
            'asignados': asignados_modulo,
        })

    otros_modelos = []
    total_otros = 0
    asignados_otros = 0
    for key, perms_dict in permisos_por_modelo.items():
        if key not in modelos_procesados:
            app_lbl, mdl_nm = key
            for p_info in perms_dict.values():
                total_otros += 1
                if p_info['asignado']:
                    asignados_otros += 1
            otros_modelos.append({
                'model_code': mdl_nm,
                'nombre_legible': f'{app_lbl} / {mdl_nm}',
                'permiso_view': perms_dict.get('view'),
                'permiso_add': perms_dict.get('add'),
                'permiso_change': perms_dict.get('change'),
                'permiso_delete': perms_dict.get('delete'),
                'otros': [v for k, v in perms_dict.items() if k not in ('view', 'add', 'change', 'delete')],
            })

    if otros_modelos:
        matriz.append({
            'codigo': 'otros',
            'nombre': 'Componentes Adicionales del Sistema',
            'icono': 'sliders',
            'descripcion': 'Permisos de módulos complementarios del sistema.',
            'modelos': otros_modelos,
            'total_permisos': total_otros,
            'asignados': asignados_otros,
        })

    return matriz
