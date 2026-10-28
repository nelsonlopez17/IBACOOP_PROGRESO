import time
from decimal import Decimal
from django.core import signing
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from APPS.usuarios.models import Usuario
from APPS.portal.models import SolicitudContacto, ContenidoWeb, ConfiguracionPortal, FotoGaleria


class PortalNavegacionTestCase(TestCase):
    def test_vistas_publicas_accesibles_anonimo(self):
        """Verifica que todas las secciones del portal público respondan HTTP 200 para visitantes anónimos."""
        rutas = [
            ('portal:index', 'portal/index.html'),
            ('portal:nosotros', 'portal/nosotros.html'),
            ('portal:oferta_academica', 'portal/oferta_academica.html'),
            ('portal:admisiones', 'portal/admisiones.html'),
            ('portal:galeria', 'portal/galeria.html'),
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

    def test_usuario_autenticado_en_raiz_puede_ver_portal_publico(self):
        """Un usuario con sesión activa que ingresa a '/' puede ver la Landing Page pública (HTTP 200) sin ser redirigido."""
        self.client.force_login(self.usuario)
        response = self.client.get(reverse('portal:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/index.html')
        self.assertContains(response, 'Volver a Mi Panel')

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
    def setUp(self):
        cache.clear()

    def test_envio_exitoso_solicitud_contacto(self):
        """Prueba que un visitante humano pueda enviar el formulario de contacto con token válido."""
        token_humano = signing.dumps(time.time() - 10)
        datos_contacto = {
            'nombre_remitente': 'Carlos Alberto Gómez',
            'correo': 'carlos.gomez@gmail.com',
            'telefono': '55443322',
            'asunto': 'Información para admisión 1ro Básico',
            'mensaje': 'Buenas tardes, quisiera saber el costo de las cuotas y horarios para entrega de papelería.',
            'token_seguridad': token_humano,
            'website_url': '',
        }

        url = reverse('portal:contacto')
        response = self.client.post(url, datos_contacto, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(SolicitudContacto.objects.filter(correo='carlos.gomez@gmail.com').exists())

        solicitud = SolicitudContacto.objects.get(correo='carlos.gomez@gmail.com')
        self.assertEqual(solicitud.nombre_remitente, 'Carlos Alberto Gómez')
        self.assertEqual(solicitud.telefono, '55443322')
        self.assertFalse(solicitud.atendido)
        self.assertContains(response, 'enviado exitosamente')

    def test_envio_fallido_telefono_invalido(self):
        """Prueba que números de teléfono demasiado cortos fallen la validación."""
        token_humano = signing.dumps(time.time() - 10)
        datos_invalidos = {
            'nombre_remitente': 'Maria Lopez',
            'correo': 'maria@gmail.com',
            'telefono': '123',
            'asunto': 'Consulta',
            'mensaje': 'Mensaje de prueba con más de diez caracteres.',
            'token_seguridad': token_humano,
        }

        url = reverse('portal:contacto')
        response = self.client.post(url, datos_invalidos)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SolicitudContacto.objects.filter(correo='maria@gmail.com').exists())
        self.assertFormError(response.context['form'], 'telefono', 'Por favor ingrese un número de teléfono válido (mínimo 8 dígitos).')

    def test_antispam_bloqueo_envio_inmediato_bot(self):
        """Prueba que un envío en menos de 2.5 segundos (bot automatizado) sea rechazado."""
        token_inmediato = signing.dumps(time.time())
        datos_bot = {
            'nombre_remitente': 'Spam Bot Automator',
            'correo': 'bot@spammer.com',
            'telefono': '77889900',
            'asunto': 'Oferta especial de servicios',
            'mensaje': 'Mensaje generado instantáneamente por un script automatizado.',
            'token_seguridad': token_inmediato,
        }

        url = reverse('portal:contacto')
        response = self.client.post(url, datos_bot)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SolicitudContacto.objects.filter(correo='bot@spammer.com').exists())
        self.assertFormError(
            response.context['form'],
            'token_seguridad',
            'El mensaje se envió de forma inmediata sin tiempo de lectura humana. Por favor verifique sus datos e intente de nuevo.'
        )

    def test_antispam_bloqueo_honeypot(self):
        """Prueba que si un bot rellena el campo trampa website_url, la solicitud sea descartada."""
        token_humano = signing.dumps(time.time() - 10)
        datos_honeypot = {
            'nombre_remitente': 'Bot Trampa',
            'correo': 'bot_trampa@spammer.com',
            'telefono': '55667788',
            'asunto': 'Consulta con trampa',
            'mensaje': 'Mensaje intentando engañar al formulario.',
            'website_url': 'http://sitio-spam-malicioso.com',
            'token_seguridad': token_humano,
        }

        url = reverse('portal:contacto')
        response = self.client.post(url, datos_honeypot)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SolicitudContacto.objects.filter(correo='bot_trampa@spammer.com').exists())
        self.assertFormError(response.context['form'], 'website_url', 'Solicitud descartada por detección de actividad automatizada (Spam).')

    def test_antispam_bloqueo_multiples_enlaces(self):
        """Prueba que un mensaje con múltiples hipervínculos externos sea bloqueado."""
        token_humano = signing.dumps(time.time() - 10)
        datos_enlaces = {
            'nombre_remitente': 'Promotor de Enlaces',
            'correo': 'enlaces@spam.com',
            'telefono': '55112233',
            'asunto': 'Visite nuestros sitios web',
            'mensaje': 'Visite https://sitio1.com y también www.sitio2.com para grandes ofertas.',
            'token_seguridad': token_humano,
        }

        url = reverse('portal:contacto')
        response = self.client.post(url, datos_enlaces)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SolicitudContacto.objects.filter(correo='enlaces@spam.com').exists())
        self.assertFormError(response.context['form'], 'mensaje', 'Por medidas de seguridad escolar, no se permite incluir múltiples enlaces web en el mensaje.')

    def test_antispam_rate_limit_por_ip(self):
        """Prueba que tras 3 envíos exitosos desde la misma IP, el 4to intento sea bloqueado."""
        url = reverse('portal:contacto')
        for i in range(3):
            token_valido = signing.dumps(time.time() - 10)
            datos = {
                'nombre_remitente': f'Remitente {i}',
                'correo': f'remitente{i}@gmail.com',
                'telefono': f'5544330{i}',
                'asunto': f'Consulta {i}',
                'mensaje': f'Mensaje de consulta número {i} con más de diez caracteres.',
                'token_seguridad': token_valido,
            }
            resp = self.client.post(url, datos, follow=True)
            self.assertEqual(resp.status_code, 200)

        # 4to intento desde la misma IP: bloqueado por tasa máxima
        token_valido = signing.dumps(time.time() - 10)
        datos_bloqueados = {
            'nombre_remitente': 'Remitente Cuatro',
            'correo': 'remitente4@gmail.com',
            'telefono': '55443304',
            'asunto': 'Consulta cuatro',
            'mensaje': 'Este cuarto mensaje debe ser rechazado por límite de envíos.',
            'token_seguridad': token_valido,
        }
        resp_bloqueada = self.client.post(url, datos_bloqueados, follow=True)
        self.assertEqual(resp_bloqueada.status_code, 200)
        self.assertFalse(SolicitudContacto.objects.filter(correo='remitente4@gmail.com').exists())
        self.assertContains(resp_bloqueada, 'Ha superado el límite de consultas permitidas')


class PortalConfiguracionYGaleriaTestCase(TestCase):
    def setUp(self):
        self.director = Usuario.objects.create_user(
            username='director_portal',
            email='director_portal@ibacoop.edu.gt',
            password='Password123!',
            rol='DIRECTOR',
            debe_cambiar_password=False,
        )
        self.docente = Usuario.objects.create_user(
            username='docente_portal',
            email='docente_portal@ibacoop.edu.gt',
            password='Password123!',
            rol='DOCENTE',
            debe_cambiar_password=False,
        )

    def test_singleton_configuracion_portal(self):
        """Verifica que ConfiguracionPortal opere bajo patrón singleton y genere enlace de WhatsApp."""
        cfg = ConfiguracionPortal.get_solo()
        self.assertIsNotNone(cfg.pk)
        self.assertEqual(ConfiguracionPortal.get_solo().pk, cfg.pk)
        self.assertIn('50001234', cfg.link_whatsapp)
        self.assertEqual(cfg.cuota_mensual, Decimal('100.00'))
        self.assertTrue(len(cfg.lista_puntos_primero_basico) >= 1)
        self.assertTrue(len(cfg.lista_requisitos_primero_basico) >= 1)

    def test_transformacion_url_google_drive(self):
        """Verifica que FotoGaleria convierta enlaces compartidos de Google Drive a URLs directas de imagen."""
        drive_url = "https://drive.google.com/file/d/1A2B3C4D5E6F7G8H9I/view?usp=sharing"
        foto = FotoGaleria.objects.create(
            titulo="Laboratorio de Computación",
            url_imagen=drive_url,
            categoria="INSTALACIONES"
        )
        self.assertIn("drive.google.com/thumbnail?id=1A2B3C4D5E6F7G8H9I", foto.url_directa)

        direct_url = "https://images.unsplash.com/photo-1580582932707-520aed937b7b"
        foto_directa = FotoGaleria.objects.create(
            titulo="Cancha Deportiva",
            url_imagen=direct_url,
            categoria="DEPORTES"
        )
        self.assertEqual(foto_directa.url_directa, direct_url)

    def test_docente_no_puede_acceder_a_gestion_portal(self):
        """Un usuario con rol DOCENTE debe tener el acceso bloqueado a la gestión del portal."""
        self.client.force_login(self.docente)
        response = self.client.get(reverse('portal:gestion_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

    def test_director_accede_a_gestion_portal(self):
        """Un usuario con rol DIRECTOR puede acceder al panel interno de control del portal."""
        self.client.force_login(self.director)
        response = self.client.get(reverse('portal:gestion_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/gestion/panel_gestion.html')

    def test_actualizacion_configuracion_portal_completa(self):
        """Verifica que Dirección pueda actualizar plan de estudios, requisitos, cuotas y cintillo."""
        self.client.force_login(self.director)
        url = reverse('portal:gestion_configuracion')

        datos_actualizados = {
            'nombre_instituto': 'Instituto Básico por Cooperativa El Progreso',
            'lema': 'Educación y Valores',
            'hero_titulo': 'Bienvenidos a IBACOOP El Progreso',
            'hero_descripcion': 'Formando a las nuevas generaciones con excelencia y principios cooperativos.',
            'mision': 'Misión personalizada de prueba para estudiantes.',
            'vision': 'Visión institucional de liderazgo académico cooperativo.',
            # Plan de Estudios
            'plan_estudios_subtitulo': 'Plan formativo actualizado para el ciclo 2026',
            'descripcion_primero_basico': 'Adaptación intensiva y habilidades cuantitativas.',
            'puntos_primero_basico': 'Lógica Matemática\nRobótica Básica\nInglés Práctico',
            'descripcion_segundo_basico': 'Consolidación científica y proyectos cooperativos.',
            'puntos_segundo_basico': 'Física Experimental\nEmprendimiento y Finanzas',
            'descripcion_tercero_basico': 'Orientación vocacional y transición al diversificado.',
            'puntos_tercero_basico': 'Álgebra Superior\nPrácticas en Laboratorio TAC',
            # Requisitos de Inscripción
            'requisitos_subtitulo': 'Documentos requeridos para inscripción 2026:',
            'requisitos_primero_basico': 'Certificado RENAP CUI\nCertificado de 6to Primaria original\nDiploma de Primaria',
            'requisitos_traslados': 'Certificados de grados cursados\nConstancia de Solvencia\nFotocopia de DPI',
            # Datos de contacto y cuotas
            'telefono_principal': '78881234',
            'telefono_whatsapp': '55556677',
            'correo_contacto': 'info@ibacoop.edu.gt',
            'direccion_fisica': 'Colonia El Progreso, Escuintla',
            'horario_atencion': '13:00 a 18:00 hrs',
            'jornada': 'Vespertina',
            'cuota_inscripcion': '175.00',
            'cuota_mensual': '125.00',
            'ciclo_escolar_activo': 'Ciclo Escolar 2026',
            'inscripciones_abiertas': True,
            'mostrar_cintillo_alerta': True,
            'tipo_cintillo_alerta': 'AVISO',
            'texto_cintillo_alerta': 'Atención: Inscripciones abiertas para Primero Básico.',
            'enlace_cintillo': '/admisiones/',
        }

        response = self.client.post(url, datos_actualizados, follow=True)
        self.assertEqual(response.status_code, 200)

        cfg = ConfiguracionPortal.get_solo()
        self.assertEqual(cfg.cuota_mensual, Decimal('125.00'))
        self.assertEqual(cfg.hero_titulo, 'Bienvenidos a IBACOOP El Progreso')
        self.assertEqual(cfg.plan_estudios_subtitulo, 'Plan formativo actualizado para el ciclo 2026')
        self.assertEqual(cfg.descripcion_primero_basico, 'Adaptación intensiva y habilidades cuantitativas.')
        self.assertEqual(len(cfg.lista_puntos_primero_basico), 3)
        self.assertEqual(cfg.lista_puntos_primero_basico[0], 'Lógica Matemática')
        self.assertEqual(len(cfg.lista_requisitos_primero_basico), 3)

        # Verificar reflejo en portada pública
        resp_publica = self.client.get(reverse('portal:index'))
        self.assertContains(resp_publica, 'Plan formativo actualizado para el ciclo 2026')
        self.assertContains(resp_publica, 'Lógica Matemática')
        self.assertContains(resp_publica, 'Robótica Básica')
        self.assertContains(resp_publica, 'Certificado RENAP CUI')
        self.assertContains(resp_publica, 'Q 125.00')

        # Verificar reflejo en páginas especializadas
        resp_oferta = self.client.get(reverse('portal:oferta_academica'))
        self.assertContains(resp_oferta, 'Lógica Matemática')

        resp_admisiones = self.client.get(reverse('portal:admisiones'))
        self.assertContains(resp_admisiones, 'Certificado RENAP CUI')

    def test_alerta_en_pantalla_mensajes_pendientes(self):
        """Verifica que el panel administrativo muestre la alerta si existen mensajes de visitantes pendientes."""
        SolicitudContacto.objects.create(
            nombre_remitente="Madre de Familia",
            correo="madre@correo.com",
            telefono="55443322",
            asunto="Información de cupo",
            mensaje="Deseo saber si hay cupos disponibles.",
            atendido=False
        )

        self.client.force_login(self.director)
        resp_dashboard = self.client.get(reverse('core:home'))
        self.assertEqual(resp_dashboard.status_code, 200)
        self.assertContains(resp_dashboard, 'Mensajes de Visitantes Pendientes')
        self.assertContains(resp_dashboard, 'Atender Mensajes')

        resp_portal = self.client.get(reverse('portal:gestion_dashboard'))
        self.assertEqual(resp_portal.status_code, 200)
        self.assertContains(resp_portal, 'Mensajes de Visitantes Pendientes')

    def test_gestion_solicitud_contacto_por_secretaria(self):
        """Verifica que se pueda registrar seguimiento y marcar atendida una solicitud."""
        sol = SolicitudContacto.objects.create(
            nombre_remitente="Padre de Familia de Prueba",
            correo="padre@gmail.com",
            telefono="55554444",
            asunto="Información de cuotas",
            mensaje="Consulta sobre cuota mensual de Primero Básico."
        )

        self.client.force_login(self.director)
        url_detalle = reverse('portal:solicitud_detalle', kwargs={'pk': sol.pk})

        resp_get = self.client.get(url_detalle)
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, 'Volver al Panel')

        resp_post = self.client.post(url_detalle, {
            'atendido': True,
            'notas_seguimiento': 'Se llamó al padre de familia y se le brindó información de cuota escolar.'
        }, follow=True)

        self.assertEqual(resp_post.status_code, 200)
        sol.refresh_from_db()
        self.assertTrue(sol.atendido)
        self.assertEqual(sol.atendido_por, self.director)
        self.assertIn('cuota escolar', sol.notas_seguimiento)

    def test_marcar_solicitud_atendida_rapido(self):
        """Verifica la acción de marcar atendida una solicitud rápidamente desde el listado."""
        sol = SolicitudContacto.objects.create(
            nombre_remitente="Madre de Familia Rápida",
            correo="madre@correo.com",
            telefono="44443333",
            asunto="Cupo para Segundo Básico",
            mensaje="Deseo saber si hay cupos disponibles para Segundo Básico.",
            atendido=False
        )

        url_rapido = reverse('portal:solicitud_marcar_atendido', kwargs={'pk': sol.pk})

        # Intento anónimo debe redirigir al login
        resp_anon = self.client.post(url_rapido)
        self.assertEqual(resp_anon.status_code, 302)
        sol.refresh_from_db()
        self.assertFalse(sol.atendido)

        # Intento autenticado por director
        self.client.force_login(self.director)
        resp = self.client.post(url_rapido, follow=True)
        self.assertEqual(resp.status_code, 200)
        sol.refresh_from_db()
        self.assertTrue(sol.atendido)
        self.assertEqual(sol.atendido_por, self.director)

    def test_publicaciones_visibles_en_portal_publico(self):
        """Verifica que las publicaciones activas se visualicen en la portada pública y en su vista de detalle."""
        pub = ContenidoWeb.objects.create(
            titulo="Inauguración de Laboratorio de Computación 2026",
            seccion="NOTICIAS",
            cuerpo="Se ha instalado nuevo equipo de cómputo para los tres grados del Ciclo Básico.",
            publicado=True,
            autor=self.director
        )

        # Portada pública del portal
        resp_index = self.client.get(reverse('portal:index'))
        self.assertEqual(resp_index.status_code, 200)
        self.assertContains(resp_index, "Inauguración de Laboratorio de Computación 2026")
        self.assertContains(resp_index, "Últimas Publicaciones y Comunicados")

        # Detalle público del comunicado
        url_detalle = reverse('portal:publicacion_detalle', kwargs={'pk': pub.pk})
        resp_det = self.client.get(url_detalle)
        self.assertEqual(resp_det.status_code, 200)
        self.assertContains(resp_det, "Inauguración de Laboratorio de Computación 2026")
        self.assertContains(resp_det, "Ciclo Básico")

        # Listado público de publicaciones
        resp_list = self.client.get(reverse('portal:publicaciones_todas'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, "Inauguración de Laboratorio de Computación 2026")

