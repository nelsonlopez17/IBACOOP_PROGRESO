from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from axes.models import AccessAttempt

from APPS.usuarios.models import Usuario
from APPS.inventario.models import ArticuloInventario
from APPS.disciplina.models import IncidenteDisciplinario, CitacionPadre, TipoFaltaChoices, CategoriaFaltaChoices
from APPS.estudiantes.models import Estudiante, Persona
from APPS.academico.models import CicloEscolar
from APPS.portal.models import ConfiguracionPortal, ContenidoWeb, FotoGaleria, SolicitudContacto
from APPS.auditoria.servicios import AuditoriaService, AUDITED_MODELS
from APPS.auditoria.models import EventoSeguridad, TipoEventoSeguridad


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
        self.custom_user = Usuario.objects.create_user(
            username='auditor_custom',
            email='auditor@ibacoop.edu.gt',
            password='Password123!',
            rol='PERSONAL',
            debe_cambiar_password=False,
        )

    def test_docente_no_puede_acceder_a_auditoria(self):
        """Un usuario con rol DOCENTE debe ser redirigido fuera de auditoría y generar evento de seguridad."""
        self.client.force_login(self.docente_user)
        response = self.client.get(reverse('auditoria:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

        # Verificación de captura de evento de seguridad por acceso denegado
        evento = EventoSeguridad.objects.filter(
            tipo=TipoEventoSeguridad.ACCESO_DENEGADO,
            usuario=self.docente_user
        ).first()
        self.assertIsNotNone(evento)
        self.assertIn('/auditoria/', evento.ruta)

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

    def test_usuario_con_grupo_o_permiso_accede(self):
        """Un usuario asignado al Grupo Directores accede correctamente a auditoría."""
        grupo_dir, _ = Group.objects.get_or_create(name='Directores')
        self.custom_user.groups.add(grupo_dir)
        self.client.force_login(self.custom_user)

        response = self.client.get(reverse('auditoria:dashboard'))
        self.assertEqual(response.status_code, 200)


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

    def test_catalogo_modelos_auditados(self):
        """Verifica que el catálogo incluya modelos del ERP, del portal web y excluya nombres no normalizados."""
        self.assertIn('citacionpadre', AUDITED_MODELS)
        self.assertIn('incidentedisciplinario', AUDITED_MODELS)
        self.assertIn('usuario', AUDITED_MODELS)
        self.assertIn('configuracionportal', AUDITED_MODELS)
        self.assertIn('contenidoweb', AUDITED_MODELS)
        self.assertIn('fotogaleria', AUDITED_MODELS)
        self.assertIn('solicitudcontacto', AUDITED_MODELS)
        self.assertNotIn('incidenteconductual', AUDITED_MODELS)

    def test_auditoria_cambios_portal_web(self):
        """Verifica que los cambios en configuración y contenidos del portal queden auditados con diff."""
        config = ConfiguracionPortal.get_solo()
        config.cuota_mensual = Decimal('125.00')
        config.save()

        historial = config.history.all()
        self.assertGreaterEqual(historial.count(), 1)

        ultimo = historial.first()
        diff = AuditoriaService.get_record_diff('configuracionportal', ultimo.history_id)
        self.assertIsNotNone(diff)

        # Verificar presencia en la vista del panel
        resp = self.client.get(reverse('auditoria:dashboard') + '?modelo=configuracionportal')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Ajustes del Portal Web')
        self.assertContains(resp, 'Portal Web')

    def test_seguimiento_inmutable_y_diff_de_cambios(self):
        """Verifica que modificar un registro auditado genere historial y el diff capture el delta."""
        articulo = ArticuloInventario.objects.create(
            codigo_unico='AUD-TEST-001',
            nombre='Impresora Láser HP',
            categoria='TECNOLOGIA',
            stock_actual=10,
            stock_minimo_alerta=2,
            unidad_medida='unidades'
        )

        # Modificación de existencia en inventario
        articulo.stock_actual = 6
        articulo.save()

        historial = articulo.history.all()
        self.assertGreaterEqual(historial.count(), 2)

        ultimo_registro = historial.first()
        diff = AuditoriaService.get_record_diff('articuloinventario', ultimo_registro.history_id)

        self.assertIsNotNone(diff)
        field_names = [c['field_name'] for c in diff['changes']]
        self.assertIn('stock_actual', field_names)

        # Inspección de diferencias en la vista de detalle
        url_diff = reverse('auditoria:diff_detail', kwargs={
            'modelo': 'articuloinventario',
            'history_id': ultimo_registro.history_id
        })
        response = self.client.get(url_diff)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auditoria/diferencia_detalle.html')
        self.assertContains(response, 'AUD-TEST-001')

    def test_filtros_rapidos_dashboard(self):
        """Verifica que los presets rápidos de fecha operen correctamente."""
        url_hoy = reverse('auditoria:dashboard') + "?preset=hoy"
        resp_hoy = self.client.get(url_hoy)
        self.assertEqual(resp_hoy.status_code, 200)

        url_semana = reverse('auditoria:dashboard') + "?preset=semana"
        resp_semana = self.client.get(url_semana)
        self.assertEqual(resp_semana.status_code, 200)

    def test_exportar_auditoria_csv(self):
        """Verifica que la exportación de auditoría en CSV responda con HTTP 200 y cabeceras adecuadas."""
        url_csv = reverse('auditoria:exportar_csv')
        response = self.client.get(url_csv)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="auditoria_ibacoop_', response['Content-Disposition'])

    def test_desbloquear_intento_acceso(self):
        """Verifica que el endpoint de desbloqueo administrativo libere una IP/cuenta retenida."""
        intento = AccessAttempt.objects.create(
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.150",
            username="docente_bloqueado",
            failures_since_start=4
        )

        url_desbloqueo = reverse('auditoria:desbloquear_intento', kwargs={'attempt_id': intento.id})
        response = self.client.post(url_desbloqueo, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(AccessAttempt.objects.filter(pk=intento.id).exists())
        self.assertContains(response, 'Se ha desbloqueado exitosamente')

        # Verificación del registro del evento de desbloqueo
        self.assertTrue(EventoSeguridad.objects.filter(
            tipo=TipoEventoSeguridad.DESBLOQUEO_CUENTA
        ).exists())

    def test_historial_cambios_usuario(self):
        """Verifica que la modificación de un usuario quede registrada en el historial inmutable."""
        user_test = Usuario.objects.create_user(
            username='operador_auditoria',
            email='operador_antiguo@ibacoop.edu.gt',
            password='Password123!',
            rol='PERSONAL',
            debe_cambiar_password=False
        )

        user_test.email = 'operador_nuevo@ibacoop.edu.gt'
        user_test.save()

        historial = user_test.history.all()
        self.assertGreaterEqual(historial.count(), 2)

        diff = AuditoriaService.get_record_diff('usuario', historial.first().history_id)
        self.assertIsNotNone(diff)
        fields_changed = [c['field_name'] for c in diff['changes']]
        self.assertIn('email', fields_changed)

    def test_meta_auditoria_exportar_csv(self):
        """Verifica que descargar el reporte CSV genere un evento de meta-auditoría."""
        url_csv = reverse('auditoria:exportar_csv')
        self.client.get(url_csv)

        evento_export = EventoSeguridad.objects.filter(
            tipo=TipoEventoSeguridad.DESCARGA_REPORTE,
            usuario=self.director_user
        ).first()
        self.assertIsNotNone(evento_export)
        self.assertIn('CSV', evento_export.descripcion)

    def test_cierre_sesion_evento(self):
        """Verifica que el logout de un usuario genere un evento de auditoría de sesión."""
        self.client.logout()

        evento_logout = EventoSeguridad.objects.filter(
            tipo=TipoEventoSeguridad.CIERRE_SESION,
            usuario=self.director_user
        ).first()
        self.assertIsNotNone(evento_logout)

    def test_filtro_usuario_predictivo_con_cui(self):
        """Verifica que el selector de usuario en auditoría incluya clase de búsqueda predictiva y datos de CUI/nombre."""
        usuario_con_cui = Usuario.objects.create_user(
            username="cgomez_auditoria",
            email="cgomez@ibacoop.edu.gt",
            password="Password123!",
            rol="SECRETARIA",
            debe_cambiar_password=False
        )
        Persona.objects.create(
            usuario=usuario_con_cui,
            nombres="Carlos Roberto",
            apellidos="Gómez Morales",
            cui="2987123450501",
            genero="M",
            telefono_principal="55551234"
        )

        response = self.client.get(reverse('auditoria:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'searchable-select')
        self.assertContains(response, '2987123450501')
        self.assertContains(response, 'Carlos Roberto Gómez Morales')
        self.assertContains(response, 'cgomez_auditoria')

