from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from APPS.usuarios.models import Usuario
from APPS.inventario.models import ArticuloInventario
from APPS.auditoria.servicios import AuditoriaService


class AuditoriaPermisosTestCase(TestCase):
    def setUp(self):
        self.admin_user = Usuario.objects.create_user(
            username='admin_auditoria',
            email='admin@ibacoop.edu.gt',
            password='Password123!',
            rol='ADMINISTRADOR',
            debe_cambiar_password=False,
        )
        self.docente_user = Usuario.objects.create_user(
            username='docente_auditoria',
            email='docente@ibacoop.edu.gt',
            password='Password123!',
            rol='DOCENTE',
            debe_cambiar_password=False,
        )

    def test_docente_no_puede_acceder_a_auditoria(self):
        """Un usuario con rol DOCENTE debe ser redirigido fuera de auditoría."""
        self.client.force_login(self.docente_user)
        response = self.client.get(reverse('auditoria:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

    def test_administrador_accede_a_auditoria_dashboard(self):
        """Un usuario con rol ADMINISTRADOR debe acceder con éxito (HTTP 200)."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('auditoria:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auditoria/panel.html')

    def test_administrador_accede_a_seguridad(self):
        """Un administrador puede acceder al panel de seguridad de accesos."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('auditoria:seguridad'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auditoria/seguridad.html')


class AuditoriaDiffAndExportTestCase(TestCase):
    def setUp(self):
        self.director_user = Usuario.objects.create_user(
            username='director_auditoria',
            email='director@ibacoop.edu.gt',
            password='Password123!',
            rol='DIRECTOR',
            debe_cambiar_password=False,
        )
        self.client.force_login(self.director_user)

    def test_seguimiento_inmutable_y_diff_de_cambios(self):
        """Verifica que modificar un registro auditado genere historial y el diff capture el delta."""
        # creacion de articulo de inventario para pruebas
        articulo = ArticuloInventario.objects.create(
            codigo_unico='AUD-TEST-001',
            nombre='Impresora Láser HP',
            categoria='TECNOLOGIA',
            stock_actual=10,
            stock_minimo_alerta=2,
            unidad_medida='unidades'
        )


        # modificacion de existencia en inventario
        articulo.stock_actual = 6
        articulo.save()

        # verificacion de registros en el historial de cambios
        historial = articulo.history.all()
        self.assertGreaterEqual(historial.count(), 2)

        ultimo_registro = historial.first()
        diff = AuditoriaService.get_record_diff('articuloinventario', ultimo_registro.history_id)
        
        self.assertIsNotNone(diff)
        fields_changed = [c['field'] for c in diff['changes']]
        self.assertIn('stock_actual', fields_changed)

        # inspeccion de diferencias en la vista de detalle
        url_diff = reverse('auditoria:diff_detail', kwargs={
            'modelo': 'articuloinventario',
            'history_id': ultimo_registro.history_id
        })
        response = self.client.get(url_diff)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auditoria/diferencia_detalle.html')
        self.assertContains(response, 'AUD-TEST-001')

    def test_exportar_auditoria_csv(self):
        """Verifica que la exportación de auditoría en CSV responda con HTTP 200 y cabeceras adecuadas."""
        url_csv = reverse('auditoria:exportar_csv')
        response = self.client.get(url_csv)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="auditoria_ibacoop_', response['Content-Disposition'])
