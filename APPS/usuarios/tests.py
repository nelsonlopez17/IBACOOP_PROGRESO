from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Group
from APPS.usuarios.models import Usuario
from APPS.usuarios.forms import CustomUserCreationForm, CustomUserChangeForm


class UsuarioFormTestCase(TestCase):
    def setUp(self):
        self.group1 = Group.objects.create(name='Docentes')
        self.group2 = Group.objects.create(name='Secretaría')
        self.group3 = Group.objects.create(name='Contabilidad')

    def test_creacion_usuario_con_grupos(self):
        """Prueba que los grupos seleccionados se asignen correctamente al crear un usuario."""
        form_data = {
            'username': 'nuevo_usuario',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan@colegio.edu.gt',
            'rol': 'DOCENTE',
            'is_active': True,
            'password1': 'Password123!',
            'password2': 'Password123!',
            'groups': [self.group1.id, self.group2.id],
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        usuario = form.save()

        # verificacion de asignacion de grupos
        self.assertEqual(usuario.groups.count(), 2)
        self.assertIn(self.group1, usuario.groups.all())
        self.assertIn(self.group2, usuario.groups.all())

    def test_modificacion_usuario_eliminar_grupos(self):
        """Prueba que desmarcar grupos en el formulario los elimine de la cuenta del usuario."""
        usuario = Usuario.objects.create_user(
            username='usuario_edit',
            email='edit@colegio.edu.gt',
            password='Password123!',
            rol='SECRETARIA',
        )
        usuario.groups.set([self.group1, self.group2, self.group3])
        self.assertEqual(usuario.groups.count(), 3)

        form_data = {
            'username': 'usuario_edit',
            'first_name': 'Maria',
            'last_name': 'Gomez',
            'email': 'edit@colegio.edu.gt',
            'rol': 'SECRETARIA',
            'is_active': True,
            'groups': [self.group3.id],
        }
        form = CustomUserChangeForm(data=form_data, instance=usuario)
        self.assertTrue(form.is_valid(), form.errors)
        usuario_actualizado = form.save()

        self.assertEqual(usuario_actualizado.groups.count(), 1)
        self.assertIn(self.group3, usuario_actualizado.groups.all())
        self.assertNotIn(self.group1, usuario_actualizado.groups.all())
        self.assertNotIn(self.group2, usuario_actualizado.groups.all())

    def test_eliminar_todos_los_grupos(self):
        """Prueba que desmarcar todos los grupos elimine totalmente los permisos del usuario."""
        usuario = Usuario.objects.create_user(
            username='usuario_limpio',
            email='limpio@colegio.edu.gt',
            password='Password123!',
            rol='DOCENTE',
        )
        usuario.groups.set([self.group1, self.group2])
        self.assertEqual(usuario.groups.count(), 2)

        form_data = {
            'username': 'usuario_limpio',
            'first_name': 'Carlos',
            'last_name': 'Lopez',
            'email': 'limpio@colegio.edu.gt',
            'rol': 'DOCENTE',
            'is_active': True,
            'groups': [],  # Todos desmarcados
        }
        form = CustomUserChangeForm(data=form_data, instance=usuario)
        self.assertTrue(form.is_valid(), form.errors)
        usuario_actualizado = form.save()

        self.assertEqual(usuario_actualizado.groups.count(), 0)


class BloqueoCuentaAxesTestCase(TestCase):
    def setUp(self):
        self.username = '2580123450101'
        self.password_correcta = 'ClaveSegura123!'
        self.password_erronea = 'ClaveIncorrecta'
        self.login_url = reverse('usuarios:login')

        self.usuario = Usuario.objects.create_user(
            username=self.username,
            email='test_bloqueo@colegio.edu.gt',
            password=self.password_correcta,
            rol='DOCENTE'
        )

    def test_bloqueo_despues_de_tres_intentos_fallidos(self):
        """Verifica que tras 3 intentos fallidos la cuenta queda bloqueada y muestra la pantalla de lockout."""
        for _ in range(2):
            response = self.client.post(self.login_url, {
                'username': self.username,
                'password': self.password_erronea
            })
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'usuarios/login.html')

        # bloqueo temporal activado por intentos fallidos
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password_erronea
        })
        self.assertEqual(response.status_code, 429)
        self.assertTemplateUsed(response, 'usuarios/lockout.html')
        self.assertContains(response, 'Acceso Bloqueado Temporalmente', status_code=429)

        from axes.models import AccessAttempt
        self.assertTrue(AccessAttempt.objects.filter(username=self.username).exists())

    def test_login_exitoso_limpia_intentos_fallidos(self):
        """Verifica que ingresar la contraseña correcta resetea los intentos fallidos acumulados."""
        from axes.models import AccessAttempt

        for _ in range(2):
            self.client.post(self.login_url, {
                'username': self.username,
                'password': self.password_erronea
            })
        self.assertEqual(AccessAttempt.objects.filter(username=self.username).count(), 1)

        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password_correcta
        })
        self.assertEqual(response.status_code, 302)

        # restablecimiento de contador de intentos
        self.assertEqual(AccessAttempt.objects.filter(username=self.username).count(), 0)


class MiPerfilNotificacionYValidacionTestCase(TestCase):
    def setUp(self):
        from datetime import date
        from APPS.core.models import Persona
        from APPS.estudiantes.models import Estudiante

        self.usuario = Usuario.objects.create_user(
            username='2990123450201',
            email='carlos.est@colegio.edu.gt',
            password='Password123!',
            rol='ESTUDIANTE',
            debe_cambiar_password=False,
        )
        self.persona = Persona.objects.create(
            usuario=self.usuario,
            cui='2990123450201',
            nombres='Carlos',
            apellidos='Morales',
            fecha_nacimiento=date(2012, 5, 10),
            genero='M',
            telefono_principal='55443322',
            correo='carlos.est@colegio.edu.gt',
            direccion='Barrio El Centro, El Progreso',
        )
        self.estudiante = Estudiante.objects.create(
            persona=self.persona,
            codigo_mineduc='C123ABC',
        )

    def test_actualizar_telefono_en_mi_perfil_muestra_toast_inmediato_y_no_se_apila(self):
        """Al guardar cambios en Mi Perfil, la notificación emergente se consume en la misma vista y no se apila en el Dashboard."""
        self.client.force_login(self.usuario)
        response = self.client.post(
            reverse('usuarios:mi_perfil'),
            {
                'telefono_principal': '44556677',
                'telefono_secundario': '',
                'correo': 'carlos.est@colegio.edu.gt',
                'direccion': 'Barrio El Centro, El Progreso',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="django-toast-messages"')
        self.assertContains(response, 'Sus datos de contacto fueron actualizados exitosamente.')

        dash_response = self.client.get(reverse('core:home'))
        self.assertNotContains(dash_response, 'Sus datos de contacto fueron actualizados exitosamente.')

    def test_error_en_mi_perfil_marca_campo_especifico(self):
        """Al ingresar un teléfono inválido, el error se asocia directamente al campo problemático con borde rojo."""
        self.client.force_login(self.usuario)
        response = self.client.post(
            reverse('usuarios:mi_perfil'),
            {
                'telefono_principal': '123',  # Inválido: menos de 8 dígitos
                'telefono_secundario': '',
                'correo': 'carlos.est@colegio.edu.gt',
                'direccion': 'Barrio El Centro, El Progreso',
            },
        )
        self.assertEqual(response.status_code, 200)
        contacto_form = response.context['contacto_form']
        self.assertIn('telefono_principal', contacto_form.errors)
        self.assertEqual(contacto_form.fields['telefono_principal'].widget.attrs.get('aria-invalid'), 'true')
        self.assertIn('border-rose-500', contacto_form.fields['telefono_principal'].widget.attrs.get('class', ''))

    def test_inmutabilidad_username_y_proteccion_3fn_en_edicion(self):
        """
        Verifica que:
        1. username sea inmutable en CustomUserChangeForm (disabled=True).
        2. first_name, last_name y email estén protegidos cuando existe Persona vinculada.
        3. is_active no pueda desmarcarse cuando el usuario edita su propia cuenta.
        4. Al corregir el CUI en Persona, se sincronice automáticamente usuario.username.
        """
        form = CustomUserChangeForm(
            data={
                'username': 'intento_hack_username',
                'first_name': 'IntentoNombre',
                'last_name': 'IntentoApellido',
                'email': 'hack@colegio.edu.gt',
                'rol': 'ESTUDIANTE',
                'is_active': False,  # Intento de autodesactivación
                'debe_cambiar_password': False,
            },
            instance=self.usuario,
            current_user=self.usuario,
        )
        self.assertTrue(form.fields['username'].disabled)
        self.assertTrue(form.fields['first_name'].disabled)
        self.assertTrue(form.fields['last_name'].disabled)
        self.assertTrue(form.fields['email'].disabled)
        self.assertTrue(form.fields['is_active'].disabled)

        self.assertTrue(form.is_valid(), form.errors)
        usuario_guardado = form.save()
        usuario_guardado.refresh_from_db()

        self.assertEqual(usuario_guardado.username, '2990123450201')
        self.assertEqual(usuario_guardado.first_name, 'Carlos')
        self.assertEqual(usuario_guardado.last_name, 'Morales')
        self.assertTrue(usuario_guardado.is_active)

        # sincronizacion automatica de identificador de usuario
        self.persona.cui = '2990123450299'
        self.persona.save()
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.username, '2990123450299')

    def test_proteccion_jerarquica_superusuario_en_edicion_y_toggle(self):
        """Verifica que un usuario con permiso change_usuario pero no superusuario no pueda editar ni desactivar a un Superadministrador."""
        from django.contrib.auth.models import Permission

        superadmin = Usuario.objects.create_superuser(
            username='superadmin_root',
            email='root@ibacoop.edu.gt',
            password='Password123!',
            rol='ADMINISTRADOR',
        )
        operador = Usuario.objects.create_user(
            username='secretaria_iam',
            email='sec@ibacoop.edu.gt',
            password='Password123!',
            rol='SECRETARIA',
            debe_cambiar_password=False,
        )
        perm_change = Permission.objects.get(codename='change_usuario')
        operador.user_permissions.add(perm_change)

        self.client.force_login(operador)

        # restriccion de permisos sobre cuenta principal
        res_edit = self.client.get(reverse('usuarios:usuario_update', args=[superadmin.pk]))
        self.assertEqual(res_edit.status_code, 403)

        res_toggle = self.client.post(reverse('usuarios:usuario_toggle_active', args=[superadmin.pk]))
        self.assertEqual(res_toggle.status_code, 403)
        superadmin.refresh_from_db()
        self.assertTrue(superadmin.is_active)
