from django.test import TestCase
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

        # Verificar que los grupos se asignaron
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

        # Enviar formulario desmarcando el grupo1 y group2 (quedando únicamente group3)
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

        # Verificar que los grupos 1 y 2 fueron eliminados y solo queda el grupo 3
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

        # Todos los grupos deben haber sido removidos
        self.assertEqual(usuario_actualizado.groups.count(), 0)
