"""
estudiantes/models.py

Gestión de Estudiantes, Encargados y sus relaciones de parentesco.
Implementa el patrón Subtipo en Estudiante y Encargado con OneToOneField hacia Persona (primary_key=True).
"""
from django.db import models
from APPS.core.models import ModeloAuditable, Persona


class ParentescoChoices(models.TextChoices):
    PADRE   = 'PADRE',   'Padre'
    MADRE   = 'MADRE',   'Madre'
    ABUELO  = 'ABUELO',  'Abuelo/a'
    TIO     = 'TIO',     'Tío/a'
    HERMANO = 'HERMANO', 'Hermano/a'
    TUTOR   = 'TUTOR',   'Tutor Legal'
    OTRO    = 'OTRO',    'Otro'


class EstadoEstudianteChoices(models.TextChoices):
    ACTIVO     = 'ACTIVO',     'Activo'
    RETIRADO   = 'RETIRADO',   'Retirado'
    GRADUADO   = 'GRADUADO',   'Graduado'
    SUSPENDIDO = 'SUSPENDIDO', 'Suspendido'


class Estudiante(ModeloAuditable):
    """
    Subtipo de Persona para representar a los estudiantes matriculados.
    La relación persona (OneToOneField) actúa como llave primaria.
    """
    persona = models.OneToOneField(
        Persona,
        on_delete=models.RESTRICT,
        primary_key=True,
        related_name='estudiante',
        verbose_name='Persona'
    )
    codigo_mineduc = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código MINEDUC',
        help_text='Código único otorgado por el MINEDUC.'
    )
    estado_estudiante = models.CharField(
        max_length=20,
        choices=EstadoEstudianteChoices.choices,
        default=EstadoEstudianteChoices.ACTIVO,
        verbose_name='Estado académico'
    )
    encargado = models.ForeignKey(
        'Encargado',
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='estudiantes',
        verbose_name='Encargado / Tutor Legal'
    )
    nombre_padre = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nombre del padre'
    )
    telefono_padre = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono del padre'
    )
    nombre_madre = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nombre de la madre'
    )
    telefono_madre = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono de la madre'
    )
    historial_medico = models.TextField(
        blank=True,
        verbose_name='Historial médico',
        help_text='Información médica relevante, alergias, afecciones, etc.'
    )
    # checklist papeleria oficial mineduc (5 documentos obligatorios)
    doc_cert_nacimiento_renap = models.BooleanField(
        default=False,
        verbose_name='Certificado de Nacimiento RENAP'
    )
    doc_dpi_encargado = models.BooleanField(
        default=False,
        verbose_name='Fotocopia DPI Encargado'
    )
    doc_certificado_grado_anterior = models.BooleanField(
        default=False,
        verbose_name='Certificado del Grado Anterior'
    )
    doc_diploma_primaria = models.BooleanField(
        default=False,
        verbose_name='Diploma de Primaria'
    )
    doc_codigo_mineduc = models.BooleanField(
        default=False,
        verbose_name='Constancia Código Personal MINEDUC'
    )
    estado_activo = models.BooleanField(
        default=True,
        verbose_name='Estudiante activo',
        help_text='Indica si el estudiante se encuentra activo en el instituto.'
    )

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'

    def __str__(self):
        cui = f" | CUI: {self.persona.cui}" if self.persona and self.persona.cui else ""
        return f"{self.persona.nombre_completo}{cui} (MINEDUC: {self.codigo_mineduc})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from APPS.core.models import ContactoPersona, DocumentoExpediente, TipoVinculoContactoChoices, TipoDocumentoExpedienteChoices

        if self.persona_id:
            if self.nombre_padre or self.telefono_padre:
                ContactoPersona.objects.update_or_create(
                    persona_id=self.persona_id,
                    tipo_vinculo=TipoVinculoContactoChoices.PADRE,
                    defaults={
                        'nombre_completo': self.nombre_padre or 'Padre',
                        'telefono': self.telefono_padre or '',
                        'esta_eliminado': False,
                    }
                )
            if self.nombre_madre or self.telefono_madre:
                ContactoPersona.objects.update_or_create(
                    persona_id=self.persona_id,
                    tipo_vinculo=TipoVinculoContactoChoices.MADRE,
                    defaults={
                        'nombre_completo': self.nombre_madre or 'Madre',
                        'telefono': self.telefono_madre or '',
                        'esta_eliminado': False,
                    }
                )
            mapa_docs = {
                'doc_cert_nacimiento_renap': TipoDocumentoExpedienteChoices.CERT_NACIMIENTO_RENAP,
                'doc_dpi_encargado': TipoDocumentoExpedienteChoices.DPI_ENCARGADO,
                'doc_certificado_grado_anterior': TipoDocumentoExpedienteChoices.CERTIFICADO_GRADO_ANTERIOR,
                'doc_diploma_primaria': TipoDocumentoExpedienteChoices.DIPLOMA_PRIMARIA,
                'doc_codigo_mineduc': TipoDocumentoExpedienteChoices.CODIGO_MINEDUC,
            }
            for campo, tipo_doc in mapa_docs.items():
                if getattr(self, campo, False):
                    DocumentoExpediente.objects.update_or_create(
                        persona_id=self.persona_id,
                        tipo_documento=tipo_doc,
                        defaults={'entregado': True, 'esta_eliminado': False}
                    )
            if self.encargado_id:
                EstudianteEncargado.objects.update_or_create(
                    estudiante_id=self.pk,
                    encargado_id=self.encargado_id,
                    defaults={
                        'parentesco': ParentescoChoices.TUTOR,
                        'es_contacto_principal': True,
                        'esta_eliminado': False,
                    }
                )

    @property
    def expediente_completo(self):
        """Indica si entregó los 5 documentos obligatorios del MINEDUC."""
        return all([
            self.doc_cert_nacimiento_renap,
            self.doc_dpi_encargado,
            self.doc_certificado_grado_anterior,
            self.doc_diploma_primaria,
            self.doc_codigo_mineduc
        ])

    @property
    def documentos_entregados_count(self):
        """Retorna el número de documentos obligatorios entregados (0 a 5)."""
        docs = [
            self.doc_cert_nacimiento_renap,
            self.doc_dpi_encargado,
            self.doc_certificado_grado_anterior,
            self.doc_diploma_primaria,
            self.doc_codigo_mineduc
        ]
        return sum(1 for d in docs if d)

    @property
    def porcentaje_expediente(self):
        """Retorna el porcentaje de papelería física completada (0 a 100)."""
        return int((self.documentos_entregados_count / 5) * 100)

    @property
    def cuentas_inscripcion(self):
        return self.cuentas_por_cobrar.filter(
            esta_eliminado=False,
            concepto__categoria_concepto='MATRICULA'
        )

    @property
    def solvencia_inscripcion_estado(self):
        cuentas = self.cuentas_inscripcion
        if not cuentas.exists():
            return 'SIN_COBRO'
        if all(c.saldo_pendiente <= 0 for c in cuentas):
            return 'SOLVENTE'
        return 'PENDIENTE'

    @property
    def saldo_total_pendiente(self):
        from decimal import Decimal
        total = sum(c.saldo_pendiente for c in self.cuentas_por_cobrar.filter(esta_eliminado=False))
        return total if total else Decimal('0.00')

    @property
    def semaforo_disciplina(self):
        """
        Calcula el estado del semáforo disciplinario del estudiante conforme
        a la Normativa de Convivencia Pacífica (Acuerdo Ministerial 01-2011 del MINEDUC).
        """
        from APPS.disciplina.models import IncidenteDisciplinario, TipoFaltaChoices
        from APPS.academico.models import CicloEscolar

        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True).first()
        qs = IncidenteDisciplinario.objects.filter(estudiante=self)
        if ciclo_activo:
            qs = qs.filter(ciclo_escolar=ciclo_activo)

        leves = qs.filter(tipo_falta=TipoFaltaChoices.LEVE).count()
        graves = qs.filter(tipo_falta__in=[TipoFaltaChoices.GRAVE, TipoFaltaChoices.MUY_GRAVE]).count()

        if graves > 0 or leves >= 3:
            estado = 'ROJO'
            label = 'Atención Requerida'
            css_class = 'bg-rose-50 text-rose-700 border-rose-300'
            icono = 'shield-alert'
        elif leves > 0:
            estado = 'AMARILLO'
            label = 'En Seguimiento'
            css_class = 'bg-amber-50 text-amber-700 border-amber-300'
            icono = 'alert-circle'
        else:
            estado = 'VERDE'
            label = 'Conducta Ejemplar'
            css_class = 'bg-emerald-50 text-emerald-700 border-emerald-300'
            icono = 'shield-check'

        return {
            'estado': estado,
            'label': label,
            'class': css_class,
            'icono': icono,
            'faltas_leves': leves,
            'faltas_graves': graves,
            'total': leves + graves,
        }

    @property
    def incidentes_conductuales(self):
        """Alias para retrocompatibilidad con referencias previas."""
        return self.incidentes_disciplinarios



class Encargado(ModeloAuditable):
    """
    Subtipo de Persona para representar a los padres o tutores legales.
    La relación persona (OneToOneField) actúa como llave primaria.
    """
    persona = models.OneToOneField(
        Persona,
        on_delete=models.RESTRICT,
        primary_key=True,
        related_name='encargado',
        verbose_name='Persona'
    )
    lugar_de_trabajo = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Lugar de trabajo'
    )

    class Meta:
        verbose_name = 'Encargado'
        verbose_name_plural = 'Encargados'

    def __str__(self):
        cui = f" | DPI: {self.persona.cui}" if getattr(self, "persona", None) and self.persona.cui else ""
        return f"{self.persona.nombre_completo}{cui}"


class EstudianteEncargado(ModeloAuditable):
    """
    Tabla pivote N:M entre Estudiantes y Encargados especificando parentesco y contacto principal.
    """
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.RESTRICT,
        related_name='encargados_rel',
        verbose_name='Estudiante'
    )
    encargado = models.ForeignKey(
        Encargado,
        on_delete=models.RESTRICT,
        related_name='estudiantes_rel',
        verbose_name='Encargado'
    )
    parentesco = models.CharField(
        max_length=20,
        choices=ParentescoChoices.choices,
        verbose_name='Parentesco'
    )
    es_contacto_principal = models.BooleanField(
        default=False,
        verbose_name='¿Es contacto principal?'
    )

    class Meta:
        verbose_name = 'Relación Estudiante-Encargado'
        verbose_name_plural = 'Relaciones Estudiante-Encargado'
        unique_together = [['estudiante', 'encargado']]

    def __str__(self):
        return f"{self.estudiante.persona.nombre_completo} - {self.encargado.persona.nombre_completo} ({self.get_parentesco_display()})"

