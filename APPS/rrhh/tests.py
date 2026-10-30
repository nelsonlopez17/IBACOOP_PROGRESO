"""
APPS/rrhh/tests.py

Pruebas unitarias automatizadas para el Módulo de Recursos Humanos:
  - Personal y puestos
  - Asistencia diaria
  - Planilla y nómina mensual (Cálculo masivo y Boletas PDF)
"""
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from APPS.core.models import Persona
from APPS.usuarios.models import RolChoices
from APPS.academico.models import CicloEscolar
from APPS.rrhh.models import (
    Personal, Puesto, Planilla,
    EstadoLaboralChoices, MesChoices
)

Usuario = get_user_model()


class RecursosHumanosTestCase(TestCase):

    def setUp(self):
        self.admin_user = Usuario.objects.create_user(
            username='2580123450101',
            email='admin.rrhh@ibacoop.edu.gt',
            password='TestPassword123!',
            rol=RolChoices.ADMINISTRADOR,
            is_staff=True,
            is_superuser=True
        )

        self.ciclo = CicloEscolar.objects.create(
            anio=2026,
            estado_activo=True
        )

        self.puesto = Puesto.objects.create(
            nombre_puesto='Docente de Matemáticas'
        )

        self.persona1 = Persona.objects.create(
            cui='1000000000001',
            nombres='Lucía',
            apellidos='Méndez',
            fecha_nacimiento='1990-04-12',
            correo='lucia.mendez@ibacoop.edu.gt',
            telefono_principal='55551111'
        )
        self.emp1 = Personal.objects.create(
            persona=self.persona1,
            puesto=self.puesto,
            fecha_contratacion='2022-01-10',
            salario_base_asignado=Decimal('3500.00'),
            estado_laboral=EstadoLaboralChoices.ACTIVO
        )

        self.persona2 = Persona.objects.create(
            cui='1000000000002',
            nombres='Mario',
            apellidos='López',
            fecha_nacimiento='1988-08-20',
            correo='mario.lopez@ibacoop.edu.gt',
            telefono_principal='55552222'
        )
        self.emp2 = Personal.objects.create(
            persona=self.persona2,
            puesto=self.puesto,
            fecha_contratacion='2021-02-01',
            salario_base_asignado=Decimal('4000.00'),
            estado_laboral=EstadoLaboralChoices.ACTIVO
        )

    def test_generacion_masiva_planilla(self):
        """Verifica el cálculo y emisión masiva de planilla para empleados activos con bonificación e IGSS."""
        self.client.force_login(self.admin_user)

        response = self.client.post(reverse('rrhh:planilla_generar'), {
            'ciclo_escolar': self.ciclo.pk,
            'mes_pagado': MesChoices.MARZO,
            'bonificacion_ley': '250.00',
            'descontar_igss': True,
            'fecha_pago': '2026-03-30'
        })
        self.assertEqual(response.status_code, 302)

        pl1 = Planilla.objects.get(personal=self.emp1, mes_pagado=MesChoices.MARZO, ciclo_escolar=self.ciclo)
        self.assertEqual(pl1.bonificacion_incentivo, Decimal('250.00'))
        self.assertEqual(pl1.total_bonificaciones, Decimal('250.00'))
        self.assertEqual(pl1.descuentos, Decimal('169.05'))
        self.assertEqual(pl1.total_pagar, Decimal('3580.95'))

        pl2 = Planilla.objects.get(personal=self.emp2, mes_pagado=MesChoices.MARZO, ciclo_escolar=self.ciclo)
        self.assertEqual(pl2.total_pagar, Decimal('4056.80'))

    def test_ajuste_individual_planilla_y_descarga_pdf(self):
        """Verifica modificación individual de nómina y generación del comprobante oficial en PDF."""
        self.client.force_login(self.admin_user)

        # calculo de retenciones de ley y sueldo liquido en planilla
        pl = Planilla.objects.create(
            personal=self.emp1,
            ciclo_escolar=self.ciclo,
            mes_pagado=MesChoices.ABRIL,
            bonificaciones=Decimal('250.00'),
            descuentos=Decimal('100.00'),
            total_pagar=Decimal('3650.00'),
            pagado=False
        )

        response = self.client.post(reverse('rrhh:planilla_update', kwargs={'pk': pl.pk}), {
            'bonificaciones': '500.00',
            'descuentos': '100.00',
            'fecha_pago': '2026-04-30',
            'pagado': True
        })
        self.assertEqual(response.status_code, 302)

        pl.refresh_from_db()
        self.assertTrue(pl.pagado)
        self.assertEqual(pl.total_pagar, Decimal('3900.00'))  # 3500 + 500 - 100

        res_pdf = self.client.get(reverse('rrhh:planilla_pdf', kwargs={'pk': pl.pk}))
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf['Content-Type'], 'application/pdf')

    def test_generacion_y_coexistencia_bono_14_en_julio(self):
        """Verifica que en Julio coexistan la Planilla Ordinaria y la Planilla de Bono 14 sin colisión."""
        self.client.force_login(self.admin_user)

        # 1. generar planilla ordinaria de julio
        res_ord = self.client.post(reverse('rrhh:planilla_generar'), {
            'ciclo_escolar': self.ciclo.pk,
            'tipo_planilla': 'ORDINARIA',
            'mes_pagado': MesChoices.JULIO,
            'bonificacion_ley': '250.00',
            'descontar_igss': True,
            'fecha_pago': '2026-07-31'
        })
        self.assertEqual(res_ord.status_code, 302)

        # 2. generar planilla de bono 14 en julio (decreto 42-92, exento de igss y sin bono de ley)
        res_bono = self.client.post(reverse('rrhh:planilla_generar'), {
            'ciclo_escolar': self.ciclo.pk,
            'tipo_planilla': 'BONO_14',
            'mes_pagado': MesChoices.JULIO,
            'bonificacion_ley': '0.00',
            'descontar_igss': False,
            'fecha_pago': '2026-07-15'
        })
        self.assertEqual(res_bono.status_code, 302)

        # 3. verificar que ambas boletas existen para el mismo colaborador en el mismo mes y ciclo
        pl_ord = Planilla.objects.get(personal=self.emp1, mes_pagado=MesChoices.JULIO, tipo_planilla='ORDINARIA')
        pl_bono14 = Planilla.objects.get(personal=self.emp1, mes_pagado=MesChoices.JULIO, tipo_planilla='BONO_14')

        self.assertEqual(pl_ord.total_pagar, Decimal('3580.95'))  # 3500 + 250 - 169.05 (igss)
        self.assertEqual(pl_bono14.total_pagar, Decimal('3500.00'))  # 100% salario base neto sin igss ni bono incentivo
        self.assertEqual(pl_bono14.descuento_igss, Decimal('0.00'))

    def test_ajuste_con_descuentos_desglosados_y_motivo(self):
        """Verifica el ajuste con anticipo de sueldo, retención judicial y otros descuentos con su motivo."""
        self.client.force_login(self.admin_user)

        pl = Planilla.objects.create(
            personal=self.emp1,
            ciclo_escolar=self.ciclo,
            mes_pagado=MesChoices.MAYO,
            tipo_planilla='ORDINARIA',
            bonificacion_incentivo=Decimal('250.00'),
            descuento_igss=Decimal('169.05'),
            pagado=False
        )

        response = self.client.post(reverse('rrhh:planilla_update', kwargs={'pk': pl.pk}), {
            'bonificacion_incentivo': '250.00',
            'bonificaciones': '0.00',
            'descuento_igss': '169.05',
            'descuento_anticipo': '300.00',
            'descuento_judicial': '200.00',
            'descuento_otros': '50.00',
            'motivo_otros_descuentos': 'Descuento por falta justificada 1 día',
            'fecha_pago': '2026-05-30',
            'pagado': True
        })
        self.assertEqual(response.status_code, 302)

        pl.refresh_from_db()
        self.assertEqual(pl.descuento_anticipo, Decimal('300.00'))
        self.assertEqual(pl.descuento_judicial, Decimal('200.00'))
        self.assertEqual(pl.descuento_otros, Decimal('50.00'))
        # total descuentos = 169.05 + 300.00 + 200.00 + 50.00 = 719.05
        self.assertEqual(pl.descuentos, Decimal('719.05'))
        # total pagar = 3500 + 250 - 719.05 = 3030.95
        self.assertEqual(pl.total_pagar, Decimal('3030.95'))

        # comprobante pdf se genera correctamente con los rubros
        res_pdf = self.client.get(reverse('rrhh:planilla_pdf', kwargs={'pk': pl.pk}))
        self.assertEqual(res_pdf.status_code, 200)

        # vista / pantalla de detalle de boleta en recursos humanos
        res_det_rrhh = self.client.get(reverse('rrhh:planilla_detail', kwargs={'pk': pl.pk}))
        self.assertEqual(res_det_rrhh.status_code, 200)
        self.assertContains(res_det_rrhh, 'Boleta de Pago de Sueldos')
        self.assertContains(res_det_rrhh, '3,030.95')
        self.assertContains(res_det_rrhh, 'Descuento por falta justificada 1 día')

        # vista / pantalla de detalle de boleta en gestion financiera
        res_det_fin = self.client.get(reverse('financiero:planilla_detail', kwargs={'pk': pl.pk}))
        self.assertEqual(res_det_fin.status_code, 200)
        self.assertContains(res_det_fin, 'Boleta de Pago de Sueldos')
        self.assertContains(res_det_fin, '3,030.95')

        # intentar modificar una boleta pagada debe ser bloqueado y redirigido al detalle
        res_bloqueo_get = self.client.get(reverse('rrhh:planilla_update', kwargs={'pk': pl.pk}))
        self.assertEqual(res_bloqueo_get.status_code, 302)
        self.assertRedirects(res_bloqueo_get, reverse('rrhh:planilla_detail', kwargs={'pk': pl.pk}))

        res_bloqueo_post = self.client.post(reverse('rrhh:planilla_update', kwargs={'pk': pl.pk}), {
            'bonificacion_incentivo': '999.00',
        })
        self.assertEqual(res_bloqueo_post.status_code, 302)
        pl.refresh_from_db()
        self.assertNotEqual(pl.bonificacion_incentivo, Decimal('999.00'))

