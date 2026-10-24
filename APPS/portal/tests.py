from django.test import TestCase
from django.urls import reverse
from APPS.usuarios.models import Usuario
from APPS.portal.models import SolicitudContacto, ContenidoWeb


class PortalNavegacionTestCase(TestCase):
    def test_vistas_publicas_accesibles_anonimo(self):
        """Verifica que todas las secciones del portal público respondan HTTP 200 para visitantes anónimos."""
        rutas = [
            ('portal:index', 'portal/index.html'),
            ('portal:nosotros', 'portal/nosotros.html'),
            ('portal:oferta_academica', 'portal/oferta_academica.html'),
            ('portal:admisiones', 'portal/admisiones.html'),
            ('portal:contacto', 'portal/contacto.html'),
        ]

        for nombre_url, plantilla in rutas:
            url = reverse(nombre_url)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Error al acceder a {nombre_url}")
            self.assertTemplateUsed(response, plantilla)
            self.assertContains(response, 'IBACOOP')


class PortalRedireccionInteligenteTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='director_test',
            email='director@ibacoop.edu.gt',
            password='Password123!',
            rol='DIRECTOR',
            debe_cambiar_password=False,
        )


    def test_visitante_anonimo_en_raiz_ve_portal_publico(self):
        """Un visitante anónimo que ingresa a '/' debe ver la Landing Page pública (HTTP 200)."""
        response = self.client.get(reverse('portal:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/index.html')

    def test_usuario_autenticado_en_raiz_es_redirigido_al_dashboard(self):
        """Un usuario con sesión activa que ingresa a '/' es redirigido inteligentemente a /dashboard/ (HTTP 302)."""
        self.client.force_login(self.usuario)
        response = self.client.get(reverse('portal:index'))
        self.assertRedirects(response, reverse('core:home'), fetch_redirect_response=False)

    def test_acceso_privado_dashboard_requiere_login(self):
        """Un usuario no autenticado que intenta entrar a /dashboard/ es redirigido a login."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('usuarios:login'), response.url)

    def test_usuario_autenticado_accede_a_dashboard(self):
        """Un usuario autenticado que accede a /dashboard/ recibe HTTP 200."""
        self.client.force_login(self.usuario)
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')


class SolicitudContactoTestCase(TestCase):
    def test_envio_exitoso_solicitud_contacto(self):
        """Prueba que un visitante pueda enviar el formulario de contacto y se guarde en la BD."""
        datos_contacto = {
            'nombre_remitente': 'Carlos Alberto Gómez',
            'correo': 'carlos.gomez@gmail.com',
            'telefono': '55443322',
            'asunto': 'Información para admisión 1ro Básico',
            'mensaje': 'Buenas tardes, quisiera saber el costo de la matrícula y horarios para entrega de papelería.',
        }

        url = reverse('portal:contacto')
        response = self.client.post(url, datos_contacto, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(SolicitudContacto.objects.filter(correo='carlos.gomez@gmail.com').exists())

        solicitud = SolicitudContacto.objects.get(correo='carlos.gomez@gmail.com')
        self.assertEqual(solicitud.nombre_remitente, 'Carlos Alberto Gómez')
        self.assertEqual(solicitud.telefono, '55443322')
        self.assertFalse(solicitud.atendido)
        self.assertContains(response, '¡Gracias por contactarnos!')

    def test_envio_fallido_telefono_invalido(self):
        """Prueba que números de teléfono demasiado cortos fallen la validación."""
        datos_invalidos = {
            'nombre_remitente': 'Maria Lopez',
            'correo': 'maria@gmail.com',
            'telefono': '123',  # Menor a 8 dígitos
            'asunto': 'Consulta',
            'mensaje': 'Mensaje de prueba.',
        }

        url = reverse('portal:contacto')
        response = self.client.post(url, datos_invalidos)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SolicitudContacto.objects.filter(correo='maria@gmail.com').exists())
        self.assertFormError(response.context['form'], 'telefono', 'Por favor ingrese un número de teléfono válido (mínimo 8 dígitos).')
