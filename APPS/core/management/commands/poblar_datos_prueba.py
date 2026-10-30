"""
APPS/core/management/commands/poblar_datos_prueba.py

Comando de administración para poblar la base de datos con registros reales y
completos para pruebas integrales en todos los módulos del ERP Escolar
IBACOOP El Progreso (Guatemala).

Cumple estrictamente con:
  - Longitudes de caracteres y validadores de formularios (CUI de 13 dígitos,
    teléfonos de 8 dígitos, códigos MINEDUC de 7 caracteres, NIT guatemalteco).
  - Glosario Oficial Obligatorio de Guatemala (MINEDUC / Decreto Ley 17-95).
  - Al menos 12 a 20+ registros reales por módulo para probar todas las vistas,
    filtros, reportes PDF/CSV y pista de auditoría (creaciones y modificaciones).
"""
from datetime import date, time, datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.utils import timezone

from APPS.usuarios.models import Usuario, RolChoices
from APPS.core.models import Persona, GeneroChoices
from APPS.rrhh.models import (
    Puesto, Personal, Planilla,
    EstadoLaboralChoices, MesChoices
)
from APPS.estudiantes.models import (
    Encargado, Estudiante, EstudianteEncargado,
    ParentescoChoices, EstadoEstudianteChoices
)
from APPS.academico.models import (
    CicloEscolar, BloqueAcademico, Grado, Seccion, Curso,
    AsignacionEstudiante, AsignacionDocente, NotaBloque, NotaFinalCurso, AsistenciaEstudiantil
)
from APPS.financiero.models import (
    ConceptoPago, CuentaPorCobrar, BecaDescuento, Abono,
    EstadoPagoChoices, CategoriaConceptoChoices
)
from APPS.inventario.models import (
    ArticuloInventario, MovimientoInventario,
    CategoriaChoices, TipoMovimientoChoices
)
from APPS.disciplina.models import (
    IncidenteDisciplinario, CitacionPadre,
    TipoFaltaChoices, CategoriaFaltaChoices, EstadoCitacionChoices
)
from APPS.portal.models import (
    ContenidoWeb, SolicitudContacto, SeccionPortalChoices
)


class Command(BaseCommand):
    help = 'Agrega al menos 12+ registros realistas por módulo con nombres reales de Guatemala y longitudes exactas para pruebas integrales.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== INICIANDO POBLADO DE DATOS DE PRUEBA - IBACOOP EL PROGRESO ==='))

        with transaction.atomic():
            grupos_map = self._crear_grupos_y_permisos()
            admin_user = self._obtener_usuario_auditoria()
            puestos_map = self._poblar_puestos()
            personal_list = self._poblar_personal(puestos_map)
            ciclo_2026, ciclo_2025, bloques_2026 = self._poblar_ciclos_y_bloques()
            grados_map, secciones_map, cursos_list = self._poblar_estructura_academica()
            encargados_list = self._poblar_encargados()
            self._normalizar_registros_preexistentes(encargados_list, puestos_map)
            self._poblar_asignaciones_docentes(personal_list, cursos_list, secciones_map, ciclo_2026)
            self._poblar_planillas(personal_list, ciclo_2026, admin_user)

            estudiantes_list = self._poblar_estudiantes_y_relaciones(encargados_list)
            asignaciones_est = self._poblar_inscripciones_y_notas(
                estudiantes_list, secciones_map, cursos_list, ciclo_2026, bloques_2026, admin_user
            )
            self._poblar_asistencia_estudiantil(asignaciones_est, cursos_list)

            conceptos_map = self._poblar_conceptos_pago()
            self._poblar_becas(estudiantes_list, conceptos_map)
            self._poblar_cuentas_y_abonos(estudiantes_list, conceptos_map, ciclo_2026, admin_user)

            articulos_list = self._poblar_inventario(admin_user)
            self._poblar_movimientos_inventario(articulos_list, personal_list)

            self._poblar_disciplina_y_citaciones(estudiantes_list, ciclo_2026, personal_list, admin_user)
            self._poblar_portal_web(admin_user)
            self._asignar_grupos_a_usuarios(grupos_map)

        self.stdout.write(self.style.SUCCESS('[OK] Poblado de datos completado exitosamente en todos los modulos.'))

    def _obtener_usuario_auditoria(self):
        admin_user = Usuario.objects.filter(is_superuser=True).first() or Usuario.objects.first()
        return admin_user

    def _crear_grupos_y_permisos(self):
        from APPS.usuarios.permisos import configurar_grupos_y_permisos
        # eliminar grupos duplicados antiguos
        Group.objects.filter(name__in=['Dirección', 'Docentes Guía', 'Comisión de Disciplina']).delete()
        grupos_por_rol = configurar_grupos_y_permisos()
        self.stdout.write(f'  -> Grupos de seguridad RBAC configurados: {Group.objects.count()} grupos oficiales.')
        return grupos_por_rol

    def _asignar_grupos_a_usuarios(self, grupos_map):
        from APPS.usuarios.permisos import sincronizar_grupo_usuario
        for u in Usuario.objects.all():
            u.user_permissions.clear()
            u.groups.clear()
            sincronizar_grupo_usuario(u)


    def _normalizar_registros_preexistentes(self, encargados_list, puestos_map):
        """
        Normaliza registros de prueba antiguos que tenían textos ficticios o incompletos
        asignándoles nombres reales guatemaltecos, teléfonos de 8 dígitos y códigos MINEDUC válidos,
        preservando intacto al usuario administrador principal (Nelson Lopez).
        """
        reemplazos_personas = {
            '1234567891234': ('Isabella María', 'López Castellanos', date(2012, 5, 14), GeneroChoices.FEMENINO, '3a. Avenida 2-14 Zona 1, El Progreso, Jutiapa', '54128741', 'isabella.lopez@est.ibacoop.edu.gt', 'R741MNP'),
            '1231231231234': ('Sebastián Alejandro', 'Méndez Cordón', date(2012, 8, 22), GeneroChoices.MASCULINO, '4a. Calle 5-19 Zona 2, El Progreso, Jutiapa', '45213698', 'sebastian.mendez@est.ibacoop.edu.gt', 'S852QWE'),
            '1234512345123': ('Camila Alejandra', 'Guzmán Sandoval', date(2013, 1, 19), GeneroChoices.FEMENINO, '2a. Avenida 6-10 Zona 1, El Progreso, Jutiapa', '51247896', 'camila.guzman@est.ibacoop.edu.gt', 'T963ASD'),
            '3213213213211': ('Juan Fernando', 'Cifuentes Villatoro', date(2011, 11, 10), GeneroChoices.MASCULINO, 'Barrio El Calvario, Calle Principal, El Progreso, Jutiapa', '48963214', 'juan.cifuentes@est.ibacoop.edu.gt', 'U159ZXC'),
            '0987654321123': ('Daniela Sofía', 'Pineda Sagastume', date(2012, 3, 28), GeneroChoices.FEMENINO, 'Colonia Las Brisas Casa #12, El Progreso, Jutiapa', '53698745', 'daniela.pineda@est.ibacoop.edu.gt', 'V357PLM'),
            '1111122222333': ('Mario Augusto', 'Cabrera Archila', date(1985, 4, 12), GeneroChoices.MASCULINO, '5a. Calle 3-40 Zona 1, El Progreso, Jutiapa', '57841236', 'mario.cabrera@ibacoop.edu.gt', None),
            '1234512345124': ('Otto Vinicio', 'Pérez Monzón', date(1977, 9, 15), GeneroChoices.MASCULINO, '6a. Avenida 1-22 Zona 2, El Progreso, Jutiapa', '41257896', 'otto.perez.m@gmail.com', None),
            '9876543219876': ('Pedro Pablo', 'Echeverría Godoy', date(1980, 2, 18), GeneroChoices.MASCULINO, '3a. Calle 7-15 Zona 3, El Progreso, Jutiapa', '52147852', 'pedro.echeverria@gmail.com', None),
            '8888888888888': ('Roberto Antonio', 'Baldetti Paz', date(1975, 6, 30), GeneroChoices.MASCULINO, '4a. Avenida 4-18 Zona 1, El Progreso, Jutiapa', '46325896', 'roberto.baldetti@gmail.com', None),
            '3213213213212': ('Héctor Eduardo', 'Cifuentes Monroy', date(1979, 12, 5), GeneroChoices.MASCULINO, 'Barrio San José, El Progreso, Jutiapa', '58961472', 'hector.cifuentes@gmail.com', None),
            '9999999999999': ('Roxana Gabriela', 'Baldetti Paz', date(2011, 7, 14), GeneroChoices.FEMENINO, '4a. Avenida 4-18 Zona 1, El Progreso, Jutiapa', '46325896', 'roxana.baldetti@est.ibacoop.edu.gt', 'W753OKN'),
            '1231233455678': ('Enrique Alejandro', 'Fernández Solares', date(2012, 10, 8), GeneroChoices.MASCULINO, 'Aldea Acequia, El Progreso, Jutiapa', '54789632', 'enrique.fernandez@est.ibacoop.edu.gt', 'X951IJB'),
            '1111111111123': ('Pedro José', 'Jiménez Dardón', date(2013, 4, 21), GeneroChoices.MASCULINO, '1a. Calle 8-05 Zona 1, El Progreso, Jutiapa', '43698524', 'pedro.jimenez@est.ibacoop.edu.gt', 'Y258UHV'),
            '3467826487364': ('Juan Antonio', 'López Samayoa', date(2011, 9, 17), GeneroChoices.MASCULINO, '2a. Calle 3-11 Zona 2, El Progreso, Jutiapa', '47451937', 'juan.lopez.s@est.ibacoop.edu.gt', 'Z654TGB'),
            '1231231231223': ('Nelson Estuardo', 'López Hernández', date(1988, 6, 15), GeneroChoices.MASCULINO, '3a. Avenida 5-20 Zona 1, El Progreso, Jutiapa', '55124789', 'nelson.docente@ibacoop.edu.gt', None),
        }

        for idx, (cui, (nom, ape, fnac, gen, direc, tel, correo, cod_min)) in enumerate(reemplazos_personas.items()):
            persona = Persona.todos.filter(cui=cui).first()
            if not persona:
                continue
            persona.nombres = nom
            persona.apellidos = ape
            persona.fecha_nacimiento = fnac
            persona.genero = gen
            persona.direccion = direc
            persona.telefono_principal = tel
            persona.correo = correo
            persona.save()

            if persona.usuario:
                persona.usuario.first_name = nom
                persona.usuario.last_name = ape
                persona.usuario.email = correo
                persona.usuario.save(update_fields=['first_name', 'last_name', 'email'])

            if cod_min and hasattr(persona, 'estudiante'):
                est = persona.estudiante
                est.codigo_mineduc = cod_min
                if not est.encargado and encargados_list:
                    est.encargado = encargados_list[idx % len(encargados_list)]
                if not est.nombre_padre:
                    est.nombre_padre = f'Carlos Antonio {ape.split()[0]}'
                    est.telefono_padre = tel
                if not est.nombre_madre:
                    est.nombre_madre = f'María Elena {ape.split()[-1]}'
                    est.telefono_madre = '42158963'
                if not est.historial_medico:
                    est.historial_medico = 'Buena salud general. Esquema de vacunación completo.'
                est.doc_cert_nacimiento_renap = True
                est.doc_dpi_encargado = True
                est.doc_certificado_grado_anterior = True
                est.doc_diploma_primaria = True
                est.doc_codigo_mineduc = True
                est.save()

                if est.encargado:
                    EstudianteEncargado.objects.update_or_create(
                        estudiante=est,
                        encargado=est.encargado,
                        defaults={
                            'parentesco': ParentescoChoices.PADRE,
                            'es_contacto_principal': True,
                            'esta_eliminado': False,
                        }
                    )

            if hasattr(persona, 'encargado'):
                enc = persona.encargado
                if not enc.lugar_de_trabajo:
                    enc.lugar_de_trabajo = 'Comerciante y Productor Agrícola Independiente'
                    enc.save()

            if hasattr(persona, 'personal'):
                emp = persona.personal
                if not emp.nit:
                    emp.nit = f'{4512360 + idx}-8'
                if not emp.numero_contrato_fisico:
                    emp.numero_contrato_fisico = f'CONT-IBACOOP-2025-{idx:03d}'
                if not emp.ubicacion_expediente_fisico:
                    emp.ubicacion_expediente_fisico = f'Archivador B-2, Gaveta 1, Carpeta #{idx:02d} (Secretaría)'
                if not emp.contacto_emergencia_nombre:
                    emp.contacto_emergencia_nombre = f'Ana María {ape.split()[-1]}'
                    emp.contacto_emergencia_telefono = '54128963'
                emp.doc_dpi_personal = True
                emp.doc_nit_sat = True
                emp.doc_titulo_academico = True
                emp.doc_colegiado_activo = True
                emp.doc_antecedentes_penales = True
                emp.doc_antecedentes_policiales = True
                emp.doc_contrato_fisico = True
                emp.doc_tarjeta_salud = True
                emp.save()

        # normalizar conceptos y cursos preexistentes
        ConceptoPago.todos.filter(nombre__iexact='kermesse 2026').update(
            nombre='Actividad Cultural y Gastronómica Escolar 2026',
            categoria_concepto=CategoriaConceptoChoices.EVENTOS
        )
        Curso.todos.filter(codigo_curso='MAT-1').update(nombre_curso='Matemáticas Prácticas I (Taller)')
        Curso.todos.filter(codigo_curso='LENG-1').update(nombre_curso='Taller de Lectura y Redacción I')

    def _poblar_puestos(self):
        datos_puestos = [
            ('Director General', 'Dirección general, representación legal y supervisión pedagógica del instituto por cooperativa.'),
            ('Subdirector Técnico Pedagógico', 'Coordinación curricular del CNB, acompañamiento docente y evaluación educativa.'),
            ('Coordinador Académico', 'Supervisión de horarios, cargas académicas y cumplimiento de bloques bimestrales.'),
            ('Secretaria de Dirección', 'Control de inscripciones, expedientes de estudiantes, certificaciones SIRE y atención al público.'),
            ('Contador General', 'Administración de cuotas escolares, cuentas por cobrar, caja, bancos y planilla de sueldos.'),
            ('Auxiliar Administrativo', 'Apoyo operativo a secretaría general, archivo físico y recepción de documentos.'),
            ('Docente / Catedrático', 'Personal docente encargado de impartir cursos oficiales del Nivel Básico (MINEDUC).'),
            ('Docente Guía', 'Docente encargado del acompañamiento pedagógico, asistencia y disciplina de una sección asignada.'),
            ('Encargado de Laboratorio de Computación', 'Administración del equipo tecnológico y docencia del área de Tecnologías del Aprendizaje.'),
            ('Orientador Escolar', 'Acompañamiento psicopedagógico, convivencia pacífica y atención a padres de familia o encargados.'),
            ('Bibliotecario Escolar', 'Resguardo del acervo bibliográfico, textos del MINEDUC y préstamos de material didáctico.'),
            ('Personal de Servicios / Conserjería', 'Mantenimiento preventivo, limpieza e higiene de las instalaciones educativas.'),
        ]
        puestos_map = {}
        for nombre, desc in datos_puestos:
            puesto, _ = Puesto.objects.update_or_create(
                nombre_puesto=nombre,
                defaults={'descripcion': desc, 'esta_eliminado': False}
            )
            puestos_map[nombre] = puesto
        self.stdout.write(f'  -> Puestos institucionales: {Puesto.objects.count()} registros.')
        return puestos_map

    def _poblar_personal(self, puestos_map):
        datos_personal = [
            {
                'cui': '2415879632202',
                'nombres': 'Héctor Rolando',
                'apellidos': 'Figueroa Salguero',
                'fecha_nacimiento': date(1976, 4, 14),
                'genero': GeneroChoices.MASCULINO,
                'direccion': '4a. Calle 3-18 Zona 1, Barrio El Centro, El Progreso, Jutiapa',
                'telefono_principal': '54128963',
                'telefono_secundario': '78431250',
                'correo': 'hector.figueroa@ibacoop.edu.gt',
                'puesto': 'Director General',
                'rol': RolChoices.DIRECTOR,
                'nit': '4125896-3',
                'fecha_contratacion': date(2018, 1, 15),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('6200.00'),
                'contrato': 'CONT-IBACOOP-2026-001',
                'ubicacion': 'Archivador A-1, Gaveta 1, Carpeta #01 (Dirección)',
                'emerg_nombre': 'Silvia Patricia Calderón de Figueroa',
                'emerg_tel': '55147892',
                'docs': (True, True, True, True, True, True, True, True),
            },
            {
                'cui': '2536987412202',
                'nombres': 'Claudia Maribel',
                'apellidos': 'Orellana Ruano',
                'fecha_nacimiento': date(1984, 8, 22),
                'genero': GeneroChoices.FEMENINO,
                'direccion': '2a. Avenida 5-40 Zona 2, Colonia Las Brisas, El Progreso, Jutiapa',
                'telefono_principal': '42158796',
                'telefono_secundario': '58741236',
                'correo': 'claudia.orellana@ibacoop.edu.gt',
                'puesto': 'Secretaria de Dirección',
                'rol': RolChoices.SECRETARIA,
                'nit': '5896321-4',
                'fecha_contratacion': date(2020, 1, 10),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('4150.00'),
                'contrato': 'CONT-IBACOOP-2026-002',
                'ubicacion': 'Archivador A-1, Gaveta 1, Carpeta #02 (Secretaría)',
                'emerg_nombre': 'Jorge Mario Orellana Chinchilla',
                'emerg_tel': '41256398',
                'docs': (True, True, True, True, True, True, True, True),
            },
            {
                'cui': '2647895122202',
                'nombres': 'Byron Estuardo',
                'apellidos': 'Castañeda Lemus',
                'fecha_nacimiento': date(1981, 11, 5),
                'genero': GeneroChoices.MASCULINO,
                'direccion': '6a. Calle 1-09 Zona 1, Barrio San José, El Progreso, Jutiapa',
                'telefono_principal': '31458962',
                'telefono_secundario': '78452310',
                'correo': 'byron.castaneda@ibacoop.edu.gt',
                'puesto': 'Contador General',
                'rol': RolChoices.CONTADOR,
                'nit': '6321458-K',
                'fecha_contratacion': date(2019, 2, 1),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('4600.00'),
                'contrato': 'CONT-IBACOOP-2026-003',
                'ubicacion': 'Archivador A-1, Gaveta 1, Carpeta #03 (Contabilidad)',
                'emerg_nombre': 'Glenda Yojana Lemus Portillo',
                'emerg_tel': '52369874',
                'docs': (True, True, True, True, True, True, True, True),
            },
            {
                'cui': '2758963142202',
                'nombres': 'Mynor Alejandro',
                'apellidos': 'Sandoval Recinos',
                'fecha_nacimiento': date(1986, 2, 19),
                'genero': GeneroChoices.MASCULINO,
                'direccion': '3a. Avenida 8-22 Zona 3, Barrio El Calvario, El Progreso, Jutiapa',
                'telefono_principal': '58963214',
                'telefono_secundario': '47851236',
                'correo': 'mynor.sandoval@ibacoop.edu.gt',
                'puesto': 'Docente Guía',
                'rol': RolChoices.DOCENTE,
                'nit': '7412589-6',
                'fecha_contratacion': date(2021, 1, 15),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('4350.00'),
                'contrato': 'CONT-IBACOOP-2026-004',
                'ubicacion': 'Archivador B-1, Gaveta 1, Carpeta #04 (Secretaría)',
                'emerg_nombre': 'Rosa María Recinos Palma',
                'emerg_tel': '56987412',
                'docs': (True, True, True, True, True, True, True, True),
            },
            {
                'cui': '2869541232202',
                'nombres': 'Evelyn Karina',
                'apellidos': 'Galdámez Najera',
                'fecha_nacimiento': date(1989, 7, 11),
                'genero': GeneroChoices.FEMENINO,
                'direccion': '1a. Calle 4-65 Zona 1, El Progreso, Jutiapa',
                'telefono_principal': '45123698',
                'telefono_secundario': '32145698',
                'correo': 'evelyn.galdamez@ibacoop.edu.gt',
                'puesto': 'Docente / Catedrático',
                'rol': RolChoices.DOCENTE,
                'nit': '8523697-1',
                'fecha_contratacion': date(2021, 1, 15),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('4200.00'),
                'contrato': 'CONT-IBACOOP-2026-005',
                'ubicacion': 'Archivador B-1, Gaveta 1, Carpeta #05 (Secretaría)',
                'emerg_nombre': 'Carlos Humberto Galdámez',
                'emerg_tel': '48965231',
                'docs': (True, True, True, True, True, True, True, False),
            },
            {
                'cui': '2974125862202',
                'nombres': 'Sergio Vinicio',
                'apellidos': 'Morales Barrera',
                'fecha_nacimiento': date(1983, 9, 28),
                'genero': GeneroChoices.MASCULINO,
                'direccion': 'Aldea Acequia, Kilómetro 128 Ruta Interamericana, El Progreso, Jutiapa',
                'telefono_principal': '51236987',
                'telefono_secundario': '44587963',
                'correo': 'sergio.morales@ibacoop.edu.gt',
                'puesto': 'Docente Guía',
                'rol': RolChoices.DOCENTE,
                'nit': '9632587-4',
                'fecha_contratacion': date(2020, 1, 16),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('4350.00'),
                'contrato': 'CONT-IBACOOP-2026-006',
                'ubicacion': 'Archivador B-1, Gaveta 1, Carpeta #06 (Secretaría)',
                'emerg_nombre': 'Marta Alicia Barrera Solís',
                'emerg_tel': '53698741',
                'docs': (True, True, True, True, True, True, True, True),
            },
            {
                'cui': '3012547892202',
                'nombres': 'Ingrid Paola',
                'apellidos': 'Aguilar Monterroso',
                'fecha_nacimiento': date(1991, 3, 17),
                'genero': GeneroChoices.FEMENINO,
                'direccion': '5a. Avenida 2-33 Zona 2, Barrio El Porvenir, El Progreso, Jutiapa',
                'telefono_principal': '36985214',
                'telefono_secundario': '57412369',
                'correo': 'ingrid.aguilar@ibacoop.edu.gt',
                'puesto': 'Docente / Catedrático',
                'rol': RolChoices.DOCENTE,
                'nit': '3258741-9',
                'fecha_contratacion': date(2022, 1, 12),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('4100.00'),
                'contrato': 'CONT-IBACOOP-2026-007',
                'ubicacion': 'Archivador B-1, Gaveta 2, Carpeta #07 (Secretaría)',
                'emerg_nombre': 'Luis Fernando Monterroso',
                'emerg_tel': '46325874',
                'docs': (True, True, True, False, True, True, True, True),
            },
            {
                'cui': '3125896472202',
                'nombres': 'Otto René',
                'apellidos': 'Valenzuela Gudiel',
                'fecha_nacimiento': date(1987, 12, 3),
                'genero': GeneroChoices.MASCULINO,
                'direccion': '7a. Calle 6-14 Zona 1, El Progreso, Jutiapa',
                'telefono_principal': '59874123',
                'telefono_secundario': '41236589',
                'correo': 'otto.valenzuela@ibacoop.edu.gt',
                'puesto': 'Encargado de Laboratorio de Computación',
                'rol': RolChoices.DOCENTE,
                'nit': '7539514-2',
                'fecha_contratacion': date(2022, 2, 1),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('4250.00'),
                'contrato': 'CONT-IBACOOP-2026-008',
                'ubicacion': 'Archivador B-1, Gaveta 2, Carpeta #08 (Secretaría)',
                'emerg_nombre': 'Ana Patricia Gudiel de Valenzuela',
                'emerg_tel': '58741239',
                'docs': (True, True, True, True, True, True, True, True),
            },
            {
                'cui': '3236985412202',
                'nombres': 'Lesbia Xiomara',
                'apellidos': 'Chinchilla Vásquez',
                'fecha_nacimiento': date(1990, 5, 25),
                'genero': GeneroChoices.FEMENINO,
                'direccion': 'Colonia San Antonio, Calle Principal Casa #19, El Progreso, Jutiapa',
                'telefono_principal': '47859632',
                'telefono_secundario': '33258964',
                'correo': 'lesbia.chinchilla@ibacoop.edu.gt',
                'puesto': 'Docente Guía',
                'rol': RolChoices.DOCENTE,
                'nit': '8456321-7',
                'fecha_contratacion': date(2023, 1, 10),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('4350.00'),
                'contrato': 'CONT-IBACOOP-2026-009',
                'ubicacion': 'Archivador B-1, Gaveta 2, Carpeta #09 (Secretaría)',
                'emerg_nombre': 'Mario Roberto Vásquez',
                'emerg_tel': '51478963',
                'docs': (True, True, True, True, True, True, True, True),
            },
            {
                'cui': '3347852192202',
                'nombres': 'Edgar Leonel',
                'apellidos': 'MarroquínZepeda',
                'fecha_nacimiento': date(1979, 10, 9),
                'genero': GeneroChoices.MASCULINO,
                'direccion': '2a. Calle 7-11 Zona 3, El Progreso, Jutiapa',
                'telefono_principal': '56321478',
                'telefono_secundario': '48759631',
                'correo': 'edgar.marroquin@ibacoop.edu.gt',
                'puesto': 'Coordinador Académico',
                'rol': RolChoices.DOCENTE,
                'nit': '4987651-8',
                'fecha_contratacion': date(2019, 1, 14),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('4850.00'),
                'contrato': 'CONT-IBACOOP-2026-010',
                'ubicacion': 'Archivador A-1, Gaveta 2, Carpeta #10 (Dirección)',
                'emerg_nombre': 'Norma Elizabeth Zepeda',
                'emerg_tel': '52147896',
                'docs': (True, True, True, True, True, True, True, True),
            },
            {
                'cui': '3458961272202',
                'nombres': 'Silvia Lorena',
                'apellidos': 'Estrada Portillo',
                'fecha_nacimiento': date(1993, 6, 30),
                'genero': GeneroChoices.FEMENINO,
                'direccion': '4a. Avenida 3-28 Zona 1, El Progreso, Jutiapa',
                'telefono_principal': '43258961',
                'telefono_secundario': '59632147',
                'correo': 'silvia.estrada@ibacoop.edu.gt',
                'puesto': 'Auxiliar Administrativo',
                'rol': RolChoices.SECRETARIA,
                'nit': '9517536-5',
                'fecha_contratacion': date(2024, 1, 15),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('3650.00'),
                'contrato': 'CONT-IBACOOP-2026-011',
                'ubicacion': 'Archivador A-1, Gaveta 2, Carpeta #11 (Secretaría)',
                'emerg_nombre': 'Roberto Carlos Portillo',
                'emerg_tel': '47896325',
                'docs': (True, True, False, False, True, True, True, True),
            },
            {
                'cui': '3569874122202',
                'nombres': 'Ramiro Antonio',
                'apellidos': 'Gómez Alarcón',
                'fecha_nacimiento': date(1975, 1, 20),
                'genero': GeneroChoices.MASCULINO,
                'direccion': 'Aldea Las Flores, Sector La Ceiba, El Progreso, Jutiapa',
                'telefono_principal': '57412368',
                'telefono_secundario': '42369874',
                'correo': 'ramiro.gomez@ibacoop.edu.gt',
                'puesto': 'Personal de Servicios / Conserjería',
                'rol': RolChoices.PERSONAL,
                'nit': '2589631-0',
                'fecha_contratacion': date(2018, 3, 1),
                'estado_laboral': EstadoLaboralChoices.ACTIVO,
                'salario': Decimal('3550.00'),
                'contrato': 'CONT-IBACOOP-2026-012',
                'ubicacion': 'Archivador C-1, Gaveta 1, Carpeta #12 (Secretaría)',
                'emerg_nombre': 'Juana Francisca Alarcón',
                'emerg_tel': '58963254',
                'docs': (True, True, False, False, True, True, True, True),
            },
        ]

        # corregir espacio en apellido
        datos_personal[9]['apellidos'] = 'Marroquín Zepeda'

        personal_creado = []
        for item in datos_personal:
            usuario, u_created = Usuario.objects.update_or_create(
                username=item['cui'],
                defaults={
                    'email': item['correo'],
                    'first_name': item['nombres'],
                    'last_name': item['apellidos'],
                    'rol': item['rol'],
                    'is_active': True,
                    'debe_cambiar_password': False,
                }
            )
            if u_created:
                usuario.set_password('Ibacoop2026*')
                usuario.save(update_fields=['password'])

            persona, _ = Persona.objects.update_or_create(
                cui=item['cui'],
                defaults={
                    'usuario': usuario,
                    'nombres': item['nombres'],
                    'apellidos': item['apellidos'],
                    'fecha_nacimiento': item['fecha_nacimiento'],
                    'genero': item['genero'],
                    'direccion': item['direccion'],
                    'telefono_principal': item['telefono_principal'],
                    'telefono_secundario': item['telefono_secundario'],
                    'correo': item['correo'],
                    'esta_eliminado': False,
                }
            )

            d = item['docs']
            personal, _ = Personal.objects.update_or_create(
                persona=persona,
                defaults={
                    'puesto': puestos_map[item['puesto']],
                    'nit': item['nit'],
                    'fecha_contratacion': item['fecha_contratacion'],
                    'estado_laboral': item['estado_laboral'],
                    'salario_base_asignado': item['salario'],
                    'numero_contrato_fisico': item['contrato'],
                    'ubicacion_expediente_fisico': item['ubicacion'],
                    'contacto_emergencia_nombre': item['emerg_nombre'],
                    'contacto_emergencia_telefono': item['emerg_tel'],
                    'doc_dpi_personal': d[0],
                    'doc_nit_sat': d[1],
                    'doc_titulo_academico': d[2],
                    'doc_colegiado_activo': d[3],
                    'doc_antecedentes_penales': d[4],
                    'doc_antecedentes_policiales': d[5],
                    'doc_contrato_fisico': d[6],
                    'doc_tarjeta_salud': d[7],
                    'esta_eliminado': False,
                }
            )
            personal_creado.append(personal)

        self.stdout.write(f'  -> Personal institucional (RRHH): {Personal.objects.count()} colaboradores activos.')
        return personal_creado

    def _poblar_ciclos_y_bloques(self):
        ciclo_2024, _ = CicloEscolar.objects.update_or_create(
            anio=2024,
            defaults={
                'estado_activo': False,
                'fecha_inicio': date(2024, 1, 15),
                'fecha_fin': date(2024, 10, 31),
                'esta_eliminado': False,
            }
        )
        ciclo_2025, _ = CicloEscolar.objects.update_or_create(
            anio=2025,
            defaults={
                'estado_activo': False,
                'fecha_inicio': date(2025, 1, 15),
                'fecha_fin': date(2025, 10, 31),
                'esta_eliminado': False,
            }
        )
        ciclo_2026, _ = CicloEscolar.objects.update_or_create(
            anio=2026,
            defaults={
                'estado_activo': True,
                'fecha_inicio': date(2026, 1, 15),
                'fecha_fin': date(2026, 10, 30),
                'esta_eliminado': False,
            }
        )

        fechas_bimestres = {
            1: ('1° Bimestre', date(2026, 1, 15), date(2026, 3, 20)),
            2: ('2° Bimestre', date(2026, 3, 23), date(2026, 5, 29)),
            3: ('3° Bimestre', date(2026, 6, 1), date(2026, 8, 14)),
            4: ('4° Bimestre', date(2026, 8, 17), date(2026, 10, 30)),
        }

        for c in [ciclo_2024, ciclo_2025]:
            for orden in range(1, 5):
                BloqueAcademico.objects.update_or_create(
                    ciclo_escolar=c,
                    orden=orden,
                    defaults={
                        'nombre_bloque': f'{orden}° Bimestre',
                        'fecha_inicio': date(c.anio, (orden - 1) * 2 + 1, 15),
                        'fecha_fin': date(c.anio, orden * 2 + 2, 20),
                        'esta_eliminado': False,
                    }
                )

        bloques_2026 = {}
        for orden, (nombre, f_ini, f_fin) in fechas_bimestres.items():
            b, _ = BloqueAcademico.objects.update_or_create(
                ciclo_escolar=ciclo_2026,
                orden=orden,
                defaults={
                    'nombre_bloque': nombre,
                    'fecha_inicio': f_ini,
                    'fecha_fin': f_fin,
                    'esta_eliminado': False,
                }
            )
            bloques_2026[orden] = b

        self.stdout.write(f'  -> Ciclos escolares: {CicloEscolar.objects.count()} | Bloques académicos: {BloqueAcademico.objects.count()}.')
        return ciclo_2026, ciclo_2025, bloques_2026

    def _poblar_estructura_academica(self):
        # asegurar los grados del nivel basico
        g1 = Grado.objects.filter(orden=1).first()
        if g1:
            g1.nombre = 'Primero Básico'
            g1.esta_eliminado = False
            g1.save()
        else:
            g1 = Grado.objects.create(nombre='Primero Básico', orden=1)

        g2, _ = Grado.objects.update_or_create(
            nombre='Segundo Básico',
            defaults={'orden': 2, 'esta_eliminado': False}
        )
        g3, _ = Grado.objects.update_or_create(
            nombre='Tercero Básico',
            defaults={'orden': 3, 'esta_eliminado': False}
        )
        grados_map = {1: g1, 2: g2, 3: g3}

        # secciones para cada grado
        secciones_map = {}
        for orden, grado in grados_map.items():
            for letra in ['A', 'B']:
                sec, _ = Seccion.objects.update_or_create(
                    grado=grado,
                    letra=letra,
                    defaults={'cupo_maximo': 35, 'esta_eliminado': False}
                )
                secciones_map[f'{orden}{letra}'] = sec

        # cursos del curriculo nacional base
        datos_cursos = [
            # primero basico
            (g1, 'MAT-101', 'Matemáticas I'),
            (g1, 'CYL-101', 'Comunicación y Lenguaje Idioma Español I'),
            (g1, 'CNT-101', 'Ciencias Naturales I'),
            (g1, 'CSO-101', 'Ciencias Sociales, Formación Ciudadana e Interculturalidad I'),
            (g1, 'ING-101', 'Comunicación y Lenguaje Idioma Extranjero Inglés I'),
            (g1, 'TAC-101', 'Tecnologías del Aprendizaje y la Comunicación I'),
            (g1, 'EMP-101', 'Emprendimiento para la Productividad I'),
            (g1, 'EAR-101', 'Educación Artística I'),
            (g1, 'EFI-101', 'Educación Física I'),
            # segundo basico
            (g2, 'MAT-201', 'Matemáticas II'),
            (g2, 'CYL-201', 'Comunicación y Lenguaje Idioma Español II'),
            (g2, 'CNT-201', 'Ciencias Naturales II'),
            (g2, 'CSO-201', 'Ciencias Sociales, Formación Ciudadana e Interculturalidad II'),
            (g2, 'TAC-201', 'Tecnologías del Aprendizaje y la Comunicación II'),
            (g2, 'EMP-201', 'Emprendimiento para la Productividad II'),
            # tercero basico
            (g3, 'MAT-301', 'Matemáticas III'),
            (g3, 'CYL-301', 'Comunicación y Lenguaje Idioma Español III'),
            (g3, 'CNT-301', 'Ciencias Naturales III'),
            (g3, 'CSO-301', 'Ciencias Sociales, Formación Ciudadana e Interculturalidad III'),
            (g3, 'TAC-301', 'Tecnologías del Aprendizaje y la Comunicación III'),
        ]

        cursos_list = []
        for grado, codigo, nombre in datos_cursos:
            curso, _ = Curso.objects.update_or_create(
                codigo_curso=codigo,
                defaults={
                    'grado': grado,
                    'nombre_curso': nombre,
                    'esta_eliminado': False,
                }
            )
            cursos_list.append(curso)

        self.stdout.write(f'  -> Grados: {Grado.objects.count()} | Secciones: {Seccion.objects.count()} | Cursos CNB: {Curso.objects.count()}.')
        return grados_map, secciones_map, cursos_list

    def _poblar_asignaciones_docentes(self, personal_list, cursos_list, secciones_map, ciclo_2026):
        # filtrar personal con rol docente
        docentes = [p for p in personal_list if p.persona.usuario and p.persona.usuario.rol == RolChoices.DOCENTE]
        if not docentes:
            docentes = personal_list[:5]

        for idx, curso in enumerate(cursos_list):
            docente = docentes[idx % len(docentes)]
            # asignar en la seccion del grado correspondiente
            letra_key = f'{curso.grado.orden}A'
            seccion = secciones_map.get(letra_key)
            if seccion:
                AsignacionDocente.objects.update_or_create(
                    personal=docente,
                    curso=curso,
                    seccion=seccion,
                    ciclo_escolar=ciclo_2026,
                    defaults={'esta_eliminado': False}
                )
        self.stdout.write(f'  -> Asignaciones de carga docente: {AsignacionDocente.objects.count()} registros.')

    def _poblar_planillas(self, personal_list, ciclo_2026, admin_user):
        # generar planillas de sueldos para meses seleccionados
        meses_config = [
            (MesChoices.AGOSTO, date(2026, 8, 31), True),
            (MesChoices.SEPTIEMBRE, date(2026, 9, 30), True),
            (MesChoices.OCTUBRE, date(2026, 10, 30), False),
        ]
        bono_ley = Decimal('250.00')
        for mes, fecha_pago, esta_pagado in meses_config:
            for emp in personal_list[:10]:
                igss = (emp.salario_base_asignado * Decimal('0.0483')).quantize(Decimal('0.01'))
                total = emp.salario_base_asignado + bono_ley - igss
                planilla, created = Planilla.objects.update_or_create(
                    personal=emp,
                    mes_pagado=mes,
                    ciclo_escolar=ciclo_2026,
                    defaults={
                        'bonificaciones': bono_ley,
                        'descuentos': igss,
                        'total_pagar': total,
                        'fecha_pago': fecha_pago if esta_pagado else None,
                        'pagado': esta_pagado,
                        'esta_eliminado': False,
                    }
                )
                if created and esta_pagado:
                    # generar segunda entrada en historial para probar comparativa de auditoria
                    planilla.bonificaciones = bono_ley + Decimal('150.00')
                    planilla.total_pagar = emp.salario_base_asignado + planilla.bonificaciones - igss
                    planilla._change_reason = 'Reconocimiento de horas adicionales en comisión de evaluación bimestral'
                    planilla._history_user = admin_user
                    planilla.save()
        self.stdout.write(f'  -> Planillas de sueldos: {Planilla.objects.count()} registros.')

    def _poblar_encargados(self):
        datos_encargados = [
            ('2145896302202', 'Carlos Humberto', 'Morales Polanco', date(1978, 3, 12), GeneroChoices.MASCULINO, '3a. Calle 4-15 Zona 1, El Progreso, Jutiapa', '54123698', '78451230', 'cmorales.polanco@gmail.com', 'Cooperativa Integral Agrícola El Progreso R.L.'),
            ('2256987412202', 'Rosa María', 'Castillo de Morales', date(1980, 7, 24), GeneroChoices.FEMENINO, '3a. Calle 4-15 Zona 1, El Progreso, Jutiapa', '45896321', '54123698', 'rosamaria.castillo@gmail.com', 'Farmacia Comunitaria San Rafael'),
            ('2369854122202', 'Jorge Luis', 'Hernández Girón', date(1975, 11, 8), GeneroChoices.MASCULINO, 'Aldea Las Flores, Callejón El Mango Casa #8, El Progreso, Jutiapa', '32145896', '58964123', 'jorgeluis.hgiron@gmail.com', 'Transportes Orientales Unidos S.A.'),
            ('2478523692202', 'Miriam Elizabeth', 'Barrios Orellana', date(1982, 5, 19), GeneroChoices.FEMENINO, '5a. Avenida 6-22 Zona 2, Barrio El Calvario, El Progreso, Jutiapa', '56987415', '41258741', 'miriam.barrios82@gmail.com', 'Centro de Salud de El Progreso - MSPAS'),
            ('2589631472202', 'Julio César', 'Estrada Marroquín', date(1974, 9, 3), GeneroChoices.MASCULINO, '1a. Avenida 2-50 Zona 1, Barrio San José, El Progreso, Jutiapa', '47852136', '52364178', 'jc.estrada.m@gmail.com', 'Ferretería y Materiales El Constructor'),
            ('2698741252202', 'Brenda Patricia', 'Salguero Portillo', date(1985, 2, 14), GeneroChoices.FEMENINO, 'Colonia Vista Hermosa Lote 14, El Progreso, Jutiapa', '51236985', '36987412', 'brenda.salguero85@gmail.com', 'Comerciante Individual - Mercado Municipal'),
            ('2741258962202', 'Marco Tulio', 'Recinos Chinchilla', date(1977, 12, 28), GeneroChoices.MASCULINO, '4a. Calle 8-10 Zona 3, El Progreso, Jutiapa', '58741263', '44563218', 'marcotulio.recinos@gmail.com', 'Municipalidad de El Progreso, Jutiapa'),
            ('2852369742202', 'Olga Marina', 'Lemus de Recinos', date(1981, 6, 15), GeneroChoices.FEMENINO, '4a. Calle 8-10 Zona 3, El Progreso, Jutiapa', '42365897', '58741263', 'olgamarina.lemus@gmail.com', 'Panadería y Repostería La Bendición'),
            ('2963258742202', 'Erwin Geovany', 'Najera Ruano', date(1979, 4, 2), GeneroChoices.MASCULINO, 'Aldea Ovejero, Sector Principal, El Progreso, Jutiapa', '33698521', '55412369', 'erwin.najera.r@gmail.com', 'Agroservicios del Oriente S.A.'),
            ('3074125892202', 'Gladys Noemí', 'Solís Gudiel', date(1983, 8, 21), GeneroChoices.FEMENINO, '6a. Avenida 3-44 Zona 2, El Progreso, Jutiapa', '49632587', '57896321', 'gladys.solis.g@gmail.com', 'Agencia Banrural El Progreso'),
            ('3185236972202', 'Víctor Manuel', 'Palma Monterroso', date(1972, 1, 17), GeneroChoices.MASCULINO, '2a. Calle 5-18 Zona 1, El Progreso, Jutiapa', '53214789', '46985214', 'victormanuel.palma@gmail.com', 'Taller Mecánico Automotriz Palma'),
            ('3296325872202', 'Sandra Judith', 'Vásquez Alarcón', date(1986, 10, 11), GeneroChoices.FEMENINO, 'Barrio El Porvenir, Calle Real Casa #27, El Progreso, Jutiapa', '48523691', '31254785', 'sandra.vasquez.a@gmail.com', 'Supermercado La Económica'),
        ]

        encargados_creados = []
        for cui, nom, ape, fnac, gen, direc, tel1, tel2, email, trabajo in datos_encargados:
            usuario, u_created = Usuario.objects.update_or_create(
                username=cui,
                defaults={
                    'email': email,
                    'first_name': nom,
                    'last_name': ape,
                    'rol': RolChoices.ENCARGADO,
                    'is_active': True,
                    'debe_cambiar_password': False,
                }
            )
            if u_created:
                usuario.set_password('Ibacoop2026*')
                usuario.save(update_fields=['password'])

            persona, _ = Persona.objects.update_or_create(
                cui=cui,
                defaults={
                    'usuario': usuario,
                    'nombres': nom,
                    'apellidos': ape,
                    'fecha_nacimiento': fnac,
                    'genero': gen,
                    'direccion': direc,
                    'telefono_principal': tel1,
                    'telefono_secundario': tel2,
                    'correo': email,
                    'esta_eliminado': False,
                }
            )
            encargado, _ = Encargado.objects.update_or_create(
                persona=persona,
                defaults={
                    'lugar_de_trabajo': trabajo,
                    'esta_eliminado': False,
                }
            )
            encargados_creados.append(encargado)

        self.stdout.write(f'  -> Padres de Familia o Encargados: {Encargado.objects.count()} registros.')
        return encargados_creados

    def _poblar_estudiantes_y_relaciones(self, encargados_list):
        # estudiantes con datos realistas para pruebas
        datos_estudiantes = [
            ('3612547892202', 'A482KLP', 'Diego Alejandro', 'Morales Castillo', date(2013, 2, 14), GeneroChoices.MASCULINO, '3a. Calle 4-15 Zona 1, El Progreso, Jutiapa', '54123698', 'diego.morales26@est.ibacoop.edu.gt', 0, ParentescoChoices.PADRE, 'Carlos Humberto Morales Polanco', '54123698', 'Rosa María Castillo de Morales', '45896321', 'Sin alergias conocidas. Tipo de sangre O positivo.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3623658972202', 'B719MNR', 'Valeria Sofía', 'Morales Castillo', date(2011, 6, 20), GeneroChoices.FEMENINO, '3a. Calle 4-15 Zona 1, El Progreso, Jutiapa', '45896321', 'valeria.morales26@est.ibacoop.edu.gt', 1, ParentescoChoices.MADRE, 'Carlos Humberto Morales Polanco', '54123698', 'Rosa María Castillo de Morales', '45896321', 'Uso permanente de lentes oftálmicos para lectura.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3634789652202', 'C305TQV', 'José Andrés', 'Hernández López', date(2013, 5, 11), GeneroChoices.MASCULINO, 'Aldea Las Flores, Callejón El Mango Casa #8, El Progreso, Jutiapa', '32145896', 'jose.hernandez26@est.ibacoop.edu.gt', 2, ParentescoChoices.PADRE, 'Jorge Luis Hernández Girón', '32145896', 'Marta Lidia López de Hernández', '58964123', 'Alergia leve al polvo y cambio de clima.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3645896322202', 'D841WXZ', 'María Fernanda', 'Barrios Orellana', date(2013, 9, 3), GeneroChoices.FEMENINO, '5a. Avenida 6-22 Zona 2, Barrio El Calvario, El Progreso, Jutiapa', '56987415', 'mfernanda.barrios26@est.ibacoop.edu.gt', 3, ParentescoChoices.MADRE, 'Rudy Amílcar Barrios', '41258741', 'Miriam Elizabeth Barrios Orellana', '56987415', 'Ninguna condición médica reportada. Esquema de vacunación completo.', (True, True, True, True, False), EstadoEstudianteChoices.ACTIVO),
            ('3656987412202', 'E592JHK', 'Kevin Estuardo', 'Estrada Portillo', date(2012, 11, 18), GeneroChoices.MASCULINO, '1a. Avenida 2-50 Zona 1, Barrio San José, El Progreso, Jutiapa', '47852136', 'kevin.estrada26@est.ibacoop.edu.gt', 4, ParentescoChoices.PADRE, 'Julio César Estrada Marroquín', '47852136', 'Silvia Portillo de Estrada', '52364178', 'Intolerancia a la lactosa. Tipo de sangre A positivo.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3667896542202', 'F128LMP', 'Ana Lucía', 'Salguero Portillo', date(2013, 4, 7), GeneroChoices.FEMENINO, 'Colonia Vista Hermosa Lote 14, El Progreso, Jutiapa', '51236985', 'analucia.salguero26@est.ibacoop.edu.gt', 5, ParentescoChoices.MADRE, 'Mario René Salguero', '36987412', 'Brenda Patricia Salguero Portillo', '51236985', 'Asma bronquial leve controlada con inhalador.', (True, True, False, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3678965412202', 'G963QRS', 'Cristian Daniel', 'Recinos Lemus', date(2012, 1, 25), GeneroChoices.MASCULINO, '4a. Calle 8-10 Zona 3, El Progreso, Jutiapa', '58741263', 'cristian.recinos26@est.ibacoop.edu.gt', 6, ParentescoChoices.PADRE, 'Marco Tulio Recinos Chinchilla', '58741263', 'Olga Marina Lemus de Recinos', '42365897', 'Sin antecedentes quirúrgicos ni alergias medicamentosas.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3689654122202', 'H471VBN', 'Dulce María', 'Recinos Lemus', date(2010, 8, 12), GeneroChoices.FEMENINO, '4a. Calle 8-10 Zona 3, El Progreso, Jutiapa', '42365897', 'dulce.recinos26@est.ibacoop.edu.gt', 7, ParentescoChoices.MADRE, 'Marco Tulio Recinos Chinchilla', '58741263', 'Olga Marina Lemus de Recinos', '42365897', 'Buena salud general. Participa en selección escolar de atletismo.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3698521472202', 'J635CXZ', 'Brandon Alexander', 'Najera Ruano', date(2012, 3, 29), GeneroChoices.MASCULINO, 'Aldea Ovejero, Sector Principal, El Progreso, Jutiapa', '33698521', 'brandon.najera26@est.ibacoop.edu.gt', 8, ParentescoChoices.PADRE, 'Erwin Geovany Najera Ruano', '33698521', 'Sonia Maribel Ruano', '55412369', 'Alergia a la penicilina registrada en ficha médica.', (True, False, True, True, False), EstadoEstudianteChoices.ACTIVO),
            ('3701254782202', 'K852DFG', 'Fátima Gabriela', 'Solís Gudiel', date(2011, 10, 5), GeneroChoices.FEMENINO, '6a. Avenida 3-44 Zona 2, El Progreso, Jutiapa', '49632587', 'fatima.solis26@est.ibacoop.edu.gt', 9, ParentescoChoices.MADRE, 'Carlos Enrique Solís', '57896321', 'Gladys Noemí Solís Gudiel', '49632587', 'Sin observaciones médicas especiales.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3712365892202', 'L741HJK', 'Luis Fernando', 'Palma Monterroso', date(2010, 12, 16), GeneroChoices.MASCULINO, '2a. Calle 5-18 Zona 1, El Progreso, Jutiapa', '53214789', 'luis.palma26@est.ibacoop.edu.gt', 10, ParentescoChoices.PADRE, 'Víctor Manuel Palma Monterroso', '53214789', 'Elena Monterroso de Palma', '46985214', 'Fractura antigua en muñeca derecha rehabilitada al 100%.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3723698542202', 'M951RTY', 'Andrea Carolina', 'Vásquez Alarcón', date(2011, 7, 22), GeneroChoices.FEMENINO, 'Barrio El Porvenir, Calle Real Casa #27, El Progreso, Jutiapa', '48523691', 'andrea.vasquez26@est.ibacoop.edu.gt', 11, ParentescoChoices.MADRE, 'Juan Antonio Vásquez', '31254785', 'Sandra Judith Vásquez Alarcón', '48523691', 'Tipo de sangre O negativo. Sin alergias.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3734569872202', 'N357UIO', 'Javier Eduardo', 'Chinchilla Orellana', date(2010, 4, 9), GeneroChoices.MASCULINO, '3a. Avenida 9-12 Zona 2, El Progreso, Jutiapa', '41258963', 'javier.chinchilla26@est.ibacoop.edu.gt', 3, ParentescoChoices.TIO, 'Oscar René Chinchilla', '41258963', 'Lilian Orellana de Chinchilla', '52369871', 'Sin afecciones médicas crónicas.', (True, True, True, True, True), EstadoEstudianteChoices.ACTIVO),
            ('3745698712202', 'P258ASD', 'Katerin Yulisa', 'Gómez Salguero', date(2012, 6, 30), GeneroChoices.FEMENINO, 'Aldea Las Flores, Sector Central, El Progreso, Jutiapa', '52369841', 'katerin.gomez26@est.ibacoop.edu.gt', 5, ParentescoChoices.TUTOR, 'Pedro Antonio Gómez', '52369841', 'Celia Salguero', '47896523', 'Pendiente entrega de certificado de grado anterior.', (True, True, False, True, False), EstadoEstudianteChoices.ACTIVO),
            ('3756987412202', 'Q654ZXC', 'Pablo Sebastián', 'Aguilar Lemus', date(2010, 2, 18), GeneroChoices.MASCULINO, '5a. Calle 1-30 Zona 1, El Progreso, Jutiapa', '59632145', 'pablo.aguilar26@est.ibacoop.edu.gt', 7, ParentescoChoices.ABUELO, 'Pablo Aguilar Fajardo', '59632145', 'Cristina Lemus', '43698521', 'Traslado por cambio de domicilio familiar.', (True, True, True, True, True), EstadoEstudianteChoices.RETIRADO),
        ]

        estudiantes_creados = []
        for (cui, cod_min, nom, ape, fnac, gen, direc, tel, email, enc_idx, parentesco,
             nom_p, tel_p, nom_m, tel_m, hist_med, docs, estado_est) in datos_estudiantes:

            usuario, u_created = Usuario.objects.update_or_create(
                username=cui,
                defaults={
                    'email': email,
                    'first_name': nom,
                    'last_name': ape,
                    'rol': RolChoices.ESTUDIANTE,
                    'is_active': estado_est == EstadoEstudianteChoices.ACTIVO,
                    'debe_cambiar_password': False,
                }
            )
            if u_created:
                usuario.set_password('Ibacoop2026*')
                usuario.save(update_fields=['password'])

            persona, _ = Persona.objects.update_or_create(
                cui=cui,
                defaults={
                    'usuario': usuario,
                    'nombres': nom,
                    'apellidos': ape,
                    'fecha_nacimiento': fnac,
                    'genero': gen,
                    'direccion': direc,
                    'telefono_principal': tel,
                    'telefono_secundario': tel_m,
                    'correo': email,
                    'esta_eliminado': False,
                }
            )

            encargado_obj = encargados_list[enc_idx % len(encargados_list)]
            estudiante, _ = Estudiante.objects.update_or_create(
                persona=persona,
                defaults={
                    'codigo_mineduc': cod_min,
                    'estado_estudiante': estado_est,
                    'encargado': encargado_obj,
                    'nombre_padre': nom_p,
                    'telefono_padre': tel_p,
                    'nombre_madre': nom_m,
                    'telefono_madre': tel_m,
                    'historial_medico': hist_med,
                    'doc_cert_nacimiento_renap': docs[0],
                    'doc_dpi_encargado': docs[1],
                    'doc_certificado_grado_anterior': docs[2],
                    'doc_diploma_primaria': docs[3],
                    'doc_codigo_mineduc': docs[4],
                    'estado_activo': estado_est == EstadoEstudianteChoices.ACTIVO,
                    'esta_eliminado': False,
                }
            )
            estudiantes_creados.append(estudiante)

            # crear relacion en la tabla pivote de estudiante y encargado
            EstudianteEncargado.objects.update_or_create(
                estudiante=estudiante,
                encargado=encargado_obj,
                defaults={
                    'parentesco': parentesco,
                    'es_contacto_principal': True,
                    'esta_eliminado': False,
                }
            )

        self.stdout.write(f'  -> Estudiantes inscritos en padrón: {Estudiante.objects.count()} | Relaciones Estudiante-Encargado: {EstudianteEncargado.objects.count()}.')
        return estudiantes_creados

    def _poblar_inscripciones_y_notas(self, estudiantes_list, secciones_map, cursos_list, ciclo_2026, bloques_2026, admin_user):
            # primero basico
        distribucion_secciones = [
            '1A', '2A', '1A', '1A', '2A', '1B', '2A',
            '3A', '2A', '2A', '3A', '3A', '3A', '1B'
        ]
        estudiantes_activos = [e for e in estudiantes_list if e.estado_estudiante == EstadoEstudianteChoices.ACTIVO]

        asignaciones_creadas = []
        for idx, est in enumerate(estudiantes_activos):
            sec_key = distribucion_secciones[idx % len(distribucion_secciones)]
            seccion = secciones_map[sec_key]
            asig, _ = AsignacionEstudiante.objects.update_or_create(
                estudiante=est,
                ciclo_escolar=ciclo_2026,
                defaults={
                    'seccion': seccion,
                    'esta_eliminado': False,
                }
            )
            asignaciones_creadas.append(asig)

            # cursos correspondientes al grado de la seccion
            cursos_grado = [c for c in cursos_list if c.grado_id == seccion.grado_id]

            for c_idx, curso in enumerate(cursos_grado):
                # generar notas para los bimestres del ciclo
                max_bimestre = 4 if idx < 8 else 3
                for orden_bim in range(1, max_bimestre + 1):
                    bloque = bloques_2026[orden_bim]

                    # asignar curso con nota de recuperacion para pruebas
                    if (idx in [4, 8]) and c_idx == 0:
                        zona = Decimal('30.00') + Decimal(str((orden_bim * 2) % 6))
                        examen = Decimal('16.00') + Decimal(str(orden_bim % 5))
                    else:
                        zona = Decimal('42.00') + Decimal(str(((idx * 3 + c_idx * 2 + orden_bim) % 17)))
                        examen = Decimal('25.00') + Decimal(str(((idx * 2 + c_idx + orden_bim) % 14)))

                    nota_b, created = NotaBloque.objects.update_or_create(
                        asignacion_estudiante=asig,
                        curso=curso,
                        bloque_academico=bloque,
                        defaults={
                            'nota_zona': zona,
                            'nota_examen': examen,
                            'esta_eliminado': False,
                        }
                    )
                    # crear modificacion auditada para el panel de diferencias
                    if created and idx < 3 and c_idx == 0 and orden_bim == 1:
                        nota_b.nota_zona = min(zona + Decimal('3.00'), Decimal('60.00'))
                        nota_b._change_reason = 'Revisión de cuadro de actividades de zona autorizada por Coordinación Académica'
                        nota_b._history_user = admin_user
                        nota_b.save()

                # actualizar nota final de curso y ejecutar calculo oficial
                nf, _ = NotaFinalCurso.objects.get_or_create(
                    asignacion_estudiante=asig,
                    curso=curso,
                    defaults={'esta_eliminado': False}
                )
                if idx == 4 and c_idx == 0:
                    nf.nota_recuperacion_1 = Decimal('68.00')
                nf.calcular_nota_final()

        self.stdout.write(
            f'  -> Inscripciones académicas: {AsignacionEstudiante.objects.count()} | '
            f'Notas por bloque: {NotaBloque.objects.count()} | '
            f'Notas finales: {NotaFinalCurso.objects.count()}.'
        )
        return asignaciones_creadas

    def _poblar_asistencia_estudiantil(self, asignaciones_est, cursos_list):
        fechas_clases = [
            date(2026, 10, 5),
            date(2026, 10, 6),
            date(2026, 10, 7),
        ]
        for f_idx, fecha in enumerate(fechas_clases):
            for a_idx, asig in enumerate(asignaciones_est[:12]):
                cursos_grado = [c for c in cursos_list if c.grado_id == asig.seccion.grado_id]
                if not cursos_grado:
                    continue
                curso = cursos_grado[0]

                if f_idx == 1 and a_idx == 2:
                    presente, justificado, obs = False, True, 'Presentó receta médica del Centro de Salud de El Progreso firmada por el encargado.'
                elif f_idx == 2 and a_idx == 5:
                    presente, justificado, obs = False, False, 'Inasistencia sin aviso previo del padre de familia o encargado.'
                else:
                    presente, justificado, obs = True, False, 'Asistencia regular a período de clase.'

                AsistenciaEstudiantil.objects.update_or_create(
                    asignacion_estudiante=asig,
                    curso=curso,
                    fecha=fecha,
                    defaults={
                        'presente': presente,
                        'justificado': justificado,
                        'observaciones': obs,
                        'esta_eliminado': False,
                    }
                )
        self.stdout.write(f'  -> Asistencias estudiantiles: {AsistenciaEstudiantil.objects.count()} registros.')

    def _poblar_conceptos_pago(self):
        datos_conceptos = [
            ('Cuota de Inscripción Escolar Ciclo 2026', Decimal('250.00'), CategoriaConceptoChoices.MATRICULA, True),
            ('Cuota Mensual de Enseñanza', Decimal('175.00'), CategoriaConceptoChoices.COLEGIATURA, False),
            ('Carné Estudiantil y Seguro Escolar Anual', Decimal('65.00'), CategoriaConceptoChoices.SERVICIOS, True),
            ('Guías Didácticas y Folletos CNB', Decimal('120.00'), CategoriaConceptoChoices.MATERIALES, False),
            ('Mantenimiento de Laboratorio de Computación', Decimal('85.00'), CategoriaConceptoChoices.SERVICIOS, False),
            ('Uniforme Oficial de Educación Física', Decimal('180.00'), CategoriaConceptoChoices.MATERIALES, False),
            ('Gira Educativa y Cultural Departamental', Decimal('150.00'), CategoriaConceptoChoices.EVENTOS, False),
            ('Derecho de Cierre y Diploma de Tercero Básico', Decimal('225.00'), CategoriaConceptoChoices.EVENTOS, False),
            ('Certificación General de Estudios MINEDUC', Decimal('35.00'), CategoriaConceptoChoices.SERVICIOS, False),
            ('Aporte de Aniversario del Instituto por Cooperativa', Decimal('50.00'), CategoriaConceptoChoices.GENERAL, False),
        ]
        conceptos_map = {}
        for nombre, monto, cat, aplica_insc in datos_conceptos:
            c, _ = ConceptoPago.objects.update_or_create(
                nombre=nombre,
                defaults={
                    'monto_estandar': monto,
                    'categoria_concepto': cat,
                    'aplica_al_inscribir_seccion': aplica_insc,
                    'esta_eliminado': False,
                }
            )
            conceptos_map[nombre] = c
        self.stdout.write(f'  -> Conceptos de pago: {ConceptoPago.objects.count()} registros.')
        return conceptos_map

    def _poblar_becas(self, estudiantes_list, conceptos_map):
        cuota_mensual = conceptos_map['Cuota Mensual de Enseñanza']
        datos_becas = [
            (0, cuota_mensual, Decimal('25.00'), Decimal('0.00'), 'Descuento por Hijo de Socio Cooperativista Activo (25%)'),
            (1, cuota_mensual, Decimal('25.00'), Decimal('0.00'), 'Convenio Familiar por Hermanos Inscritos en el Instituto (25%)'),
            (2, cuota_mensual, Decimal('50.00'), Decimal('0.00'), 'Media Beca a la Excelencia Académica MINEDUC (Promedio > 90 pts)'),
            (3, None, Decimal('0.00'), Decimal('35.00'), 'Subsidio Municipal de Apoyo a la Educación Básica (Q35.00 fijos)'),
            (5, cuota_mensual, Decimal('20.00'), Decimal('0.00'), 'Convenio de Apoyo Social autorizado por Junta Directiva Cooperativa'),
            (6, cuota_mensual, Decimal('15.00'), Decimal('0.00'), 'Descuento por Pronto Pago Anual y Hermanos Inscritos'),
            (7, cuota_mensual, Decimal('50.00'), Decimal('0.00'), 'Beca Deportiva y Mérito Estudiantil Departamental'),
            (9, cuota_mensual, Decimal('30.00'), Decimal('0.00'), 'Beca Parcial por Rendimiento Destacado en Olimpiadas de Ciencias'),
            (10, None, Decimal('0.00'), Decimal('40.00'), 'Aporte Especial de la Cooperativa de Enseñanza El Progreso'),
            (11, cuota_mensual, Decimal('25.00'), Decimal('0.00'), 'Descuento Institucional para Familias Fundadoras de la Cooperativa'),
        ]
        for est_idx, concepto, porc, fijo, motivo in datos_becas:
            if est_idx < len(estudiantes_list):
                BecaDescuento.objects.update_or_create(
                    estudiante=estudiantes_list[est_idx],
                    motivo_convenio=motivo,
                    defaults={
                        'concepto': concepto,
                        'porcentaje_descuento': porc,
                        'monto_descuento_fijo': fijo,
                        'esta_activo': True,
                        'esta_eliminado': False,
                    }
                )
        self.stdout.write(f'  -> Becas y descuentos: {BecaDescuento.objects.count()} registros.')

    def _poblar_cuentas_y_abonos(self, estudiantes_list, conceptos_map, ciclo_2026, admin_user):
        c_insc = conceptos_map['Cuota de Inscripción Escolar Ciclo 2026']
        c_mens = conceptos_map['Cuota Mensual de Enseñanza']
        c_carne = conceptos_map['Carné Estudiantil y Seguro Escolar Anual']
        c_guias = conceptos_map['Guías Didácticas y Folletos CNB']

        correlativo_boleta = 101

        for idx, est in enumerate(estudiantes_list[:14]):
            # cuenta de inscripcion escolar
            cpc_insc, _ = CuentaPorCobrar.objects.get_or_create(
                estudiante=est,
                concepto=c_insc,
                ciclo_escolar=ciclo_2026,
                defaults={
                    'monto_total': c_insc.monto_estandar,
                    'saldo_pendiente': c_insc.monto_estandar,
                    'fecha_limite_pago': date(2026, 1, 31),
                    'mes_aplicacion': 1,
                    'estado_pago': EstadoPagoChoices.PENDIENTE,
                    'esta_eliminado': False,
                }
            )
            # simular pagos completos y parciales para pruebas de saldo
            if idx < 11:
                num_bol = f'BOL-BI-2026-{correlativo_boleta:05d}'
                correlativo_boleta += 1
                Abono.objects.update_or_create(
                    numero_boleta=num_bol,
                    defaults={
                        'cuenta_por_cobrar': cpc_insc,
                        'monto_pagado': cpc_insc.monto_total,
                        'fecha_pago': date(2026, 1, 18),
                        'observaciones': 'Pago de Cuota de Inscripción Escolar mediante boleta de depósito Banco Industrial.',
                        'esta_eliminado': False,
                    }
                )
            elif idx == 11:
                num_bol = f'BOL-BI-2026-{correlativo_boleta:05d}'
                correlativo_boleta += 1
                Abono.objects.update_or_create(
                    numero_boleta=num_bol,
                    defaults={
                        'cuenta_por_cobrar': cpc_insc,
                        'monto_pagado': Decimal('150.00'),
                        'fecha_pago': date(2026, 1, 22),
                        'observaciones': 'Abono parcial a Cuota de Inscripción Escolar recibido en efectivo en Secretaría.',
                        'esta_eliminado': False,
                    }
                )

            # cuotas mensuales de ensenanza
            for mes_num, f_venc in [(7, date(2026, 7, 10)), (8, date(2026, 8, 10)), (9, date(2026, 9, 10)), (10, date(2026, 10, 10))]:
                # generar variedad de saldos al dia y saldos vencidos
                if mes_num == 7 and idx not in [3, 8, 12]:
                    continue
                cpc_mes, _ = CuentaPorCobrar.objects.get_or_create(
                    estudiante=est,
                    concepto=c_mens,
                    ciclo_escolar=ciclo_2026,
                    mes_aplicacion=mes_num,
                    defaults={
                        'monto_total': c_mens.monto_estandar,
                        'saldo_pendiente': c_mens.monto_estandar,
                        'fecha_limite_pago': f_venc,
                        'estado_pago': EstadoPagoChoices.PENDIENTE,
                        'esta_eliminado': False,
                    }
                )
                if mes_num == 8 and idx < 8:
                    num_bol = f'BOL-BR-2026-{correlativo_boleta:05d}'
                    correlativo_boleta += 1
                    abono_obj, ab_created = Abono.objects.update_or_create(
                        numero_boleta=num_bol,
                        defaults={
                            'cuenta_por_cobrar': cpc_mes,
                            'monto_pagado': cpc_mes.monto_total,
                            'fecha_pago': date(2026, 8, 8),
                            'observaciones': f'Cancelación de Cuota Mensual de agosto en agencia Banrural El Progreso.',
                            'esta_eliminado': False,
                        }
                    )
                    if ab_created and idx < 2:
                        abono_obj.observaciones = 'Cancelación de Cuota Mensual de agosto verificada y conciliada por Contabilidad.'
                        abono_obj._change_reason = 'Conciliación bancaria mensual de boletas Banrural'
                        abono_obj._history_user = admin_user
                        abono_obj.save()
                elif mes_num == 9 and idx < 5:
                    num_bol = f'BOL-BR-2026-{correlativo_boleta:05d}'
                    correlativo_boleta += 1
                    Abono.objects.update_or_create(
                        numero_boleta=num_bol,
                        defaults={
                            'cuenta_por_cobrar': cpc_mes,
                            'monto_pagado': Decimal('100.00'),
                            'fecha_pago': date(2026, 9, 12),
                            'observaciones': 'Pago parcial de Cuota Mensual de septiembre en caja del instituto.',
                            'esta_eliminado': False,
                        }
                    )

            # cobro de guias didacticas para pruebas
            if idx < 6:
                CuentaPorCobrar.objects.get_or_create(
                    estudiante=est,
                    concepto=c_carne if idx % 2 == 0 else c_guias,
                    ciclo_escolar=ciclo_2026,
                    defaults={
                        'monto_total': (c_carne if idx % 2 == 0 else c_guias).monto_estandar,
                        'saldo_pendiente': (c_carne if idx % 2 == 0 else c_guias).monto_estandar,
                        'fecha_limite_pago': date(2026, 6, 15),
                        'estado_pago': EstadoPagoChoices.PENDIENTE,
                        'esta_eliminado': False,
                    }
                )

        self.stdout.write(f'  -> Cuentas por cobrar: {CuentaPorCobrar.objects.count()} | Abonos registrados: {Abono.objects.count()}.')

    def _poblar_inventario(self, admin_user):
        datos_articulos = [
            ('INV-TEC-2026-001', 'Computadora de Escritorio Dell OptiPlex 7010 Core i5', 'Equipo de cómputo con monitor LED de 22 pulgadas, 16GB RAM y SSD 512GB asignado al Laboratorio de Computación.', CategoriaChoices.TECNOLOGIA, 24, 5, 'unidades'),
            ('INV-TEC-2026-002', 'Proyector Multimedia Epson PowerLite E20 3400 Lúmenes', 'Proyector HDMI/VGA para presentaciones audiovisuales en salones de Primero a Tercero Básico.', CategoriaChoices.TECNOLOGIA, 4, 2, 'unidades'),
            ('INV-TEC-2026-003', 'Impresora Multifuncional Epson EcoTank L5290', 'Impresora de tinta continua para emisión de Boletas de Calificaciones y certificaciones en Secretaría.', CategoriaChoices.TECNOLOGIA, 3, 1, 'unidades'),
            ('INV-PAP-2026-004', 'Resma de Papel Bond Tamaño Carta 80 Gramos', 'Papel alcalino de alta blancura para impresión de evaluaciones bimestrales y oficios.', CategoriaChoices.PAPELERIA, 4, 10, 'resmas'),  # alerta stock bajo
            ('INV-PAP-2026-005', 'Caja de Marcadores para Pizarrón Acrílico Recargables', 'Cajas de 12 unidades en colores negro, azul, rojo y verde para uso del personal docente.', CategoriaChoices.PAPELERIA, 3, 8, 'cajas'),   # alerta stock bajo
            ('INV-MOB-2026-006', 'Pupitre Unipersonal con Estructura Metálica y Paleta MDF', 'Escritorio estudiantil ergonómico reforzado para salones del Nivel Básico.', CategoriaChoices.MOBILIARIO, 145, 20, 'unidades'),
            ('INV-MOB-2026-007', 'Cátedra Docente de Metal y Madera con Gaveta Con Llave', 'Escritorio formal para catedráticos ubicado en cada aula de las secciones A y B.', CategoriaChoices.MOBILIARIO, 12, 4, 'unidades'),
            ('INV-MOB-2026-008', 'Pizarrón Acrílico Blanco de 2.40 x 1.20 Metros con Marco de Aluminio', 'Pizarra mural con portaborrador de aluminio instalada en aulas.', CategoriaChoices.MOBILIARIO, 10, 3, 'unidades'),
            ('INV-LIM-2026-009', 'Desinfectante Aromatizante en Galón para Pisos y Aulas', 'Insumo de higienización diaria para conserjería y mantenimiento.', CategoriaChoices.LIMPIEZA, 2, 6, 'galones'),  # alerta stock bajo
            ('INV-DEP-2026-010', 'Balón Oficial de Fútbol y Básquetbol Molten / Mikasa', 'Implementos deportivos para el curso de Educación Física I, II y III.', CategoriaChoices.DEPORTIVO, 18, 5, 'unidades'),
            ('INV-LAB-2026-011', 'Microscopio Compuesto Binocular Educativo LED 1000x', 'Instrumento óptico para prácticas de laboratorio de Ciencias Naturales.', CategoriaChoices.LABORATORIO, 8, 2, 'unidades'),
            ('INV-LIB-2026-012', 'Colección de Guías y Textos del Currículo Nacional Base (MINEDUC)', 'Lote de libros oficiales de Matemáticas, Comunicación y Lenguaje y Ciencias Naturales.', CategoriaChoices.LIBROS, 95, 15, 'unidades'),
        ]

        articulos_creados = []
        for codigo, nombre, desc, cat, stock, stock_min, unidad in datos_articulos:
            art, created = ArticuloInventario.objects.update_or_create(
                codigo_unico=codigo,
                defaults={
                    'nombre': nombre,
                    'descripcion': desc,
                    'categoria': cat,
                    'stock_actual': stock,
                    'stock_minimo_alerta': stock_min,
                    'unidad_medida': unidad,
                    'esta_eliminado': False,
                }
            )
            if created and codigo in ['INV-PAP-2026-004', 'INV-TEC-2026-001']:
                art.descripcion = desc + ' Verificado en inventario físico semestral por Dirección.'
                art._change_reason = 'Verificación de acta de inventario físico institucional'
                art._history_user = admin_user
                art.save()
            articulos_creados.append(art)

        self.stdout.write(f'  -> Artículos de inventario: {ArticuloInventario.objects.count()} registros.')
        return articulos_creados

    def _poblar_movimientos_inventario(self, articulos_list, personal_list):
        datos_movimientos = [
            (0, 7, TipoMovimientoChoices.ENTRADA, 24, 'Recepción de lote de computadoras adquiridas con fondos de la cooperativa y subvención.', 'ACTA-DIR-2026-001'),
            (1, 3, TipoMovimientoChoices.ASIGNACION, 1, 'Entrega de proyector multimedia para clases de Ciencias Naturales en Primero Básico A.', 'VALE-RESG-2026-002'),
            (2, 1, TipoMovimientoChoices.ASIGNACION, 1, 'Asignación de impresora multifuncional a la oficina de Secretaría de Dirección.', 'VALE-RESG-2026-003'),
            (3, 1, TipoMovimientoChoices.ENTRADA, 20, 'Compra trimestral de papel bond tamaño carta según factura autorizada.', 'FACT-SAT-A84512'),
            (3, 4, TipoMovimientoChoices.SALIDA, 16, 'Entrega de resmas de papel a comisión de evaluación para reproducción de exámenes bimestrales.', 'VALE-INT-2026-005'),
            (4, 5, TipoMovimientoChoices.SALIDA, 5, 'Distribución de cajas de marcadores a los Docentes Guía de Primero, Segundo y Tercero Básico.', 'VALE-INT-2026-006'),
            (5, 0, TipoMovimientoChoices.ENTRADA, 30, 'Ingreso de pupitres nuevos fabricados para ampliación de cupo en Primero Básico B.', 'FACT-SAT-B19204'),
            (5, 11, TipoMovimientoChoices.BAJA, 2, 'Descargo de 2 pupitres por daño estructural en soldadura trasladados a bodega de reparación.', 'ACTA-BAJA-2026-007'),
            (8, 11, TipoMovimientoChoices.SALIDA, 6, 'Entrega de galones de desinfectante al personal de conserjería para jornada de limpieza.', 'VALE-CONS-2026-008'),
            (9, 6, TipoMovimientoChoices.ASIGNACION, 8, 'Asignación de balones deportivos para prácticas de Educación Física en cancha polideportiva.', 'VALE-RESG-2026-009'),
            (10, 4, TipoMovimientoChoices.ASIGNACION, 4, 'Resguardo de microscopios binoculares para prácticas de biología celular.', 'VALE-RESG-2026-010'),
            (11, 9, TipoMovimientoChoices.ENTRADA, 95, 'Ingreso de textos educativos enviados por la Dirección Departamental de Educación (DIDEDUC Jutiapa).', 'OFICIO-MINEDUC-045'),
        ]

        ahora = timezone.now()
        for idx, (art_idx, per_idx, tipo, cant, motivo, doc_ref) in enumerate(datos_movimientos):
            articulo = articulos_list[art_idx % len(articulos_list)]
            responsable = personal_list[per_idx % len(personal_list)]
            MovimientoInventario.objects.update_or_create(
                articulo=articulo,
                documento_referencia=doc_ref,
                defaults={
                    'personal_responsable': responsable,
                    'tipo_movimiento': tipo,
                    'cantidad': cant,
                    'fecha': ahora - timedelta(days=20 - idx),
                    'motivo': motivo,
                    'esta_eliminado': False,
                }
            )
        self.stdout.write(f'  -> Movimientos de inventario: {MovimientoInventario.objects.count()} registros.')

    def _poblar_disciplina_y_citaciones(self, estudiantes_list, ciclo_2026, personal_list, admin_user):
        # crear incidentes disciplinarios segun normativa de convivencia
        datos_incidentes = [
            (
                2, date(2026, 8, 14), time(7, 25), 'Entrada Principal del Instituto',
                TipoFaltaChoices.LEVE, CategoriaFaltaChoices.IMPUNTUALIDAD,
                'El estudiante ingresó 25 minutos después del toque de timbre en tres ocasiones consecutivas durante la semana.',
                'El estudiante manifestó que el transporte colectivo proveniente de Aldea Las Flores presentó retrasos por lluvias.',
                'Reflexión formativa verbal con el Docente Guía y compromiso de salir 15 minutos antes de su domicilio.',
                False, True, None
            ),
            (
                3, date(2026, 8, 21), time(9, 10), 'Aula Primero Básico Sección A',
                TipoFaltaChoices.LEVE, CategoriaFaltaChoices.UNIFORME,
                'Asistencia reiterada sin portar el uniforme de diario completo establecido en el reglamento de convivencia.',
                'Indicó que su camisa oficial estaba en reparación y no informó previamente en Secretaría.',
                'Llamado de atención formativo y comunicación telefónica informativa con la madre de familia.',
                True, True,
                (EstadoCitacionChoices.ATENDIDA, 'Verificación de cumplimiento del reglamento de presentación personal', 'La encargada se comprometió a supervisar diariamente la presentación del uniforme escolar.', 'Se constató cumplimiento ejemplar durante las semanas posteriores.', True)
            ),
            (
                4, date(2026, 9, 3), time(10, 40), 'Laboratorio de Computación',
                TipoFaltaChoices.LEVE, CategoriaFaltaChoices.DISPOSITIVO,
                'Uso no autorizado de teléfono celular para videojuegos durante la explicación práctica de hoja de cálculo.',
                'Reconoció que utilizó el dispositivo sin autorización del docente encargado del laboratorio.',
                'Resguardo temporal del dispositivo en Dirección hasta finalizar la jornada escolar y elaboración de ensayo reflexivo.',
                True, True,
                (EstadoCitacionChoices.ATENDIDA, 'Entrega de dispositivo móvil y diálogo sobre uso responsable de tecnología', 'El padre de familia firmó acta de compromiso restringiendo el envío del teléfono celular en días de clase.', 'El estudiante ha mantenido atención plena en el laboratorio.', True)
            ),
            (
                4, date(2026, 9, 18), time(8, 30), 'Aula Segundo Básico Sección A',
                TipoFaltaChoices.LEVE, CategoriaFaltaChoices.DESATENCION,
                'Interrupción constante de la clase de Matemáticas II conversando en voz alta e impidiendo el trabajo de su fila.',
                'Expresó que tenía dudas sobre el tema pero en lugar de preguntar al docente conversó con sus compañeros.',
                'Reubicación estratégica en la primera fila del salón y asignación de tutoría entre pares.',
                False, True, None
            ),
            (
                5, date(2026, 9, 24), time(11, 15), 'Aula Primero Básico Sección B',
                TipoFaltaChoices.GRAVE, CategoriaFaltaChoices.DESHONESTIDAD,
                'Durante la prueba parcial de Ciencias Naturales se detectó el uso de apuntes no autorizados ocultos en el estuche.',
                'Aceptó haber consultado la ficha de resumen por nerviosismo ante la evaluación.',
                'Asignación de trabajo de investigación formativo sobre ética estudiantil y reprogramación supervisada conforme al reglamento de evaluación.',
                True, True,
                (EstadoCitacionChoices.ATENDIDA, 'Notificación de falta grave por deshonestidad académica (Acuerdo Ministerial 01-2011)', 'La madre de familia acordó reforzar el hábito de estudio en casa y supervisar el calendario de evaluaciones.', 'La estudiante entregó su investigación formativa satisfactoriamente.', True)
            ),
            (
                6, date(2026, 9, 29), time(10, 5), 'Cancha Polideportiva Institucional',
                TipoFaltaChoices.LEVE, CategoriaFaltaChoices.FALTA_RESPETO,
                'Discusión acalorada y trato descortés hacia un compañero de sección durante el receso escolar.',
                'Señaló que reaccionó impulsivamente tras una jugada en el partido de fútbol escolar.',
                'Mediación escolar dirigida por la Comisión de Disciplina y disculpa mutua frente al Docente Guía.',
                True, True,
                (EstadoCitacionChoices.ATENDIDA, 'Diálogo formativo sobre convivencia pacífica y manejo de emociones', 'El padre de familia respaldó las medidas formativas de la Comisión de Disciplina.', 'Ambos estudiantes colaboran armónicamente en actividades grupales.', True)
            ),
            (
                8, date(2026, 9, 11), time(9, 50), 'Aula Segundo Básico Sección A',
                TipoFaltaChoices.GRAVE, CategoriaFaltaChoices.DANIO_BIENES,
                'Rayado intencional de la paleta de madera de un pupitre recién entregado al salón de clases.',
                'Admitió haber utilizado marcador permanente sobre la superficie del escritorio.',
                'Jornada formativa de lijado, barnizado y restauración del mobiliario escolar en coordinación con conserjería.',
                True, True,
                (EstadoCitacionChoices.ATENDIDA, 'Citación urgente por daño al patrimonio de la cooperativa de enseñanza', 'El encargado costeó los materiales de barniz y acompañó la entrega del pupitre restaurado.', 'Mobiliario reparado en su totalidad y caso cerrado.', True)
            ),
            (
                8, date(2026, 10, 2), time(11, 30), 'Pasillo del Segundo Nivel',
                TipoFaltaChoices.GRAVE, CategoriaFaltaChoices.AGRESION_VERBAL,
                'Empleo de vocabulario inapropiado y expresiones ofensivas hacia un compañero al finalizar el período de clase.',
                'Manifestó que estaba molesto por un comentario previo pero reconoció que su lenguaje fue incorrecto.',
                'Amonestación escrita en el expediente disciplinario y charla con Orientación Escolar.',
                True, False,
                (EstadoCitacionChoices.PENDIENTE, 'Comparecencia obligatoria ante Dirección y Comisión de Disciplina por reincidencia', '', 'Citación impresa y enviada con el estudiante para firma de recibido.', True)
            ),
            (
                9, date(2026, 10, 5), time(8, 15), 'Aula Segundo Básico Sección A',
                TipoFaltaChoices.LEVE, CategoriaFaltaChoices.IMPUNTUALIDAD,
                'Ingreso tardío al salón después del toque de timbre de finalización de recreo.',
                'Explicó que permaneció en la librería escolar adquiriendo hojas de cuadrícula.',
                'Recomendación verbal de adquirir sus materiales antes del inicio de la jornada.',
                False, True, None
            ),
            (
                10, date(2026, 10, 6), time(12, 10), 'Aula Tercero Básico Sección A',
                TipoFaltaChoices.LEVE, CategoriaFaltaChoices.DESATENCION,
                'Incumplimiento en la presentación del cuaderno de trabajo de Emprendimiento para la Productividad.',
                'Indicó que dejó el cuaderno olvidado en su mesa de estudio en casa.',
                'Compromiso de presentar las actividades completas al día siguiente a primera hora.',
                True, False,
                (EstadoCitacionChoices.REPROGRAMADA, 'Revisión conjunta de avance de tareas del cuarto bimestre', '', 'El padre de familia solicitó reprogramar la reunión por motivos laborales en su taller.', True)
            ),
            (
                12, date(2026, 10, 7), time(10, 20), 'Patio Central del Instituto',
                TipoFaltaChoices.GRAVE, CategoriaFaltaChoices.FALTA_RESPETO,
                'Desatención a las indicaciones preventivas del docente de turno durante el simulacro de evacuación escolar.',
                'Reconoció que no tomó con la debida seriedad el ejercicio de prevención de desastres.',
                'Asignación de exposición formativa sobre protocolos de seguridad escolar CONRED ante su sección.',
                True, False,
                (EstadoCitacionChoices.NO_ASISTIO, 'Reunión con Comisión de Disciplina por actitud durante simulacro escolar', '', 'El encargado no se presentó en la hora programada; se enviará segunda convocatoria.', True)
            ),
            (
                13, date(2026, 10, 8), time(9, 0), 'Aula Primero Básico Sección B',
                TipoFaltaChoices.LEVE, CategoriaFaltaChoices.UNIFORME,
                'Portación de calzado distinto al reglamentario sin aviso escrito del encargado.',
                'Informó que su calzado escolar sufrió desperfecto el día anterior.',
                'Plazo de tres días hábiles otorgado por Coordinación Académica para solventar la situación.',
                True, False,
                (EstadoCitacionChoices.PENDIENTE, 'Entrevista informativa y actualización de expediente físico pendiente', '', 'Pendiente de atención en la presente semana.', True)
            ),
        ]

        tz = timezone.get_current_timezone()
        for idx, (est_idx, fecha, hora, lugar, tipo, cat, hechos, descargo, medida, req_cit, resuelto, cit_data) in enumerate(datos_incidentes):
            if est_idx >= len(estudiantes_list):
                continue
            est = estudiantes_list[est_idx]
            docente_user = personal_list[(idx + 3) % len(personal_list)].persona.usuario or admin_user

            incidente, inc_created = IncidenteDisciplinario.objects.update_or_create(
                estudiante=est,
                ciclo_escolar=ciclo_2026,
                fecha=fecha,
                categoria=cat,
                defaults={
                    'reportado_por': docente_user,
                    'hora': hora,
                    'lugar': lugar,
                    'tipo_falta': tipo,
                    'descripcion_hechos': hechos,
                    'descargo_estudiante': descargo,
                    'medida_formativa': medida,
                    'requiere_citacion': req_cit,
                    'esta_resuelto': resuelto,
                    'esta_eliminado': False,
                }
            )
            if inc_created and resuelto and idx < 2:
                incidente.medida_formativa = medida + ' (Seguimiento completado favorablemente por el Docente Guía).'
                incidente._change_reason = 'Cierre de seguimiento pedagógico de la Comisión de Disciplina'
                incidente._history_user = admin_user
                incidente.save()

            if cit_data:
                estado_cit, motivo_cit, acuerdos, obs_seg, notif = cit_data
                dt_cit = timezone.make_aware(datetime.combine(fecha + timedelta(days=2), time(8, 30)), tz)
                CitacionPadre.objects.update_or_create(
                    incidente=incidente,
                    defaults={
                        'fecha_hora_citacion': dt_cit,
                        'motivo_citacion': motivo_cit,
                        'lugar': 'Dirección / Comisión de Disciplina y Convivencia',
                        'atendido_por': admin_user,
                        'estado': estado_cit,
                        'acuerdos_alcanzados': acuerdos,
                        'observaciones_seguimiento': obs_seg,
                        'notificacion_enviada': notif,
                        'esta_eliminado': False,
                    }
                )

        self.stdout.write(
            f'  -> Incidentes disciplinarios: {IncidenteDisciplinario.objects.count()} | '
            f'Citaciones a padres de familia: {CitacionPadre.objects.count()}.'
        )

    def _poblar_portal_web(self, admin_user):
        ahora = timezone.now()
        datos_contenidos = [
            (
                SeccionPortalChoices.NOTICIAS,
                'Apertura del Proceso de Inscripción Ordinaria para el Ciclo Escolar 2026',
                'La Junta Directiva y Dirección del Instituto de Educación Básica por Cooperativa El Progreso informan a los padres de familia o encargados de la comunidad que ya se encuentra habilitada la recepción de expedientes de inscripción para Primero, Segundo y Tercero Básico.',
                True, 15
            ),
            (
                SeccionPortalChoices.NOTICIAS,
                'Estudiantes de Tercero Básico Destacan en Feria Científica Departamental en Jutiapa',
                'Con proyectos enfocados en energías limpias y conservación hídrica en el oriente del país, las delegaciones estudiantiles de nuestras secciones A y B obtuvieron el primer lugar a nivel departamental.',
                True, 12
            ),
            (
                SeccionPortalChoices.HISTORIA,
                'Fundación y Trayectoria del Instituto por Cooperativa de Enseñanza El Progreso',
                'Fundado al amparo de la Ley de Institutos de Educación por Cooperativa de Enseñanza (Decreto Ley 17-95), nuestro centro educativo nació gracias al esfuerzo tripartito entre el Ministerio de Educación (MINEDUC), la Municipalidad de El Progreso y los padres de familia organizados en cooperativa.',
                True, 60
            ),
            (
                SeccionPortalChoices.HISTORIA,
                'Compromiso Cooperativo con la Excelencia Académica en el Oriente de Guatemala',
                'A lo largo de más de dos décadas de servicio educativo ininterrumpido, el instituto ha formado a generaciones de jóvenes íntegros bajo los lineamientos del Currículo Nacional Base (CNB).',
                True, 45
            ),
            (
                SeccionPortalChoices.OFERTA,
                'Pensum Oficial del Ciclo de Educación Básica (Primero, Segundo y Tercero Básico)',
                'Impartimos las áreas curriculares oficiales del MINEDUC: Matemáticas, Comunicación y Lenguaje (Español e Inglés), Ciencias Naturales, Ciencias Sociales y Formación Ciudadana, Tecnologías del Aprendizaje y la Comunicación (TAC), Emprendimiento para la Productividad, Educación Artística y Educación Física.',
                True, 30
            ),
            (
                SeccionPortalChoices.OFERTA,
                'Laboratorio de Computación Modernizado y Programa de Becas Cooperativas',
                'Nuestros estudiantes cuentan con acceso semanal a equipo de cómputo actualizado y programas de becas parciales por excelencia académica y apoyo a hijos de cooperativistas activos.',
                True, 25
            ),
            (
                SeccionPortalChoices.COMUNICADOS,
                'Calendario Oficial de Evaluaciones del Cuarto Bimestre y Entrega de Boletas de Calificaciones',
                'Se comunica a todos los padres de familia o encargados que las evaluaciones finales de bloque se realizarán en la tercera semana de octubre. Para la entrega de la Boleta de Calificaciones es indispensable encontrarse solvente en la Cuota Mensual de Enseñanza.',
                True, 8
            ),
            (
                SeccionPortalChoices.COMUNICADOS,
                'Disposiciones sobre Convivencia Pacífica y Uso Correcto del Uniforme Escolar',
                'De conformidad con el Acuerdo Ministerial 01-2011 del MINEDUC, se recuerda a los estudiantes y encargados la importancia de la puntualidad en el horario de ingreso (13:00 horas) y el porte adecuado del uniforme institucional.',
                True, 6
            ),
            (
                SeccionPortalChoices.EVENTOS,
                'Asamblea General Ordinaria de Padres de Familia y Socios de la Cooperativa',
                'Se convoca cordialmente a todos los padres de familia o encargados inscritos en el presente ciclo escolar a participar en la Asamblea General Informativa en el salón de usos múltiples del instituto.',
                True, 4
            ),
            (
                SeccionPortalChoices.EVENTOS,
                'Tarde Deportiva Intersecciones y Celebración de Aniversario Institucional',
                'Actividades deportivas de fútbol, básquetbol y atletismo con la participación de los Docentes Guía y todas las secciones de Primero, Segundo y Tercero Básico.',
                True, 3
            ),
            (
                SeccionPortalChoices.GALERIA,
                'Inauguración de Nuevas Estaciones en el Laboratorio de Tecnologías del Aprendizaje',
                'Registro fotográfico de la entrega de 24 equipos de cómputo de última generación para el fortalecimiento de las competencias digitales de nuestros estudiantes.',
                True, 10
            ),
            (
                SeccionPortalChoices.GALERIA,
                'Acto Cívico de Independencia Patria y Desfile Escolar en El Progreso',
                'Participación destacada de la banda escolar, cuadro de excelencia académica y cuerpo docente durante las fiestas cívicas de septiembre.',
                True, 20
            ),
        ]

        for seccion, titulo, cuerpo, pub, dias_atras in datos_contenidos:
            ContenidoWeb.objects.update_or_create(
                titulo=titulo,
                defaults={
                    'seccion': seccion,
                    'cuerpo': cuerpo,
                    'fecha_publicacion': ahora - timedelta(days=dias_atras),
                    'publicado': pub,
                    'autor': admin_user,
                    'esta_eliminado': False,
                }
            )

        datos_solicitudes = [
            ('Mario Roberto Gudiel Samayoa', 'mario.gudiel79@gmail.com', '54128974', 'Requisitos de inscripción para Primero Básico 2027', 'Buen día, deseo conocer los requisitos de papelería del MINEDUC y el valor de la cuota de inscripción escolar y cuota mensual para inscribir a mi hijo en Primero Básico.', True, 'Se brindó información detallada vía telefónica y se envió listado de los 5 documentos obligatorios RENAP/MINEDUC por correo.'),
            ('Silvia Esperanza Ruano de Paz', 'silvia.ruano.paz@gmail.com', '42369871', 'Consulta sobre traslado de estudiante a Segundo Básico', 'Estimados señores de Secretaría, nos mudaremos al municipio de El Progreso el próximo mes y deseamos consultar disponibilidad de cupo en Segundo Básico.', True, 'Secretaría confirmó disponibilidad en Sección B y agendó cita presencial para revisión de certificados.'),
            ('Juan Carlos Portillo Salguero', 'jcportillo.sal@gmail.com', '31458796', 'Información sobre becas y descuentos por hermanos', 'Tengo dos hijos que ingresarán a Primero y Tercero Básico; quisiera saber si el instituto por cooperativa cuenta con descuento familiar en la cuota mensual.', True, 'Contabilidad explicó el convenio de descuento familiar y requisitos para solicitud ante Junta Directiva.'),
            ('Flor de María Orellana Chinchilla', 'flormaria.orellana@gmail.com', '58963210', 'Horario de atención en Secretaría y Contabilidad', 'Por favor me podrían indicar el horario de atención para realizar el pago de cuota mensual y recoger una certificación de estudios.', True, 'Se respondió que el horario de atención es de lunes a viernes de 13:00 a 18:00 horas.'),
            ('Luis Alberto Castañeda Morales', 'luis.castaneda.m@gmail.com', '47851239', 'Solicitud de constancia de código personal SIRE MINEDUC', 'Soy encargado de un estudiante de Primero Básico y necesito orientación sobre la constancia de código personal solicitada en el expediente.', True, 'Se verificó en el sistema SIRE y se adjuntó la constancia al expediente físico del estudiante.'),
            ('Patricia Elizabeth Najera Lemus', 'patricia.najera84@gmail.com', '51236984', 'Consulta sobre uniforme de diario y educación física', 'Quisiera consultar dónde se adquiere el uniforme de educación física oficial del instituto y qué días les corresponde portarlo.', True, 'Se informó el horario de Educación Física de cada sección y costos establecidos en el catálogo.'),
            ('Oscar Armando Barrientos Solís', 'oscar.barrientos@gmail.com', '36985217', 'Fechas de pruebas de recuperación de fin de ciclo', 'Deseo conocer las fechas programadas por Coordinación Académica para la primera oportunidad de recuperación.', False, ''),
            ('Evelyn Yojana Vásquez Palma', 'evelyn.vasquez.p@gmail.com', '49632581', 'Información de inscripción para nuevo ingreso', 'Me interesa inscribir a mi hija que actualmente cursa sexto primaria en la Escuela Oficial Urbana Mixta; ¿cuándo inician las inscripciones?', False, ''),
            ('Rudy Estuardo Marroquín Girón', 'rudy.marroquin.g@gmail.com', '55412368', 'Confirmación de boleta de depósito bancario', 'Realicé el pago de la cuota mensual de octubre en agencia Banrural y deseo saber cuándo puedo pasar por mi recibo en Secretaría.', False, ''),
            ('Glenda Karina Monterroso Zepeda', 'glenda.monterroso@gmail.com', '43258967', 'Solicitud de cita con el Docente Guía de Primero Básico A', 'Me gustaría coordinar una breve reunión con el Docente Guía para conversar sobre el rendimiento académico de mi hijo en Matemáticas I.', False, ''),
            ('Héctor David Alarcón Recinos', 'hector.alarcon.r@gmail.com', '57412360', 'Consulta sobre actividades de clausura de Tercero Básico', 'Como padre de familia de Tercero Básico Sección A, quisiera consultar la fecha del acto de entrega de diplomas de cierre de ciclo básico.', False, ''),
            ('Norma Lidia Calderón Barrios', 'norma.calderon.b@gmail.com', '41258746', 'Felicitación al personal docente del instituto', 'Agradezco el excelente acompañamiento pedagógico y humano que los docentes han brindado a los estudiantes durante el presente ciclo escolar.', True, 'Mensaje trasladado a Dirección y compartido en claustro de catedráticos.'),
        ]

        for nombre_rem, correo, tel, asunto, mensaje, atendido, notas in datos_solicitudes:
            SolicitudContacto.objects.update_or_create(
                correo=correo,
                asunto=asunto,
                defaults={
                    'nombre_remitente': nombre_rem,
                    'telefono': tel,
                    'mensaje': mensaje,
                    'atendido': atendido,
                    'notas_seguimiento': notas,
                    'esta_eliminado': False,
                }
            )

        self.stdout.write(
            f'  -> Contenidos del portal web: {ContenidoWeb.objects.count()} | '
            f'Solicitudes de contacto: {SolicitudContacto.objects.count()}.'
        )
