"""
academico/models.py

Núcleo del sistema educativo del Instituto El Progreso (Nivel Básico — Guatemala).

Implementa el sistema académico del MINEDUC:
  - Solo existen 3 Grados: Primero, Segundo y Tercero Básico.
  - El punteo se divide en Zona (máx. 60 pts) + Examen (máx. 40 pts) = 100 pts.
  - Nota mínima de aprobación: 60 puntos.
  - Los bloques académicos (Bimestres/Trimestres) pertenecen a un CicloEscolar.

django-simple-history se aplica en NotaBloque para auditar todos los cambios
de calificaciones (quién cambió qué nota y cuándo).
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from simple_history.models import HistoricalRecords

from APPS.core.models import ModeloAuditable


class CicloEscolar(ModeloAuditable):
    """
    Representa el año lectivo (ciclo escolar) del instituto.

    Solo debe haber UN ciclo con estado_activo=True a la vez.
    Este ciclo activo es el punto de referencia de todas las operaciones
    académicas y financieras en curso.
    """
    anio = models.PositiveIntegerField(
        unique=True,
        verbose_name='Año lectivo',
    )
    estado_activo = models.BooleanField(
        default=False,
        verbose_name='Ciclo activo',
        help_text='Solo debe existir un ciclo activo a la vez.',
    )
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de inicio',
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de finalización',
    )

    class Meta:
        verbose_name = 'Ciclo Escolar'
        verbose_name_plural = 'Ciclos Escolares'
        ordering = ['-anio']

    def __str__(self):
        estado = '✓ Activo' if self.estado_activo else 'Inactivo'
        return f"Ciclo Escolar {self.anio} ({estado})"


class BloqueAcademico(ModeloAuditable):
    """
    Representa un período de evaluación dentro de un ciclo escolar.
    Ejemplos: Primer Bimestre, Segundo Bimestre, Primer Trimestre.

    RESTRICT en CicloEscolar: no se puede eliminar un ciclo que tenga bloques.
    """
    ciclo_escolar = models.ForeignKey(
        CicloEscolar,
        on_delete=models.RESTRICT,
        related_name='bloques',
        verbose_name='Ciclo Escolar',
    )
    nombre_bloque = models.CharField(
        max_length=50,
        verbose_name='Nombre del bloque',
        help_text='Ej: Primer Bimestre, Segundo Trimestre.',
    )
    orden = models.PositiveSmallIntegerField(
        verbose_name='Orden de evaluación',
    )
    fecha_inicio = models.DateField(null=True, blank=True, verbose_name='Fecha de inicio')
    fecha_fin = models.DateField(null=True, blank=True, verbose_name='Fecha de fin')

    class Meta:
        verbose_name = 'Bloque Académico'
        verbose_name_plural = 'Bloques Académicos'
        unique_together = [['ciclo_escolar', 'orden']]
        ordering = ['ciclo_escolar', 'orden']

    def __str__(self):
        return f"{self.nombre_bloque} ({self.ciclo_escolar.anio})"


class Grado(ModeloAuditable):
    """
    Representa un grado del Nivel Básico en Guatemala.
    Solo existen 3 grados: Primero Básico, Segundo Básico, Tercero Básico.

    RESTRICT implícito: no se puede eliminar un grado si tiene secciones o cursos.
    """
    nombre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Nombre del grado',
        help_text='Ej: Primero Básico, Segundo Básico, Tercero Básico.',
    )
    orden = models.PositiveSmallIntegerField(
        verbose_name='Orden de visualización',
        help_text='1=Primero, 2=Segundo, 3=Tercero.',
    )

    class Meta:
        verbose_name = 'Grado'
        verbose_name_plural = 'Grados'
        ordering = ['orden']

    def __str__(self):
        return self.nombre


class Seccion(ModeloAuditable):
    """
    Representa una sección dentro de un grado (ej. Primero Básico — Sección A).

    cupo_maximo controla la cantidad máxima de estudiantes asignables.
    RESTRICT en Grado: no se puede eliminar un grado que tenga secciones.
    """
    grado = models.ForeignKey(
        Grado,
        on_delete=models.RESTRICT,
        related_name='secciones',
        verbose_name='Grado',
    )
    letra = models.CharField(
        max_length=1,
        verbose_name='Letra de sección',
        help_text='Una sola letra mayúscula. Ej: A, B, C.',
    )
    cupo_maximo = models.PositiveSmallIntegerField(
        default=35,
        verbose_name='Cupo máximo de estudiantes',
    )

    class Meta:
        verbose_name = 'Sección'
        verbose_name_plural = 'Secciones'
        unique_together = [['grado', 'letra']]
        ordering = ['grado__orden', 'letra']

    def __str__(self):
        return f"{self.grado} — Sección {self.letra}"


class Curso(ModeloAuditable):
    """
    Representa una materia o asignatura impartida en un grado específico.

    Vinculado a un Grado específico porque los cursos del Nivel Básico
    pueden variar por grado según el pensum del MINEDUC.
    RESTRICT en Grado: no se puede eliminar un grado si tiene cursos asignados.
    """
    grado = models.ForeignKey(
        Grado,
        on_delete=models.RESTRICT,
        related_name='cursos',
        verbose_name='Grado',
    )
    nombre_curso = models.CharField(
        max_length=100,
        verbose_name='Nombre del curso',
    )
    codigo_curso = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código del curso',
        help_text='Código único para identificar el curso. Ej: MAT-1B.',
    )

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['grado__orden', 'nombre_curso']

    def __str__(self):
        return f"{self.nombre_curso} ({self.grado})"


class AsignacionEstudiante(ModeloAuditable):
    """
    Inscripción formal de un estudiante en una sección para un ciclo escolar.

    La unicidad (estudiante, ciclo_escolar) garantiza que un estudiante no pueda
    estar inscrito en más de una sección en el mismo ciclo.
    RESTRICT en todas las FK: protege la integridad de la inscripción.
    """
    estudiante = models.ForeignKey(
        'estudiantes.Estudiante',
        on_delete=models.RESTRICT,
        related_name='asignaciones',
        verbose_name='Estudiante',
    )
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.RESTRICT,
        related_name='asignaciones',
        verbose_name='Sección',
    )
    ciclo_escolar = models.ForeignKey(
        CicloEscolar,
        on_delete=models.RESTRICT,
        related_name='asignaciones_estudiantes',
        verbose_name='Ciclo Escolar',
    )

    class Meta:
        verbose_name = 'Asignación de Estudiante'
        verbose_name_plural = 'Asignaciones de Estudiantes'
        # Un estudiante solo puede estar en una sección por ciclo
        unique_together = [['estudiante', 'ciclo_escolar']]

    def __str__(self):
        return (
            f"{self.estudiante} → {self.seccion} "
            f"({self.ciclo_escolar.anio})"
        )


class AsignacionDocente(ModeloAuditable):
    """
    Asignación de un docente a un curso específico en una sección y ciclo escolar.

    La unicidad (personal, curso, seccion, ciclo_escolar) evita asignaciones duplicadas.
    RESTRICT en todas las FK: un docente con asignaciones activas no puede ser
    eliminado ni puede eliminarse el curso o sección que imparte.
    """
    personal = models.ForeignKey(
        'rrhh.Personal',
        on_delete=models.RESTRICT,
        related_name='asignaciones_docente',
        verbose_name='Docente',
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.RESTRICT,
        related_name='asignaciones_docente',
        verbose_name='Curso',
    )
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.RESTRICT,
        related_name='asignaciones_docente',
        verbose_name='Sección',
    )
    ciclo_escolar = models.ForeignKey(
        CicloEscolar,
        on_delete=models.RESTRICT,
        related_name='asignaciones_docentes',
        verbose_name='Ciclo Escolar',
    )

    class Meta:
        verbose_name = 'Asignación de Docente'
        verbose_name_plural = 'Asignaciones de Docentes'
        unique_together = [['personal', 'curso', 'seccion', 'ciclo_escolar']]

    def __str__(self):
        return (
            f"{self.personal} → {self.curso} / {self.seccion} "
            f"({self.ciclo_escolar.anio})"
        )


class NotaBloque(ModeloAuditable):
    """
    Calificación de un estudiante en un curso para un bloque académico específico.

    Sistema de punteo MINEDUC (Nivel Básico):
        - Zona:   0 a 60 puntos (actividades, tareas, parciales)
        - Examen: 0 a 40 puntos (examen de fin de bloque)
        - Total:  nota_zona + nota_examen (máx. 100)
        - Mínimo para aprobar: 60 puntos

    django-simple-history: registra automáticamente cada cambio de nota
    (quién la cambió, cuándo, y cuáles fueron los valores anterior y nuevo).

    RESTRICT en todas las FK: garantiza que no se puedan eliminar registros
    académicos mientras existan calificaciones asociadas.
    """
    asignacion_estudiante = models.ForeignKey(
        AsignacionEstudiante,
        on_delete=models.RESTRICT,
        related_name='notas',
        verbose_name='Asignación del estudiante',
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.RESTRICT,
        related_name='notas',
        verbose_name='Curso',
    )
    bloque_academico = models.ForeignKey(
        BloqueAcademico,
        on_delete=models.RESTRICT,
        related_name='notas',
        verbose_name='Bloque académico',
    )
    # --- Punteo MINEDUC ---
    nota_zona = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        verbose_name='Nota de Zona (0–60 pts)',
    )
    nota_examen = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        verbose_name='Nota de Examen (0–40 pts)',
    )
    # --- Auditoría de cambios (django-simple-history) ---
    history = HistoricalRecords(
        verbose_name='Historial de cambios de nota',
    )

    class Meta:
        verbose_name = 'Nota de Bloque'
        verbose_name_plural = 'Notas de Bloque'
        # Un estudiante tiene una sola nota por curso por bloque
        unique_together = [['asignacion_estudiante', 'curso', 'bloque_academico']]

    def __str__(self):
        return (
            f"{self.asignacion_estudiante.estudiante} — "
            f"{self.curso} / {self.bloque_academico} → "
            f"{self.nota_total} pts"
        )

    @property
    def nota_total(self):
        """Calcula el punteo total: Zona + Examen."""
        return self.nota_zona + self.nota_examen

    @property
    def estado_aprobado(self):
        """
        Determina si el estudiante aprueba el bloque.
        Según el MINEDUC, la nota mínima de aprobación es 60 puntos.
        """
        return self.nota_total >= 60

    @property
    def estado_aprobado_display(self):
        """Retorna la etiqueta visual del estado de aprobación."""
        return 'Aprobado' if self.estado_aprobado else 'No Aprobado'


class AsistenciaEstudiantil(ModeloAuditable):
    """
    Registro diario de asistencia de un estudiante a un curso específico.

    La unicidad (asignacion_estudiante, curso, fecha) garantiza un solo registro
    por estudiante por curso por día.
    """
    asignacion_estudiante = models.ForeignKey(
        AsignacionEstudiante,
        on_delete=models.RESTRICT,
        related_name='asistencias',
        verbose_name='Asignación del estudiante',
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.RESTRICT,
        related_name='asistencias',
        verbose_name='Curso',
    )
    fecha = models.DateField(verbose_name='Fecha')
    presente = models.BooleanField(
        default=True,
        verbose_name='¿Presente?',
    )
    justificado = models.BooleanField(
        default=False,
        verbose_name='¿Ausencia justificada?',
        help_text='Aplica solo si presente=False.',
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
    )

    class Meta:
        verbose_name = 'Asistencia Estudiantil'
        verbose_name_plural = 'Asistencias Estudiantiles'
        unique_together = [['asignacion_estudiante', 'curso', 'fecha']]
        ordering = ['-fecha']

    def __str__(self):
        estado = 'Presente' if self.presente else 'Ausente'
        return (
            f"{self.asignacion_estudiante.estudiante} — "
            f"{self.curso} — {self.fecha}: {estado}"
        )
