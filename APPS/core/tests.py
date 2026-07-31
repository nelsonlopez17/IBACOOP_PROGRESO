from django.test import TestCase
from django.db.models.deletion import RestrictedError
from APPS.academico.models import Grado, Seccion


class SoftDeleteRestrictedErrorTestCase(TestCase):
    def test_soft_delete_raises_restricted_error_when_active_children_exist(self):
        # Crear un Grado (padre) y una Seccion (hijo relacionado con on_delete=RESTRICT)
        grado = Grado.objects.create(nombre="Primero Básico Test", orden=1)
        seccion = Seccion.objects.create(grado=grado, letra="A", cupo_maximo=30)

        # Intentar eliminar lógicamente el grado teniendo una sección activa debe levantar RestrictedError
        with self.assertRaises(RestrictedError):
            grado.delete()

        # Si se elimina lógicamente la sección primero...
        seccion.delete()

        # Ahora el borrado lógico del grado debe ser exitoso sin lanzar excepción
        grado.delete()
        self.assertTrue(grado.esta_eliminado)
