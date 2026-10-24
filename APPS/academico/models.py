"""
academico/models.py

Núcleo del sistema académico del Instituto El Progreso (Nivel Básico — Guatemala).
Incluye Ciclos, Bloques, Grados, Secciones, Cursos, Asignaciones, Notas con Recuperaciones y Asistencia.
"""
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from simple_history.models import HistoricalRecords

from APPS.core.models import ModeloAuditable


class CicloEscolar(ModeloAuditable):
    """Año lectivo del instituto."""
    anio = models.PositiveIntegerField(
        unique=True,
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
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
        validators=[MinLengthValidator(3)],
        verbose_name='Nombre del bloque'
    )
    orden = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
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
        validators=[MinLengthValidator(3)],
        verbose_name='Nombre del grado'
    )
    orden = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
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
        validators=[MinLengthValidator(1)],
        verbose_name='Letra de sección'
    )
    cupo_maximo = models.PositiveSmallIntegerField(
        default=35,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
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
        validators=[MinLengthValidator(3)],
        verbose_name='Nombre del curso'
    )
    codigo_curso = models.CharField(
        max_length=10,
        unique=True,
        validators=[MinLengthValidator(2)],
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
    history = HistoricalRecords(
        verbose_name='Auditoría de Asignación'
    )

    class Meta:

        verbose_name = 'Asignación de Estudiante'
        verbose_name_plural = 'Asignaciones de Estudiantes'
        unique_together = [['estudiante', 'ciclo_escolar']]

    def __str__(self):
        return f"{self.estudiante.persona.nombre_completo} → {self.seccion} ({self.ciclo_escolar.anio})"


class AsignacionDocente(ModeloAuditable):
    """
    Asignación de un docente a un curso en una sección y ciclo lectivo (Normalizado en FNBC y 4FN).
    La clave candidata (curso, seccion, ciclo_escolar) determina funcionalmente al docente titular (`personal`),
    eliminando dependencias multivaluadas y garantizando consistencia de grado entre curso y sección.
    """
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
        unique_together = [['curso', 'seccion', 'ciclo_escolar']]

    def clean(self):
        super().clean()
        if self.curso_id and self.seccion_id and self.curso.grado_id != self.seccion.grado_id:
            from django.core.exceptions import ValidationError
            raise ValidationError('El grado del curso debe coincidir con el grado de la sección asignada (FNBC).')

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

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.asignacion_estudiante_id and self.curso_id:
            if self.asignacion_estudiante.seccion.grado_id != self.curso.grado_id:
                raise ValidationError('El curso calificado debe pertenecer al mismo grado de la sección del estudiante (FNBC).')
        if self.asignacion_estudiante_id and self.bloque_academico_id:
            if self.asignacion_estudiante.ciclo_escolar_id != self.bloque_academico.ciclo_escolar_id:
                raise ValidationError('El bloque académico debe pertenecer al mismo ciclo escolar de la inscripción del estudiante (FNBC).')

    def __str__(self):
        return f"{self.asignacion_estudiante.estudiante.persona.nombre_completo} — {self.curso.nombre_curso}: {self.nota_total} pts"

    @property
    def nota_total(self) -> Decimal:
        return self.nota_zona + self.nota_examen


class NotaFinalCurso(ModeloAuditable):
    """
    Registro de evaluación final y pruebas de recuperación del curso (Normalizado en 3FN/FNBC/4FN).
    Almacena únicamente los datos primarios no derivados (`nota_recuperacion_1` y `nota_recuperacion_2`),
    mientras que `nota_promedio`, `aplica_recuperacion`, `nota_definitiva` y `esta_promocionado`
    se calculan dinámicamente sin dependencias transitivas.
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

    class Meta:
        verbose_name = 'Nota Final de Curso'
        verbose_name_plural = 'Notas Finales de Cursos'
        unique_together = [['asignacion_estudiante', 'curso']]
        ordering = ['asignacion_estudiante', 'curso']

    @classmethod
    def obtener_anotaciones_sql(cls) -> dict:
        from django.db.models import Subquery, OuterRef, Avg, F, Value, DecimalField, BooleanField, Case, When
        from django.db.models.functions import Coalesce, Greatest, Round
        prom_sub = Subquery(
            NotaBloque.todos.filter(
                asignacion_estudiante_id=OuterRef('asignacion_estudiante_id'),
                curso_id=OuterRef('curso_id'),
                esta_eliminado=False,
            )
            .values('asignacion_estudiante_id', 'curso_id')
            .annotate(p=Round(Avg(F('nota_zona') + F('nota_examen')), 2))
            .values('p')[:1],
            output_field=DecimalField(max_digits=5, decimal_places=2),
        )
        nota_promedio_expr = Coalesce(
            prom_sub,
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=5, decimal_places=2),
        )
        aplica_rec_expr = Case(
            When(nota_promedio__gt=Decimal('0.00'), nota_promedio__lt=Decimal('60.00'), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
        nota_definitiva_expr = Case(
            When(nota_promedio__gte=Decimal('60.00'), then=F('nota_promedio')),
            default=Greatest(
                F('nota_promedio'),
                Coalesce(F('nota_recuperacion_1'), Value(Decimal('0.00'))),
                Coalesce(F('nota_recuperacion_2'), Value(Decimal('0.00'))),
                output_field=DecimalField(max_digits=5, decimal_places=2),
            ),
            output_field=DecimalField(max_digits=5, decimal_places=2),
        )
        esta_promocionado_expr = Case(
            When(nota_definitiva__gte=Decimal('60.00'), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
        return {
            'nota_promedio': nota_promedio_expr,
            'aplica_recuperacion': aplica_rec_expr,
            'nota_definitiva': nota_definitiva_expr,
            'esta_promocionado': esta_promocionado_expr,
        }

    @property
    def nota_promedio(self) -> Decimal:
        if not self.asignacion_estudiante_id or not self.curso_id:
            return Decimal('0.00')
        notas_bloque = list(
            NotaBloque.objects.filter(
                asignacion_estudiante_id=self.asignacion_estudiante_id,
                curso_id=self.curso_id,
                esta_eliminado=False,
            )
        )
        if not notas_bloque:
            return Decimal('0.00')
        total = sum(nb.nota_total for nb in notas_bloque)
        return round(total / Decimal(str(len(notas_bloque))), 2)

    @nota_promedio.setter
    def nota_promedio(self, valor) -> None:
        pass

    @property
    def total_materias_reprobadas(self) -> int:
        """
        Calcula el total de asignaturas reprobadas por el estudiante en su ciclo lectivo actual.
        MINEDUC Acuerdo Ministerial 1171-2010 (Art. 26 y 27).
        """
        if not self.asignacion_estudiante_id:
            return 0
        notas_finales = NotaFinalCurso.objects.filter(
            asignacion_estudiante_id=self.asignacion_estudiante_id,
            esta_eliminado=False,
        )
        return sum(1 for nf in notas_finales if nf.nota_promedio < Decimal('60.00'))

    @property
    def aplica_recuperacion(self) -> bool:
        """
        MINEDUC Acuerdo Ministerial 1171-2010 (Art. 26 y 27):
        - Tienen derecho a recuperación únicamente los estudiantes que reprueben entre 1 y 3 asignaturas.
        - Si reprueban 4 o más asignaturas, no tienen derecho a recuperación y deben cursar nuevamente el grado.
        """
        prom = self.nota_promedio
        if prom >= Decimal('60.00'):
            return False

        notas_existen = NotaBloque.objects.filter(
            asignacion_estudiante_id=self.asignacion_estudiante_id,
            curso_id=self.curso_id,
            esta_eliminado=False,
        ).exists() if (self.asignacion_estudiante_id and self.curso_id) else False
        if not notas_existen:
            return False

        return 1 <= self.total_materias_reprobadas <= 3

    @aplica_recuperacion.setter
    def aplica_recuperacion(self, valor) -> None:
        pass

    @property
    def nota_definitiva(self) -> Decimal:
        prom = self.nota_promedio
        if prom >= Decimal('60.00'):
            return prom
        # Si no tiene derecho legal a recuperación (>= 4 asignaturas reprobadas), la nota definitiva es el promedio reprobado
        if not self.aplica_recuperacion:
            return prom
        candidatas = [prom]
        if self.nota_recuperacion_1 is not None:
            candidatas.append(Decimal(str(self.nota_recuperacion_1)))
        if self.nota_recuperacion_2 is not None:
            candidatas.append(Decimal(str(self.nota_recuperacion_2)))
        return max(candidatas)

    @nota_definitiva.setter
    def nota_definitiva(self, valor) -> None:
        pass

    @property
    def esta_promocionado(self) -> bool:
        return self.nota_definitiva >= Decimal('60.00')

    @esta_promocionado.setter
    def esta_promocionado(self, valor) -> None:
        pass

    def clean(self):
        super().clean()
        if self.asignacion_estudiante_id and self.curso_id:
            if self.asignacion_estudiante.seccion.grado_id != self.curso.grado_id:
                from django.core.exceptions import ValidationError
                raise ValidationError('El curso debe pertenecer al mismo grado de la sección del estudiante (FNBC).')

    def __str__(self):
        estado = 'Promocionado' if self.esta_promocionado else 'No Promocionado'
        return f"{self.asignacion_estudiante.estudiante.persona.nombre_completo} — {self.curso.nombre_curso}: {self.nota_definitiva or self.nota_promedio} pts ({estado})"

    def calcular_nota_final(self):
        """
        Evalúa la nota promedio ordinaria y recuperaciones para retornar (nota_definitiva, esta_promocionado).
        """
        if self.pk:
            self.save(update_fields=['nota_recuperacion_1', 'nota_recuperacion_2', 'actualizado_en'])
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
        max_length=255,
        blank=True,
        verbose_name='Observaciones'
    )

    class Meta:
        verbose_name = 'Asistencia Estudiantil'
        verbose_name_plural = 'Asistencias Estudiantiles'
        unique_together = [['asignacion_estudiante', 'curso', 'fecha']]
        ordering = ['-fecha']

    def clean(self):
        super().clean()
        if self.presente and self.justificado:
            from django.core.exceptions import ValidationError
            raise ValidationError('Un estudiante presente no puede tener una falta justificada simultáneamente.')
        if self.asignacion_estudiante_id and self.curso_id:
            if self.asignacion_estudiante.seccion.grado_id != self.curso.grado_id:
                from django.core.exceptions import ValidationError
                raise ValidationError('El curso de asistencia debe pertenecer al mismo grado de la sección del estudiante (FNBC).')

    def save(self, *args, **kwargs):
        if self.presente:
            self.justificado = False
        super().save(*args, **kwargs)

    def __str__(self):
        estado = 'Presente' if self.presente else 'Ausente'
        return f"{self.asignacion_estudiante.estudiante.persona.nombre_completo} — {self.curso.nombre_curso} ({self.fecha}): {estado}"
