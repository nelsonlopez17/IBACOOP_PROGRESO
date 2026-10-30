"""
APPS/estudiantes/tests.py

Pruebas unitarias para el Módulo de Estudiantes e Integración Financiera:
  - Registro de estudiante y autogeneración de CuentaPorCobrar de matrícula.
  - Verificación de propiedades de solvencia (solvencia_inscripcion_estado, saldo_total_pendiente).
  - Vistas de lista y detalle 360° con insignias de solvencia.
"""
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from APPS.core.models import Persona
from APPS.usuarios.models import RolChoices
from APPS.academico.models import CicloEscolar, Grado, Seccion
from APPS.estudiantes.models import Estudiante, Encargado
from APPS.financiero.models import ConceptoPago, CuentaPorCobrar, Abono, CategoriaConceptoChoices

Usuario = get_user_model()


class EstudiantesFinancieroTestCase(TestCase):

    def setUp(self):
        self.admin_user = Usuario.objects.create_user(
            username='2580123450101',
            email='admin.est@ibacoop.edu.gt',
            password='TestPassword123!',
            rol=RolChoices.ADMINISTRADOR,
            is_staff=True,
            is_superuser=True
        )

        self.ciclo = CicloEscolar.objects.create(
            anio=2026,
            estado_activo=True
        )

        self.concepto_matricula = ConceptoPago.objects.create(
            nombre='Inscripción Ciclo Básico 2026',
            monto_estandar=Decimal('350.00'),
            categoria_concepto=CategoriaConceptoChoices.MATRICULA,
            aplica_al_inscribir_seccion=True
        )

        self.persona_tutor = Persona.objects.create(
            cui='1000000000010',
            nombres='Roberto',
            apellidos='Alvarado',
            fecha_nacimiento='1975-03-10',
            correo='roberto.alvarado@test.com',
            telefono_principal='55558888'
        )
        self.tutor = Encargado.objects.create(
            persona=self.persona_tutor,
            lugar_de_trabajo='Comercio Central'
        )

        self.persona_est = Persona.objects.create(
            cui='3000000000001',
            nombres='Mateo',
            apellidos='Alvarado',
            fecha_nacimiento='2012-05-15',
            correo='mateo.alvarado@test.com',
            telefono_principal='55559999'
        )
        self.estudiante = Estudiante.objects.create(
            persona=self.persona_est,
            codigo_mineduc='E123ABC',
            encargado=self.tutor
        )

    def test_solvencia_propiedades_sin_cuenta(self):
        """Verifica que un estudiante sin cuentas por cobrar tenga solvencia SIN_COBRO."""
        self.assertEqual(self.estudiante.solvencia_inscripcion_estado, 'SIN_COBRO')
        self.assertEqual(self.estudiante.saldo_total_pendiente, 0)

    def test_solvencia_pendiente_y_pago_solvente(self):
        """Verifica la transición de PENDIENTE a SOLVENTE tras registrar un abono."""
        cpc = CuentaPorCobrar.objects.create(
            estudiante=self.estudiante,
            concepto=self.concepto_matricula,
            ciclo_escolar=self.ciclo,
            monto_total=Decimal('350.00'),
            saldo_pendiente=Decimal('350.00')
        )

        self.assertEqual(self.estudiante.solvencia_inscripcion_estado, 'PENDIENTE')
        self.assertEqual(self.estudiante.saldo_total_pendiente, Decimal('350.00'))

        Abono.objects.create(
            cuenta_por_cobrar=cpc,
            monto_pagado=Decimal('350.00'),
            fecha_pago='2026-01-15',
            numero_boleta='BOL-99001'
        )

        cpc.refresh_from_db()
        self.assertEqual(cpc.saldo_pendiente, Decimal('0.00'))
        self.assertEqual(self.estudiante.solvencia_inscripcion_estado, 'SOLVENTE')
        self.assertEqual(self.estudiante.saldo_total_pendiente, Decimal('0.00'))

    def test_vistas_estudiante_muestran_solvencia(self):
        """Verifica que la lista de estudiantes y la ficha 360 respondan 200 con la información financiera."""
        CuentaPorCobrar.objects.create(
            estudiante=self.estudiante,
            concepto=self.concepto_matricula,
            ciclo_escolar=self.ciclo,
            monto_total=Decimal('350.00'),
            saldo_pendiente=Decimal('350.00')
        )

        self.client.force_login(self.admin_user)

        res_list = self.client.get(reverse('estudiantes:estudiante_list'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, 'Solvencia')
        self.assertContains(res_list, 'Pendiente')

        res_detail = self.client.get(reverse('estudiantes:estudiante_detail', kwargs={'pk': self.estudiante.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, 'Solvencia Inscripción')
        self.assertContains(res_detail, 'PENDIENTE PAGO')
        self.assertContains(res_detail, 'Deuda Pendiente Total')

    def test_encargado_list_view_activos_e_inactivos(self):
        """Verifica que EncargadoListView separe correctamente a los encargados activos e inactivos."""
        self.client.force_login(self.admin_user)

        res_activos = self.client.get(reverse('estudiantes:encargado_list'), {'estado': 'ACTIVO'})
        self.assertEqual(res_activos.status_code, 200)
        self.assertContains(res_activos, 'Roberto Alvarado')

        res_inactivos = self.client.get(reverse('estudiantes:encargado_list'), {'estado': 'INACTIVO'})
        self.assertEqual(res_inactivos.status_code, 200)
        self.assertNotContains(res_inactivos, 'Roberto Alvarado')

        self.estudiante.estado_estudiante = 'RETIRADO'
        self.estudiante.save()

        res_activos_post = self.client.get(reverse('estudiantes:encargado_list'), {'estado': 'ACTIVO'})
        self.assertEqual(res_activos_post.status_code, 200)
        self.assertNotContains(res_activos_post, 'Roberto Alvarado')

        res_inactivos_post = self.client.get(reverse('estudiantes:encargado_list'), {'estado': 'INACTIVO'})
        self.assertEqual(res_inactivos_post.status_code, 200)
        self.assertContains(res_inactivos_post, 'Roberto Alvarado')

        res_todos = self.client.get(reverse('estudiantes:encargado_list'), {'estado': 'TODOS'})
        self.assertEqual(res_todos.status_code, 200)
        self.assertContains(res_todos, 'Roberto Alvarado')

    def test_encargado_detail_and_update_views(self):
        """Verifica que las vistas de detalle y edición del encargado funcionen correctamente."""
        self.client.force_login(self.admin_user)

        res_detail = self.client.get(reverse('estudiantes:encargado_detail', kwargs={'pk': self.tutor.pk}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, 'Roberto Alvarado')
        self.assertContains(res_detail, 'Comercio Central')
        self.assertContains(res_detail, 'Mateo Alvarado')

        res_edit_get = self.client.get(reverse('estudiantes:encargado_update', kwargs={'pk': self.tutor.pk}))
        self.assertEqual(res_edit_get.status_code, 200)
        self.assertContains(res_edit_get, 'Editar Padre de Familia o Encargado')

        post_data = {
            'nombres': 'Roberto Carlos',
            'apellidos': 'Alvarado Gómez',
            'cui': self.persona_tutor.cui,
            'fecha_nacimiento': '1975-03-10',
            'correo': 'roberto.nuevo@test.com',
            'telefono_principal': '55551234',
            'lugar_de_trabajo': 'Nuevo Empleo Central',
            'direccion': 'Zona 1, El Progreso',
            'genero': 'M',
        }
        res_edit_post = self.client.post(reverse('estudiantes:encargado_update', kwargs={'pk': self.tutor.pk}), post_data)
        self.assertRedirects(res_edit_post, reverse('estudiantes:encargado_detail', kwargs={'pk': self.tutor.pk}))

        self.tutor.refresh_from_db()
        self.persona_tutor.refresh_from_db()
        self.assertEqual(self.tutor.lugar_de_trabajo, 'Nuevo Empleo Central')
        self.assertEqual(self.persona_tutor.nombres, 'Roberto Carlos')
        self.assertEqual(self.persona_tutor.telefono_principal, '55551234')




class RestriccionDescargasEstudianteTestCase(TestCase):
    def setUp(self):
        self.ciclo = CicloEscolar.objects.create(anio=2026, estado_activo=True)
        self.admin_user = Usuario.objects.create_user(
            username='admin_dl_test',
            password='TestPassword123!',
            rol=RolChoices.ADMINISTRADOR,
            debe_cambiar_password=False,
            is_staff=True,
            is_superuser=True
        )
        self.user_estudiante = Usuario.objects.create_user(
            username='est_dl_test',
            password='TestPassword123!',
            rol=RolChoices.ESTUDIANTE,
            debe_cambiar_password=False
        )
        self.persona_est = Persona.objects.create(
            cui='3000000000099',
            nombres='Kevin',
            apellidos='Gómez',
            usuario=self.user_estudiante
        )
        self.estudiante = Estudiante.objects.create(
            persona=self.persona_est,
            codigo_mineduc='EST-9988'
        )
        self.concepto = ConceptoPago.objects.create(
            nombre='Cuota Mensual Test',
            monto_estandar=Decimal('200.00'),
            categoria_concepto=CategoriaConceptoChoices.COLEGIATURA
        )
        self.cpc = CuentaPorCobrar.objects.create(
            estudiante=self.estudiante,
            concepto=self.concepto,
            ciclo_escolar=self.ciclo,
            monto_total=Decimal('200.00'),
            saldo_pendiente=Decimal('0.00'),
            estado_pago='PAGADO'
        )
        self.abono = Abono.objects.create(
            cuenta_por_cobrar=self.cpc,
            monto_pagado=Decimal('200.00'),
            fecha_pago='2026-03-01',
            numero_boleta='BOL-77777'
        )

    def test_estudiante_no_puede_descargar_expediente_pdf(self):
        """Un estudiante recibe 403 (redirección a dashboard) al intentar descargar la ficha del expediente en PDF."""
        self.client.force_login(self.user_estudiante)
        url = reverse('estudiantes:estudiante_pdf_expediente', kwargs={'pk': self.estudiante.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

    def test_estudiante_no_puede_descargar_solvencia_pdf(self):
        """Un estudiante recibe 403 al intentar descargar la constancia de solvencia en PDF."""
        self.client.force_login(self.user_estudiante)
        url = reverse('financiero:solvencia_pdf', kwargs={'pk': self.estudiante.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

    def test_estudiante_no_puede_descargar_recibo_pdf(self):
        """Un estudiante recibe 403 al intentar descargar el recibo de abono en PDF."""
        self.client.force_login(self.user_estudiante)
        url = reverse('financiero:recibo_pdf', kwargs={'pk': self.abono.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

    def test_administrador_si_puede_descargar_expediente_y_solvencia(self):
        """Un administrador puede generar y descargar el expediente y la solvencia en PDF."""
        self.client.force_login(self.admin_user)
        res_exp = self.client.get(reverse('estudiantes:estudiante_pdf_expediente', kwargs={'pk': self.estudiante.pk}))
        self.assertEqual(res_exp.status_code, 200)
        self.assertEqual(res_exp['Content-Type'], 'application/pdf')

        res_solv = self.client.get(reverse('financiero:solvencia_pdf', kwargs={'pk': self.estudiante.pk}))
        self.assertEqual(res_solv.status_code, 200)
        self.assertEqual(res_solv['Content-Type'], 'application/pdf')
