from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from APPS.usuarios.models import Usuario
from APPS.academico.models import CicloEscolar, Grado, Seccion, Curso, AsignacionEstudiante, BloqueAcademico, NotaBloque
from APPS.estudiantes.models import Estudiante, Persona
from APPS.financiero.models import ConceptoPago, CuentaPorCobrar, Abono, BecaDescuento, MetodoPagoChoices, CategoriaConceptoChoices
from APPS.inventario.models import ArticuloInventario
from APPS.rrhh.models import Personal, Puesto, Planilla, TipoPlanillaChoices, MesChoices
from APPS.disciplina.models import IncidenteDisciplinario, TipoFaltaChoices, CategoriaFaltaChoices


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

    def test_generar_cuadro_calificaciones_pdf_y_csv(self):
        """Verifica el Cuadro General de Calificaciones por Sección en PDF y CSV."""
        url_pdf = reverse('reportes:academico_cuadro_calificaciones') + f"?seccion_id={self.seccion.id}&ciclo_id={self.ciclo.id}&bloque_id={self.bloque.id}&formato=pdf"
        response_pdf = self.client.get(url_pdf)
        self.assertEqual(response_pdf.status_code, 200)
        self.assertEqual(response_pdf['Content-Type'], 'application/pdf')

        url_csv = reverse('reportes:academico_cuadro_calificaciones') + f"?seccion_id={self.seccion.id}&ciclo_id={self.ciclo.id}&bloque_id={self.bloque.id}&formato=csv"
        response_csv = self.client.get(url_csv)
        self.assertEqual(response_csv.status_code, 200)
        self.assertEqual(response_csv['Content-Type'], 'text/csv; charset=utf-8')

    def test_generar_cuadro_honor_pdf_y_csv(self):
        """Verifica el Cuadro de Honor Estudiantil en PDF y CSV."""
        url_pdf = reverse('reportes:academico_cuadro_honor') + f"?seccion_id={self.seccion.id}&ciclo_id={self.ciclo.id}&bloque_id={self.bloque.id}&formato=pdf"
        response_pdf = self.client.get(url_pdf)
        self.assertEqual(response_pdf.status_code, 200)
        self.assertEqual(response_pdf['Content-Type'], 'application/pdf')

        url_csv = reverse('reportes:academico_cuadro_honor') + f"?seccion_id={self.seccion.id}&ciclo_id={self.ciclo.id}&bloque_id={self.bloque.id}&formato=csv"
        response_csv = self.client.get(url_csv)
        self.assertEqual(response_csv.status_code, 200)
        self.assertEqual(response_csv['Content-Type'], 'text/csv; charset=utf-8')

    def test_generar_listado_estudiantes_pdf_y_csv(self):
        """Verifica el Listado Oficial de Estudiantes Inscritos en PDF y CSV."""
        url_pdf = reverse('reportes:academico_listado_estudiantes') + f"?seccion_id={self.seccion.id}&ciclo_id={self.ciclo.id}&formato=pdf"
        response_pdf = self.client.get(url_pdf)
        self.assertEqual(response_pdf.status_code, 200)
        self.assertEqual(response_pdf['Content-Type'], 'application/pdf')

        url_csv = reverse('reportes:academico_listado_estudiantes') + f"?seccion_id={self.seccion.id}&ciclo_id={self.ciclo.id}&formato=csv"
        response_csv = self.client.get(url_csv)
        self.assertEqual(response_csv.status_code, 200)
        self.assertEqual(response_csv['Content-Type'], 'text/csv; charset=utf-8')

    def test_generar_constancia_inscripcion_pdf(self):
        """Verifica la Constancia Oficial de Inscripción en PDF."""
        url = reverse('reportes:academico_constancia_inscripcion') + f"?estudiante_id={self.estudiante.pk}&ciclo_id={self.ciclo.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_generar_alertas_tempranas_csv(self):
        """Verifica la exportación CSV de alertas tempranas académicas."""
        url = reverse('reportes:academico_alertas') + f"?seccion_id={self.seccion.id}&ciclo_id={self.ciclo.id}&bloque_id={self.bloque.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

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

    def test_generar_cuadre_caja_pdf_y_csv(self):
        """Verifica el Cuadre Diario de Caja en PDF y CSV."""
        hoy = timezone.now().date()
        concepto = ConceptoPago.objects.create(
            nombre="Cuota Enero Test",
            monto_estandar=Decimal("200.00"),
            categoria_concepto=CategoriaConceptoChoices.COLEGIATURA
        )
        cpc = CuentaPorCobrar.objects.create(
            estudiante=self.estudiante,
            concepto=concepto,
            ciclo_escolar=self.ciclo,
            monto_total=Decimal("200.00"),
            fecha_limite_pago=hoy
        )
        Abono.objects.create(
            cuenta_por_cobrar=cpc,
            metodo_pago=MetodoPagoChoices.EFECTIVO,
            monto_pagado=Decimal("200.00"),
            fecha_pago=hoy,
            numero_boleta="BOL-001"
        )

        url_pdf = reverse('reportes:financiero_cuadre_caja') + f"?fecha_inicio={hoy}&fecha_fin={hoy}&formato=pdf"
        response_pdf = self.client.get(url_pdf)
        self.assertEqual(response_pdf.status_code, 200)
        self.assertEqual(response_pdf['Content-Type'], 'application/pdf')

        url_csv = reverse('reportes:financiero_cuadre_caja') + f"?fecha_inicio={hoy}&fecha_fin={hoy}&formato=csv"
        response_csv = self.client.get(url_csv)
        self.assertEqual(response_csv.status_code, 200)
        self.assertEqual(response_csv['Content-Type'], 'text/csv; charset=utf-8')

    def test_generar_estado_cuenta_estudiante_pdf(self):
        """Verifica el Estado de Cuenta / Solvencia Estudiantil en PDF."""
        url = reverse('reportes:financiero_estado_cuenta') + f"?estudiante_id={self.estudiante.pk}&ciclo_id={self.ciclo.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_generar_becas_csv(self):
        """Verifica la exportación CSV de becas y convenios."""
        url = reverse('reportes:financiero_becas') + f"?ciclo_id={self.ciclo.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')

    def test_generar_rrhh_reportes(self):
        """Verifica los reportes de RRHH: Consolidado de Planilla, Boleta Individual y Directorio."""
        persona_doc = Persona.objects.create(
            cui="9999888870101",
            nombres="Armando",
            apellidos="Paredes",
            telefono_principal="55559999"
        )
        puesto = Puesto.objects.create(
            nombre_puesto="Catedrático de Ciencias"
        )
        personal = Personal.objects.create(
            persona=persona_doc,
            puesto=puesto,
            fecha_contratacion=timezone.now().date(),
            salario_base_asignado=Decimal("3500.00"),
            estado_laboral='ACTIVO'
        )
        planilla = Planilla.objects.create(
            personal=personal,
            ciclo_escolar=self.ciclo,
            tipo_planilla=TipoPlanillaChoices.ORDINARIA,
            mes_pagado=MesChoices.ENERO,
            salario_base=Decimal("3500.00"),
            salario_ordinario=Decimal("3500.00"),
            bonificacion_incentivo=Decimal("250.00"),
            descuento_igss=Decimal("169.05"),
            pagado=True
        )

        url_plan_pdf = reverse('reportes:rrhh_consolidado_planillas') + f"?ciclo_id={self.ciclo.id}&mes=1&formato=pdf"
        resp_plan_pdf = self.client.get(url_plan_pdf)
        self.assertEqual(resp_plan_pdf.status_code, 200)
        self.assertEqual(resp_plan_pdf['Content-Type'], 'application/pdf')

        url_plan_csv = reverse('reportes:rrhh_consolidado_planillas') + f"?ciclo_id={self.ciclo.id}&mes=1&formato=csv"
        resp_plan_csv = self.client.get(url_plan_csv)
        self.assertEqual(resp_plan_csv.status_code, 200)
        self.assertEqual(resp_plan_csv['Content-Type'], 'text/csv; charset=utf-8')

        url_boleta = reverse('reportes:rrhh_boleta_pago') + f"?planilla_id={planilla.id}"
        resp_boleta = self.client.get(url_boleta)
        self.assertEqual(resp_boleta.status_code, 200)
        self.assertEqual(resp_boleta['Content-Type'], 'application/pdf')

        url_dir_pdf = reverse('reportes:rrhh_directorio') + "?formato=pdf"
        resp_dir_pdf = self.client.get(url_dir_pdf)
        self.assertEqual(resp_dir_pdf.status_code, 200)
        self.assertEqual(resp_dir_pdf['Content-Type'], 'application/pdf')

        url_dir_csv = reverse('reportes:rrhh_directorio') + "?formato=csv"
        resp_dir_csv = self.client.get(url_dir_csv)
        self.assertEqual(resp_dir_csv.status_code, 200)
        self.assertEqual(resp_dir_csv['Content-Type'], 'text/csv; charset=utf-8')

    def test_generar_disciplina_pdf_y_csv(self):
        """Verifica el Historial de Incidentes Disciplinarios en PDF y CSV."""
        IncidenteDisciplinario.objects.create(
            estudiante=self.estudiante,
            ciclo_escolar=self.ciclo,
            fecha=timezone.now().date(),
            tipo_falta=TipoFaltaChoices.LEVE,
            categoria=CategoriaFaltaChoices.DESATENCION,
            descripcion_hechos="Interrupción durante explicación de clase."
        )

        url_pdf = reverse('reportes:disciplina_historial') + f"?ciclo_id={self.ciclo.id}&seccion_id={self.seccion.id}&formato=pdf"
        resp_pdf = self.client.get(url_pdf)
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf['Content-Type'], 'application/pdf')

        url_csv = reverse('reportes:disciplina_historial') + f"?ciclo_id={self.ciclo.id}&seccion_id={self.seccion.id}&formato=csv"
        resp_csv = self.client.get(url_csv)
        self.assertEqual(resp_csv.status_code, 200)
        self.assertEqual(resp_csv['Content-Type'], 'text/csv; charset=utf-8')

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

    def test_apis_selectores_interactivos(self):
        """Verifica las APIs JSON para filtros dependientes (Grado -> Secciones y Sección -> Estudiantes)."""
        url_sec = reverse('reportes:api_secciones_por_grado', kwargs={'grado_id': self.grado.id})
        resp_sec = self.client.get(url_sec)
        self.assertEqual(resp_sec.status_code, 200)
        data_sec = resp_sec.json()
        self.assertIn('secciones', data_sec)
        self.assertTrue(len(data_sec['secciones']) >= 1)
        self.assertEqual(data_sec['secciones'][0]['id'], self.seccion.id)

        url_est = reverse('reportes:api_estudiantes_por_seccion', kwargs={
            'seccion_id': self.seccion.id,
            'ciclo_id': self.ciclo.id
        })
        resp_est = self.client.get(url_est)
        self.assertEqual(resp_est.status_code, 200)
        data_est = resp_est.json()
        self.assertIn('estudiantes', data_est)
        self.assertTrue(len(data_est['estudiantes']) >= 1)
        self.assertEqual(data_est['estudiantes'][0]['id'], self.estudiante.pk)


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
        import zipfile
        from pathlib import Path
        from django.conf import settings
        from APPS.reportes.tareas import generar_boletas_seccion_zip, obtener_estado_tarea

        resultado = generar_boletas_seccion_zip('test-task-1', self.seccion.id, self.ciclo.id)

        self.assertEqual(resultado['status'], 'COMPLETADO')
        self.assertEqual(resultado['total'], 1)
        self.assertIn('.zip', resultado['filename'])
        self.assertTrue(resultado['archivo_url'].startswith('/media/reportes_lotes/'))

        # Validar contenido interno del archivo ZIP generado
        zip_path = Path(settings.MEDIA_ROOT) / 'reportes_lotes' / resultado['filename']
        self.assertTrue(zip_path.exists())
        with zipfile.ZipFile(zip_path, 'r') as zf:
            nombres = zf.namelist()
            self.assertFalse(any(n.startswith('ERROR_') for n in nombres), f"Se encontraron errores en el zip: {nombres}")
            self.assertTrue(any(n.endswith('.pdf') for n in nombres))
            pdf_name = [n for n in nombres if n.endswith('.pdf')][0]
            info = zf.getinfo(pdf_name)
            self.assertGreater(info.file_size, 1000)

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
