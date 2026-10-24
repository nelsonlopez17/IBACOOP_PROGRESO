"""
APPS/disciplina/tests.py

Pruebas automatizadas para el Módulo de Disciplina y Convivencia Escolar.
Verifica creación de incidencias, semáforo de disciplina, citaciones a padres,
generación de PDFs oficiales (Acuerdo 01-2011) y pistas de auditoría inmutable.
"""
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from APPS.disciplina.models import IncidenteDisciplinario, CitacionPadre, TipoFaltaChoices, CategoriaFaltaChoices, EstadoCitacionChoices
from APPS.disciplina.reportes import generar_pdf_citacion_padre, generar_pdf_acta_compromiso
from APPS.estudiantes.models import Estudiante
from APPS.core.models import Persona
from APPS.academico.models import CicloEscolar

Usuario = get_user_model()


class DisciplinaTestCase(TestCase):
    def setUp(self):
        self.director = Usuario.objects.create_user(
            username='director_disc',
            email='director_disc@ibacoop.edu.gt',
            password='Password123!',
            rol='DIRECTOR',
            debe_cambiar_password=False,
        )

        self.ciclo = CicloEscolar.objects.create(
            anio=2026,
            estado_activo=True,
            fecha_inicio=date(2026, 1, 15),
            fecha_fin=date(2026, 10, 31)
        )

        self.persona = Persona.objects.create(
            cui='1234567890101',
            nombres='Juanito',
            apellidos='Pérez',
            fecha_nacimiento=date(2010, 5, 20),
            genero='M'
        )
        self.estudiante = Estudiante.objects.create(
            persona=self.persona,
            codigo_mineduc='C123ABC',
            estado_estudiante='ACTIVO'
        )

    def test_semaforo_disciplina_estudiante(self):
        """Valida que el semáforo cambie adecuadamente: VERDE -> AMARILLO -> ROJO."""
        semaforo = self.estudiante.semaforo_disciplina
        self.assertEqual(semaforo['estado'], 'VERDE')

        inc_leve = IncidenteDisciplinario.objects.create(
            estudiante=self.estudiante,
            ciclo_escolar=self.ciclo,
            reportado_por=self.director,
            fecha=date.today(),
            tipo_falta=TipoFaltaChoices.LEVE,
            categoria=CategoriaFaltaChoices.IMPUNTUALIDAD,
            descripcion_hechos='Llegó 20 minutos tarde al período de matemáticas.'
        )
        semaforo = self.estudiante.semaforo_disciplina
        self.assertEqual(semaforo['estado'], 'AMARILLO')
        self.assertEqual(semaforo['faltas_leves'], 1)

        IncidenteDisciplinario.objects.create(
            estudiante=self.estudiante,
            ciclo_escolar=self.ciclo,
            reportado_por=self.director,
            fecha=date.today(),
            tipo_falta=TipoFaltaChoices.GRAVE,
            categoria=CategoriaFaltaChoices.FALTA_RESPETO,
            descripcion_hechos='Falta de respeto grave durante la clase.'
        )
        semaforo = self.estudiante.semaforo_disciplina
        self.assertEqual(semaforo['estado'], 'ROJO')
        self.assertEqual(semaforo['faltas_graves'], 1)

    def test_citacion_y_generacion_pdf(self):
        """Verifica la vinculación de una citación y la correcta emisión de PDFs con ReportLab."""
        incidente = IncidenteDisciplinario.objects.create(
            estudiante=self.estudiante,
            ciclo_escolar=self.ciclo,
            reportado_por=self.director,
            fecha=date.today(),
            tipo_falta=TipoFaltaChoices.GRAVE,
            categoria=CategoriaFaltaChoices.DESHONESTIDAD,
            descripcion_hechos='Copia indebida durante examen bimestral.',
            requiere_citacion=True
        )

        citacion = CitacionPadre.objects.create(
            incidente=incidente,
            fecha_hora_citacion=timezone.now(),
            motivo_citacion='Comparecencia por falta grave de deshonestidad académica',
            atendido_por=self.director,
            estado=EstadoCitacionChoices.PENDIENTE
        )

        pdf_citacion = generar_pdf_citacion_padre(citacion)
        self.assertTrue(pdf_citacion.startswith(b'%PDF-'))

        pdf_acta = generar_pdf_acta_compromiso(citacion)
        self.assertTrue(pdf_acta.startswith(b'%PDF-'))

    def test_vistas_disciplina(self):
        """Verifica que las vistas principales de disciplina respondan con HTTP 200 para usuarios autorizados."""
        self.client.force_login(self.director)

        response = self.client.get(reverse('disciplina:panel'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disciplina/panel.html')

        response = self.client.get(reverse('disciplina:incidente_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disciplina/incidente_formulario.html')

    def test_historial_auditoria_inmutable(self):
        """Verifica que registrar y modificar un incidente genere historial en simple-history."""
        incidente = IncidenteDisciplinario.objects.create(
            estudiante=self.estudiante,
            ciclo_escolar=self.ciclo,
            reportado_por=self.director,
            fecha=date.today(),
            tipo_falta=TipoFaltaChoices.LEVE,
            categoria=CategoriaFaltaChoices.UNIFORME,
            descripcion_hechos='Uniforme incompleto sin justificación.'
        )

        incidente.descargo_estudiante = 'El estudiante justificó que su suéter se manchó en el camino.'
        incidente.esta_resuelto = True
        incidente.save()

        # verificacion de registros historicos de auditoria
        self.assertEqual(incidente.history.count(), 2)
