from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from APPS.usuarios.models import Usuario
from APPS.academico.models import CicloEscolar, Grado, Seccion, Curso, AsignacionEstudiante, BloqueAcademico, NotaBloque
from APPS.estudiantes.models import Estudiante, Persona
from APPS.inventario.models import ArticuloInventario
from APPS.rrhh.models import Personal, Puesto, Planilla


class ReportesPermisosTestCase(TestCase):
    def setUp(self):
        self.admin_user = Usuario.objects.create_user(
            username='admin_reportes',
            email='admin_rep@ibacoop.edu.gt',
            password='Password123!',
            rol='ADMINISTRADOR',
            debe_cambiar_password=False,
        )
        self.docente_user = Usuario.objects.create_user(
            username='docente_reportes',
            email='docente_rep@ibacoop.edu.gt',
            password='Password123!',
            rol='DOCENTE',
            debe_cambiar_password=False,
        )

    def test_docente_no_accede_a_hub_reportes(self):
        """Un usuario docente sin permisos directivos no puede acceder al Hub de Reportes."""
        self.client.force_login(self.docente_user)
        response = self.client.get(reverse('reportes:hub'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

    def test_administrador_accede_a_hub_reportes(self):
        """Un usuario Administrador accede exitosamente al Hub de Reportes (HTTP 200)."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('reportes:hub'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reportes/panel.html')


class ReportesEmisionTestCase(TestCase):
    def setUp(self):
        self.director_user = Usuario.objects.create_user(
            username='director_rep',
            email='director_rep@ibacoop.edu.gt',
            password='Password123!',
            rol='DIRECTOR',
            debe_cambiar_password=False,
        )
        self.client.force_login(self.director_user)

        self.ciclo = CicloEscolar.objects.create(
            anio=2026,
            estado_activo=True
        )
        self.grado = Grado.objects.create(nombre="Primero Básico Rep", orden=1)
        self.seccion = Seccion.objects.create(grado=self.grado, letra="A", cupo_maximo=30)
        self.curso = Curso.objects.create(nombre_curso="Matemáticas I", grado=self.grado)
        self.bloque = BloqueAcademico.objects.create(ciclo_escolar=self.ciclo, nombre_bloque="Bloque 1", orden=1)

        self.persona = Persona.objects.create(
            cui="1234567890101",
            nombres="Pedro",
            apellidos="Picapiedra",
            telefono_principal="55551234"
        )
        self.estudiante = Estudiante.objects.create(
            persona=self.persona,
            codigo_mineduc="PED123456"
        )
        self.asignacion = AsignacionEstudiante.objects.create(
            estudiante=self.estudiante,
            seccion=self.seccion,
            ciclo_escolar=self.ciclo
        )
        self.nota = NotaBloque.objects.create(
            asignacion_estudiante=self.asignacion,
            curso=self.curso,
            bloque_academico=self.bloque,
            nota_zona=Decimal(50),
            nota_examen=Decimal(35)
        )

        self.articulo = ArticuloInventario.objects.create(
            codigo_unico='REP-INV-001',
            nombre='Proyector Epson',
            categoria='TECNOLOGIA',
            stock_actual=4,
            stock_minimo_alerta=1,
            unidad_medida='unidades'
        )


    def test_generar_boleta_calificaciones_pdf(self):
        """Verifica la generación de la boleta oficial de notas en PDF."""
        url = reverse('reportes:academico_boleta_pdf', kwargs={
            'estudiante_id': self.estudiante.persona_id,
            'ciclo_id': self.ciclo.id
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(len(response.content) > 1000)

    def test_generar_antiguedad_saldos_pdf_y_csv(self):
        """Verifica la generación del reporte de antigüedad de saldos en PDF y CSV."""
        url_pdf = reverse('reportes:financiero_antiguedad') + f"?formato=pdf&ciclo_id={self.ciclo.id}"
        response_pdf = self.client.get(url_pdf)
        self.assertEqual(response_pdf.status_code, 200)
        self.assertEqual(response_pdf['Content-Type'], 'application/pdf')

        url_csv = reverse('reportes:financiero_antiguedad') + f"?formato=csv&ciclo_id={self.ciclo.id}"
        response_csv = self.client.get(url_csv)
        self.assertEqual(response_csv.status_code, 200)
        self.assertEqual(response_csv['Content-Type'], 'text/csv; charset=utf-8')

    def test_generar_inventario_pdf_y_csv(self):
        """Verifica la generación del reporte de inventario físico en PDF y CSV."""
        url_pdf = reverse('reportes:inventario_valorado') + "?formato=pdf"
        response_pdf = self.client.get(url_pdf)
        self.assertEqual(response_pdf.status_code, 200)
        self.assertEqual(response_pdf['Content-Type'], 'application/pdf')

        url_csv = reverse('reportes:inventario_valorado') + "?formato=csv"
        response_csv = self.client.get(url_csv)
        self.assertEqual(response_csv.status_code, 200)
        self.assertEqual(response_csv['Content-Type'], 'text/csv; charset=utf-8')


class GeneracionBoletasZipTestCase(TestCase):
    def setUp(self):
        self.director_user = Usuario.objects.create_user(
            username='director_reportes',
            email='director_reportes@ibacoop.edu.gt',
            password='Password123!',
            rol='DIRECTOR',
            debe_cambiar_password=False,
        )
        self.client.force_login(self.director_user)

        self.ciclo = CicloEscolar.objects.create(
            anio=2026,
            estado_activo=True
        )
        self.grado = Grado.objects.create(nombre="Segundo Básico", orden=2)
        self.seccion = Seccion.objects.create(grado=self.grado, letra="B", cupo_maximo=25)
        self.curso = Curso.objects.create(nombre_curso="Ciencias Naturales", grado=self.grado)
        self.bloque = BloqueAcademico.objects.create(ciclo_escolar=self.ciclo, nombre_bloque="Bloque 1", orden=1)

        self.persona = Persona.objects.create(
            cui="9876543210101",
            nombres="Maria",
            apellidos="Lopez",
            telefono_principal="44445555"
        )
        self.estudiante = Estudiante.objects.create(
            persona=self.persona,
            codigo_mineduc="MAR987654"
        )
        self.asignacion = AsignacionEstudiante.objects.create(
            estudiante=self.estudiante,
            seccion=self.seccion,
            ciclo_escolar=self.ciclo
        )
        self.nota = NotaBloque.objects.create(
            asignacion_estudiante=self.asignacion,
            curso=self.curso,
            bloque_academico=self.bloque,
            nota_zona=Decimal(55),
            nota_examen=Decimal(40)
        )

    def test_tarea_generar_boletas_zip(self):
        """Verifica la generación de boletas en archivo ZIP y actualización de estado en caché."""
        from APPS.reportes.tareas import generar_boletas_seccion_zip, obtener_estado_tarea
        resultado = generar_boletas_seccion_zip('test-task-1', self.seccion.id, self.ciclo.id)

        self.assertEqual(resultado['status'], 'COMPLETADO')
        self.assertEqual(resultado['total'], 1)
        self.assertIn('.zip', resultado['filename'])
        self.assertTrue(resultado['archivo_url'].startswith('/media/reportes_lotes/'))

        estado = obtener_estado_tarea('test-task-1')
        self.assertEqual(estado['state'], 'SUCCESS')
        self.assertEqual(estado['percent'], 100)

    def test_endpoint_iniciar_descarga_boletas_zip(self):
        """Verifica que la vista POST inicie la tarea asíncrona y devuelva un task_id en JSON."""
        url = reverse('reportes:boletas_zip_iniciar')
        response = self.client.post(url, {
            'seccion_id': self.seccion.id,
            'ciclo_id': self.ciclo.id
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('task_id', data)

    def test_endpoint_consultar_estado_tarea(self):
        """Verifica que el endpoint de sondeo devuelva el estado de la tarea en JSON."""
        url = reverse('reportes:tarea_estado', kwargs={'task_id': 'tarea-demo-uuid-123'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['task_id'], 'tarea-demo-uuid-123')
        self.assertIn('state', data)

