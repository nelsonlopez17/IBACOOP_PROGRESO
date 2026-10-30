from decimal import Decimal
from django.test import TestCase
from APPS.usuarios.models import Usuario
from APPS.estudiantes.models import Estudiante
from APPS.academico.models import (
    CicloEscolar, BloqueAcademico, Grado, Seccion, Curso,
    AsignacionEstudiante, NotaBloque, NotaFinalCurso
)


class NotaFinalCursoTestCase(TestCase):
    def setUp(self):
        self.ciclo = CicloEscolar.objects.create(anio=2026, estado_activo=True)
        self.bloque1 = BloqueAcademico.objects.create(ciclo_escolar=self.ciclo, nombre_bloque="Bloque 1", orden=1)
        self.bloque2 = BloqueAcademico.objects.create(ciclo_escolar=self.ciclo, nombre_bloque="Bloque 2", orden=2)
        
        self.grado = Grado.objects.create(nombre="Primero Básico Test", orden=1)
        self.seccion = Seccion.objects.create(grado=self.grado, letra="A", cupo_maximo=30)
        self.curso = Curso.objects.create(grado=self.grado, nombre_curso="Matemáticas", codigo_curso="MAT-101")
        
        self.user_estudiante = Usuario.objects.create_user(username="alumno1", password="password123")
        from APPS.core.models import Persona
        self.persona = Persona.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            cui="1234567890101",
            usuario=self.user_estudiante
        )
        self.estudiante = Estudiante.objects.create(
            persona=self.persona,
            codigo_mineduc="EST-9999"
        )
        self.asignacion = AsignacionEstudiante.objects.create(
            estudiante=self.estudiante,
            seccion=self.seccion,
            ciclo_escolar=self.ciclo
        )

    def test_calculo_nota_final_y_promocion(self):
        # creacion de notas de prueba para bloques academicos
        NotaBloque.objects.create(
            asignacion_estudiante=self.asignacion,
            curso=self.curso,
            bloque_academico=self.bloque1,
            nota_zona=Decimal("45.00"),
            nota_examen=Decimal("25.00")
        )
        NotaBloque.objects.create(
            asignacion_estudiante=self.asignacion,
            curso=self.curso,
            bloque_academico=self.bloque2,
            nota_zona=Decimal("30.00"),
            nota_examen=Decimal("20.00")
        )

        nota_final = NotaFinalCurso.objects.create(
            asignacion_estudiante=self.asignacion,
            curso=self.curso
        )
        promedio, promocionado = nota_final.calcular_nota_final()

        # verificacion de promocion de estudiante con nota aprobatoria
        self.assertEqual(promedio, Decimal("60.00"))
        self.assertTrue(promocionado)
        self.assertTrue(nota_final.esta_promocionado)


class PermisosDocumentosOficialesTestCase(TestCase):
    def setUp(self):
        from django.urls import reverse
        self.ciclo = CicloEscolar.objects.create(anio=2026, estado_activo=True)
        self.grado = Grado.objects.create(nombre="Primero Básico Test", orden=1)
        self.seccion = Seccion.objects.create(grado=self.grado, letra="A", cupo_maximo=30)

        # Usuario estudiante
        self.user_estudiante = Usuario.objects.create_user(
            username="estudiante_test_boleta",
            password="Password123!",
            rol="ESTUDIANTE",
            debe_cambiar_password=False
        )
        from APPS.core.models import Persona
        self.persona_estudiante = Persona.objects.create(
            nombres="Carlos",
            apellidos="López",
            cui="2999123450101",
            usuario=self.user_estudiante
        )
        self.estudiante = Estudiante.objects.create(
            persona=self.persona_estudiante,
            codigo_mineduc="EST-7777"
        )
        self.asignacion = AsignacionEstudiante.objects.create(
            estudiante=self.estudiante,
            seccion=self.seccion,
            ciclo_escolar=self.ciclo
        )

        # Usuario director
        self.user_director = Usuario.objects.create_user(
            username="director_test_boleta",
            password="Password123!",
            rol="DIRECTOR",
            debe_cambiar_password=False
        )

        # Usuario secretaria
        self.user_secretaria = Usuario.objects.create_user(
            username="secretaria_test_boleta",
            password="Password123!",
            rol="SECRETARIA",
            debe_cambiar_password=False
        )

    def test_estudiante_no_puede_descargar_boleta_oficial_pdf(self):
        """Un estudiante autenticado recibe 403 (redirección a dashboard) al intentar descargar la boleta PDF."""
        from django.urls import reverse
        self.client.force_login(self.user_estudiante)
        url = reverse('academico:boleta_pdf', kwargs={'pk': self.asignacion.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

    def test_director_puede_descargar_boleta_oficial_pdf(self):
        """Un usuario Director puede generar y descargar la Boleta de Calificaciones oficial en PDF."""
        from django.urls import reverse
        self.client.force_login(self.user_director)
        url = reverse('academico:boleta_pdf', kwargs={'pk': self.asignacion.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_estudiante_no_puede_descargar_certificacion_estudios_pdf(self):
        """Un estudiante autenticado recibe 403 al intentar descargar la Certificación de Estudios."""
        from django.urls import reverse
        self.client.force_login(self.user_estudiante)
        url = reverse('academico:certificacion_pdf', kwargs={'pk': self.estudiante.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))

    def test_secretaria_puede_descargar_certificacion_estudios_pdf(self):
        """Un usuario Secretaría puede generar y descargar la Certificación de Estudios en PDF."""
        from django.urls import reverse
        self.client.force_login(self.user_secretaria)
        url = reverse('academico:certificacion_pdf', kwargs={'pk': self.estudiante.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_estudiante_accede_a_mis_calificaciones(self):
        """Un usuario ESTUDIANTE puede acceder a su pantalla de calificaciones y rendimiento en modo solo lectura."""
        from django.urls import reverse
        self.client.force_login(self.user_estudiante)
        url = reverse('academico:estudiante_mis_calificaciones')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'academico/estudiante_mis_calificaciones.html')
        self.assertContains(response, 'Mis Calificaciones y Rendimiento Académico')
        self.assertContains(response, 'Solo Lectura')
        self.assertNotContains(response, 'Descargar Boleta')
