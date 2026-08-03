"""
academico/models.py

Núcleo del sistema académico del Instituto El Progreso (Nivel Básico — Guatemala).
Incluye Ciclos, Bloques, Grados, Secciones, Cursos, Asignaciones, Notas con Recuperaciones y Asistencia.
"""
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from simple_history.models import HistoricalRecords

from APPS.core.models import ModeloAuditable


class CicloEscolar(ModeloAuditable):
    """Año lectivo del instituto."""
    anio = models.PositiveIntegerField(
        unique=True,
        verbose_name='Año lectivo'
    )
    estado_activo = models.BooleanField(
        default=False,
        verbose_name='Ciclo activo',
        help_text='Único ciclo activo en el sistema.'
    )
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de inicio'
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de finalización'
    )

    class Meta:
        verbose_name = 'Ciclo Escolar'
        verbose_name_plural = 'Ciclos Escolares'
        ordering = ['-anio']

    def __str__(self):
        estado = '✓ Activo' if self.estado_activo else 'Inactivo'
        return f"Ciclo Escolar {self.anio} ({estado})"


class BloqueAcademico(ModeloAuditable):
    """Período de evaluación dentro del ciclo escolar (ej. Primer Bimestre)."""
    ciclo_escolar = models.ForeignKey(
        CicloEscolar,
        on_delete=models.RESTRICT,
        related_name='bloques',
        verbose_name='Ciclo Escolar'
    )
    nombre_bloque = models.CharField(
        max_length=50,
        verbose_name='Nombre del bloque'
    )
    orden = models.PositiveSmallIntegerField(
        verbose_name='Orden de evaluación'
    )
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de inicio'
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de fin'
    )

    class Meta:
        verbose_name = 'Bloque Académico'
        verbose_name_plural = 'Bloques Académicos'
        unique_together = [['ciclo_escolar', 'orden']]
        ordering = ['ciclo_escolar', 'orden']

    def __str__(self):
        return f"{self.nombre_bloque} ({self.ciclo_escolar.anio})"


class Grado(ModeloAuditable):
    """Grado escolar del Nivel Básico (Primero, Segundo, Tercero Básico)."""
    nombre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Nombre del grado'
    )
    orden = models.PositiveSmallIntegerField(
        verbose_name='Orden'
    )

    class Meta:
        verbose_name = 'Grado'
        verbose_name_plural = 'Grados'
        ordering = ['orden']

    def __str__(self):
        return self.nombre


class Seccion(ModeloAuditable):
    """Sección dentro de un grado (A, B, C...)."""
    grado = models.ForeignKey(
        Grado,
        on_delete=models.RESTRICT,
        related_name='secciones',
        verbose_name='Grado'
    )
    letra = models.CharField(
        max_length=1,
        verbose_name='Letra de sección'
    )
    cupo_maximo = models.PositiveSmallIntegerField(
        default=35,
        verbose_name='Cupo máximo de estudiantes'
    )

    class Meta:
        verbose_name = 'Sección'
        verbose_name_plural = 'Secciones'
        unique_together = [['grado', 'letra']]
        ordering = ['grado__orden', 'letra']

    def __str__(self):
        return f"{self.grado.nombre} — Sección {self.letra}"


class Curso(ModeloAuditable):
    """Asignatura impartida según el pensum del MINEDUC."""
    grado = models.ForeignKey(
        Grado,
        on_delete=models.RESTRICT,
        related_name='cursos',
        verbose_name='Grado'
    )
    nombre_curso = models.CharField(
        max_length=100,
        verbose_name='Nombre del curso'
    )
    codigo_curso = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código del curso'
    )

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['grado__orden', 'nombre_curso']

    def __str__(self):
        return f"{self.nombre_curso} ({self.grado.nombre})"


class AsignacionEstudiante(ModeloAuditable):
    """Inscripción formal de un estudiante en una sección para un ciclo escolar."""
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.RESTRICT,
        related_name='asignaciones',
        verbose_name='Estudiante'
    )
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.RESTRICT,
        related_name='asignaciones',
        verbose_name='Sección'
    )
    ciclo_escolar = models.ForeignKey(
        CicloEscolar,
        on_delete=models.RESTRICT,
        related_name='asignaciones_estudiantes',
        verbose_name='Ciclo Escolar'
    )

    class Meta:
        verbose_name = 'Asignación de Estudiante'
        verbose_name_plural = 'Asignaciones de Estudiantes'
        unique_together = [['estudiante', 'ciclo_escolar']]

    def __str__(self):
        return f"{self.estudiante.persona.nombre_completo} → {self.seccion} ({self.ciclo_escolar.anio})"


class AsignacionDocente(ModeloAuditable):
    """Asignación de un docente a un curso en una sección y ciclo lectivo."""
    personal = models.ForeignKey(
        'rrhh.Personal',
        on_delete=models.RESTRICT,
        related_name='asignaciones_docente',
        verbose_name='Docente'
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.RESTRICT,
        related_name='asignaciones_docente',
        verbose_name='Curso'
    )
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.RESTRICT,
        related_name='asignaciones_docente',
        verbose_name='Sección'
    )
    ciclo_escolar = models.ForeignKey(
        CicloEscolar,
        on_delete=models.RESTRICT,
        related_name='asignaciones_docentes',
        verbose_name='Ciclo Escolar'
    )

    class Meta:
        verbose_name = 'Asignación de Docente'
        verbose_name_plural = 'Asignaciones de Docentes'
        unique_together = [['personal', 'curso', 'seccion', 'ciclo_escolar']]

    def __str__(self):
        return f"{self.personal.persona.nombre_completo} → {self.curso.nombre_curso} / {self.seccion} ({self.ciclo_escolar.anio})"


class NotaBloque(ModeloAuditable):
    """Calificación de un estudiante en un bloque académico (Zona + Examen = 100 pts)."""
    asignacion_estudiante = models.ForeignKey(
        AsignacionEstudiante,
        on_delete=models.RESTRICT,
        related_name='notas',
        verbose_name='Asignación del estudiante'
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.RESTRICT,
        related_name='notas',
        verbose_name='Curso'
    )
    bloque_academico = models.ForeignKey(
        BloqueAcademico,
        on_delete=models.RESTRICT,
        related_name='notas',
        verbose_name='Bloque académico'
    )
    nota_zona = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        verbose_name='Nota de Zona (0-60 pts)'
    )
    nota_examen = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        verbose_name='Nota de Examen (0-40 pts)'
    )
    history = HistoricalRecords(
        verbose_name='Historial de cambios de nota'
    )

    class Meta:
        verbose_name = 'Nota de Bloque'
        verbose_name_plural = 'Notas de Bloque'
        unique_together = [['asignacion_estudiante', 'curso', 'bloque_academico']]

    def __str__(self):
        return f"{self.asignacion_estudiante.estudiante.persona.nombre_completo} — {self.curso.nombre_curso}: {self.nota_total} pts"

    @property
    def nota_total(self) -> Decimal:
        return self.nota_zona + self.nota_examen


class NotaFinalCurso(ModeloAuditable):
    """
    Promedio final acumulado del curso y gestión de pruebas de recuperación.
    Maneja los campos de recuperación requeridos en la especificación del sistema.
    """
    asignacion_estudiante = models.ForeignKey(
        AsignacionEstudiante,
        on_delete=models.RESTRICT,
        related_name='notas_finales',
        verbose_name='Asignación del estudiante'
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.RESTRICT,
        related_name='notas_finales',
        verbose_name='Curso'
    )
    nota_promedio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Nota Promedio (0-100 pts)'
    )
    aplica_recuperacion = models.BooleanField(
        default=False,
        verbose_name='¿Aplica a recuperación?',
        help_text='Se activa si el promedio ordinario es menor a 60 puntos.'
    )
    nota_recuperacion_1 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Nota Recuperación 1'
    )
    nota_recuperacion_2 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Nota Recuperación 2'
    )
    nota_definitiva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Nota Definitiva'
    )
    esta_promocionado = models.BooleanField(
        default=False,
        verbose_name='¿Materia Aprobada / Promocionada?'
    )

    class Meta:
        verbose_name = 'Nota Final de Curso'
        verbose_name_plural = 'Notas Finales de Cursos'
        unique_together = [['asignacion_estudiante', 'curso']]
        ordering = ['asignacion_estudiante', 'curso']

    def __str__(self):
        estado = 'Promocionado' if self.esta_promocionado else 'No Promocionado'
        return f"{self.asignacion_estudiante.estudiante.persona.nombre_completo} — {self.curso.nombre_curso}: {self.nota_definitiva or self.nota_promedio} pts ({estado})"

    def calcular_nota_final(self):
        """
        Calcula la nota promedio ordinaria y evalúa recuperaciones para determinar la nota definitiva.
        """
        notas_bloque = NotaBloque.objects.filter(
            asignacion_estudiante=self.asignacion_estudiante,
            curso=self.curso,
            esta_eliminado=False
        )

        if not notas_bloque.exists():
            self.nota_promedio = Decimal('0.00')
            self.aplica_recuperacion = False
            self.nota_definitiva = Decimal('0.00')
            self.esta_promocionado = False
        else:
            total = sum([nb.nota_total for nb in notas_bloque])
            self.nota_promedio = round(total / Decimal(str(notas_bloque.count())), 2)
            
            # Evaluación de recuperaciones
            if self.nota_promedio >= Decimal('60.00'):
                self.aplica_recuperacion = False
                self.nota_definitiva = self.nota_promedio
                self.esta_promocionado = True
            else:
                self.aplica_recuperacion = True
                mejores_notas = [self.nota_promedio]
                if self.nota_recuperacion_1 is not None:
                    mejores_notas.append(self.nota_recuperacion_1)
                if self.nota_recuperacion_2 is not None:
                    mejores_notas.append(self.nota_recuperacion_2)
                
                self.nota_definitiva = max(mejores_notas)
                self.esta_promocionado = self.nota_definitiva >= Decimal('60.00')

        self.save(update_fields=[
            'nota_promedio', 'aplica_recuperacion', 'nota_recuperacion_1',
            'nota_recuperacion_2', 'nota_definitiva', 'esta_promocionado', 'actualizado_en'
        ])
        return self.nota_definitiva, self.esta_promocionado


class AsistenciaEstudiantil(ModeloAuditable):
    """Control diario de asistencia por estudiante y curso."""
    asignacion_estudiante = models.ForeignKey(
        AsignacionEstudiante,
        on_delete=models.RESTRICT,
        related_name='asistencias',
        verbose_name='Asignación del estudiante'
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.RESTRICT,
        related_name='asistencias',
        verbose_name='Curso'
    )
    fecha = models.DateField(
        verbose_name='Fecha'
    )
    presente = models.BooleanField(
        default=True,
        verbose_name='¿Presente?'
    )
    justificado = models.BooleanField(
        default=False,
        verbose_name='¿Ausencia justificada?'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )

    class Meta:
        verbose_name = 'Asistencia Estudiantil'
        verbose_name_plural = 'Asistencias Estudiantiles'
        unique_together = [['asignacion_estudiante', 'curso', 'fecha']]
        ordering = ['-fecha']

    def __str__(self):
        estado = 'Presente' if self.presente else 'Ausente'
        return f"{self.asignacion_estudiante.estudiante.persona.nombre_completo} — {self.curso.nombre_curso} ({self.fecha}): {estado}"
