"""
APPS/inventario/tests.py

Pruebas unitarias automatizadas para el Módulo de Inventario y Control de Activos.
"""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from APPS.core.models import Persona
from APPS.usuarios.models import RolChoices
from APPS.rrhh.models import Personal, Puesto
from APPS.inventario.models import ArticuloInventario, MovimientoInventario, CategoriaChoices, TipoMovimientoChoices

Usuario = get_user_model()


class InventarioTestCase(TestCase):

    def setUp(self):
        self.user = Usuario.objects.create_user(
            username='2580123450101',
            email='admin.test@ibacoop.edu.gt',
            password='TestPassword123!',
            rol=RolChoices.ADMINISTRADOR,
            is_staff=True,
            is_superuser=True
        )

        self.persona = Persona.objects.create(
            cui='1234567890101',
            nombres='Carlos',
            apellidos='Gómez',
            fecha_nacimiento='1985-05-15',
            correo='carlos.gomez@ibacoop.edu.gt',
            telefono_principal='55554444'
        )

        self.puesto = Puesto.objects.create(
            nombre_puesto='Encargado de Inventario'
        )

        self.personal = Personal.objects.create(
            persona=self.persona,
            puesto=self.puesto,
            fecha_contratacion='2020-01-15',
            salario_base_asignado=3500.00
        )

        self.articulo = ArticuloInventario.objects.create(
            codigo_unico='EQ-TECN-001',
            nombre='Proyector Epson PowerLite',
            descripcion='Proyector multimedia para aulas',
            categoria=CategoriaChoices.TECNOLOGIA,
            stock_actual=10,
            stock_minimo_alerta=3,
            unidad_medida='unidades'
        )

    def test_articulo_creacion(self):
        """Verifica la creación y propiedades del modelo ArticuloInventario."""
        self.assertEqual(self.articulo.codigo_unico, 'EQ-TECN-001')
        self.assertFalse(self.articulo.alerta_stock_bajo)

        # validacion de alerta cuando la existencia cae bajo el minimo
        self.articulo.stock_actual = 2
        self.assertTrue(self.articulo.alerta_stock_bajo)

    def test_movimiento_entrada_incrementa_stock(self):
        """Verifica que una ENTRADA incremente el stock_actual."""
        self.client.force_login(self.user)
        response = self.client.post(reverse('inventario:movimiento_create'), {
            'articulo': self.articulo.pk,
            'personal_responsable': self.personal.pk,
            'tipo_movimiento': TipoMovimientoChoices.ENTRADA,
            'cantidad': 5,
            'motivo': 'Compra de nuevos proyectores para aulas de 2do Básico.',
            'documento_referencia': 'Factura #9874'
        })
        self.assertEqual(response.status_code, 302)  # redirige a articulo_detail

        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.stock_actual, 15)

    def test_movimiento_salida_descuenta_stock(self):
        """Verifica que una SALIDA / ASIGNACIÓN descuente el stock_actual."""
        self.client.force_login(self.user)
        response = self.client.post(reverse('inventario:movimiento_create'), {
            'articulo': self.articulo.pk,
            'personal_responsable': self.personal.pk,
            'tipo_movimiento': TipoMovimientoChoices.ASIGNACION,
            'cantidad': 4,
            'motivo': 'Asignación a Laboratorio de Computación.',
            'documento_referencia': 'Vale #001'
        })
        self.assertEqual(response.status_code, 302)

        self.articulo.refresh_from_db()
        self.assertEqual(self.articulo.stock_actual, 6)

    def test_movimiento_salida_excede_stock_error(self):
        """Verifica que una SALIDA mayor al stock actual devuelva error de validación."""
        self.client.force_login(self.user)
        response = self.client.post(reverse('inventario:movimiento_create'), {
            'articulo': self.articulo.pk,
            'personal_responsable': self.personal.pk,
            'tipo_movimiento': TipoMovimientoChoices.SALIDA,
            'cantidad': 50,  # excede el stock actual de 10
            'motivo': 'Intento desincorporación masiva.',
            'documento_referencia': ''
        })
        self.assertEqual(response.status_code, 200)  # re-renders form con error
        form = response.context['form']
        self.assertIn('cantidad', form.errors)
        self.assertIn('Stock insuficiente', form.errors['cantidad'][0])
        self.assertEqual(form.fields['cantidad'].widget.attrs.get('aria-invalid'), 'true')

    def test_vistas_accesibles(self):
        """Verifica que las vistas principales respondan HTTP 200 para el usuario autenticado."""
        self.client.force_login(self.user)

        response_list = self.client.get(reverse('inventario:articulo_list'))
        self.assertEqual(response_list.status_code, 200)

        response_detail = self.client.get(reverse('inventario:articulo_detail', kwargs={'pk': self.articulo.pk}))
        self.assertEqual(response_detail.status_code, 200)

        response_pdf = self.client.get(reverse('inventario:inventario_pdf'))
        self.assertEqual(response_pdf.status_code, 200)
        self.assertEqual(response_pdf['Content-Type'], 'application/pdf')
