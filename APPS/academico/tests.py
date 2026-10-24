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
