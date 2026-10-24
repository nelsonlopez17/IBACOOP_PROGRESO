"""
core/models.py

Módulo base del sistema de gestión escolar.
Provee:
  - ModeloAuditable y ActivosManager para la eliminación lógica (Soft Delete).
  - Modelo Persona que implementa el patrón Supertipo/Subtipo para Estudiante, Encargado y Personal.
"""
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.expressions import BaseExpression
from django.utils import timezone
from APPS.core.validadores import validador_cui_renap, validador_telefono_guatemala


def _extraer_nombres_de_expresion(expr) -> set[str]:
    """Extrae recursivamente nombres de campos referenciados en expresiones F(), Q(), Case(), Aggregate(), etc."""
    nombres = set()
    if expr is None:
        return nombres
    if isinstance(expr, models.F):
        nombres.add(expr.name.split('__')[0])
        return nombres
    if isinstance(expr, models.Q):
        for child in expr.children:
            if isinstance(child, models.Q):
                nombres.update(_extraer_nombres_de_expresion(child))
            elif isinstance(child, tuple) and len(child) == 2:
                k, v = child
                if isinstance(k, str):
                    nombres.add(k.split('__')[0])
                nombres.update(_extraer_nombres_de_expresion(v))
        return nombres
    if isinstance(expr, BaseExpression) or hasattr(expr, 'get_source_expressions'):
        try:
            for src in expr.get_source_expressions():
                nombres.update(_extraer_nombres_de_expresion(src))
        except Exception:
            pass
    return nombres


class ActivosQuerySet(models.QuerySet):
    """
    QuerySet enriquecido que permite:
      1. Inyectar dinámicamente anotaciones SQL cuando se filtra, ordena o agrega por propiedades normalizadas (3FN/4FN).
      2. Soportar propiedades virtuales con @setter en create(), get_or_create() y update_or_create().
    """

    def _asegurar_anotaciones_virtuales(self, nombres_referenciados: set[str]):
        if not nombres_referenciados or not hasattr(self.model, 'obtener_anotaciones_sql'):
            return self
        mapa_anotaciones = self.model.obtener_anotaciones_sql()
        faltantes = [
            nombre for nombre in mapa_anotaciones
            if nombre in nombres_referenciados and nombre not in self.query.annotations
        ]
        if not faltantes:
            return self
        # inyectar anotaciones en el orden del modelo para respetar dependencias
        anotaciones_a_aplicar = {}
        for k, expr in mapa_anotaciones.items():
            if k not in self.query.annotations:
                anotaciones_a_aplicar[k] = expr
        return self.annotate(**anotaciones_a_aplicar) if anotaciones_a_aplicar else self

    def _filter_or_exclude(self, negate, args, kwargs):
        nombres = set()
        for arg in args:
            nombres.update(_extraer_nombres_de_expresion(arg))
        for k, v in kwargs.items():
            nombres.add(k.split('__')[0])
            nombres.update(_extraer_nombres_de_expresion(v))
        qs = self._asegurar_anotaciones_virtuales(nombres)
        return super(ActivosQuerySet, qs)._filter_or_exclude(negate, args, kwargs)

    def aggregate(self, *args, **kwargs):
        nombres = set()
        for arg in args:
            nombres.update(_extraer_nombres_de_expresion(arg))
        for v in kwargs.values():
            nombres.update(_extraer_nombres_de_expresion(v))
        qs = self._asegurar_anotaciones_virtuales(nombres)
        return super(ActivosQuerySet, qs).aggregate(*args, **kwargs)

    def order_by(self, *field_names):
        nombres = {
            f.lstrip('-').split('__')[0]
            for f in field_names
            if isinstance(f, str) and f != '?'
        }
        qs = self._asegurar_anotaciones_virtuales(nombres)
        return super(ActivosQuerySet, qs).order_by(*field_names)

    def _separar_campos_virtuales(self, diccionario: dict | None):
        if not diccionario:
            return {}, {}
        campos_concretos = {
            f.name for f in self.model._meta.get_fields()
            if getattr(f, 'concrete', False) or getattr(f, 'many_to_many', False)
        } | {
            f.attname for f in self.model._meta.concrete_fields
        }
        concretos = {}
        virtuales = {}
        for k, v in diccionario.items():
            if k in campos_concretos:
                concretos[k] = v
            elif isinstance(getattr(self.model, k, None), property):
                virtuales[k] = v
            else:
                concretos[k] = v
        return concretos, virtuales

    def create(self, **kwargs):
        concretos, virtuales = self._separar_campos_virtuales(kwargs)
        obj = self.model(**concretos)
        for k, v in virtuales.items():
            setattr(obj, k, v)
        self._for_write = True
        obj.save(force_insert=True, using=self.db)
        return obj

    def get_or_create(self, defaults=None, **kwargs):
        concretos_def, virtuales_def = self._separar_campos_virtuales(defaults)
        concretos_kw, virtuales_kw = self._separar_campos_virtuales(kwargs)
        obj, created = super().get_or_create(defaults=concretos_def, **concretos_kw)
        virtuales = {**virtuales_kw, **virtuales_def} if created else {}
        if virtuales:
            for k, v in virtuales.items():
                setattr(obj, k, v)
            obj.save(using=self.db)
        return obj, created

    def update_or_create(self, defaults=None, create_defaults=None, **kwargs):
        concretos_def, virtuales_def = self._separar_campos_virtuales(defaults)
        concretos_kw, virtuales_kw = self._separar_campos_virtuales(kwargs)
        if create_defaults is not None:
            concretos_cdef, virtuales_cdef = self._separar_campos_virtuales(create_defaults)
            obj, created = super().update_or_create(
                defaults=concretos_def,
                create_defaults=concretos_cdef,
                **concretos_kw
            )
            virtuales = {**virtuales_kw, **virtuales_cdef} if created else {**virtuales_kw, **virtuales_def}
        else:
            obj, created = super().update_or_create(defaults=concretos_def, **concretos_kw)
            virtuales = {**virtuales_kw, **virtuales_def}
        if virtuales:
            for k, v in virtuales.items():
                setattr(obj, k, v)
            obj.save(using=self.db)
        return obj, created


class ActivosManager(models.Manager):
    """
    Manager personalizado que filtra automáticamente los registros marcados
    como eliminados lógicamente (esta_eliminado=True).
    """

    def get_queryset(self):
        return ActivosQuerySet(self.model, using=self._db).filter(esta_eliminado=False)


class TodosManager(models.Manager):
    """Manager que incluye registros activos y eliminados lógicamente con soporte de anotaciones virtuales."""

    def get_queryset(self):
        return ActivosQuerySet(self.model, using=self._db)


class ModeloAuditable(models.Model):
    """
    Modelo abstracto base para todos los modelos operativos del sistema.
    Proporciona eliminación lógica y auditoría de creación / actualización.
    """
    creado_en = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creado en',
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        verbose_name='Actualizado en',
    )
    esta_eliminado = models.BooleanField(
        default=False,
        verbose_name='¿Está eliminado?',
        help_text='Indica si el registro fue eliminado lógicamente.',
    )

    objects = ActivosManager()
    todos = TodosManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            campos_concretos = {
                f.name for f in self._meta.concrete_fields
            } | {
                f.attname for f in self._meta.concrete_fields
            }
            filtrados = [f for f in update_fields if f in campos_concretos]
            if not filtrados:
                kwargs.pop('update_fields', None)
            else:
                kwargs['update_fields'] = filtrados
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """
        Eliminación lógica con validación de dependencias RESTRICT activas.
        """
        elementos_restringidos = []

        for rel in self._meta.related_objects:
            if rel.on_delete == models.RESTRICT:
                accessor_name = rel.get_accessor_name()
                try:
                    rel_target = getattr(self, accessor_name, None)
                except Exception:
                    continue

                if rel_target is None:
                    continue

                if rel.one_to_one:
                    esta_activo = True
                    if hasattr(rel_target, 'esta_eliminado'):
                        esta_activo = not rel_target.esta_eliminado
                    if esta_activo:
                        elementos_restringidos.append(rel_target)
                else:
                    if hasattr(rel.related_model, 'esta_eliminado'):
                        relacionados_activos = rel_target.filter(esta_eliminado=False)
                    else:
                        relacionados_activos = rel_target.all()

                    if relacionados_activos.exists():
                        elementos_restringidos.append(relacionados_activos.first())

        if elementos_restringidos:
            raise models.deletion.RestrictedError(
                f"No se puede eliminar lógicamente '{self}' porque existen registros activos que dependen de él.",
                elementos_restringidos
            )

        self.esta_eliminado = True
        self.save(update_fields=['esta_eliminado', 'actualizado_en'])

    def restaurar(self):
        """Restaura un registro eliminado lógicamente."""
        self.esta_eliminado = False
        self.save(update_fields=['esta_eliminado', 'actualizado_en'])


class GeneroChoices(models.TextChoices):
    MASCULINO = 'M', 'Masculino'
    FEMENINO  = 'F', 'Femenino'


class Persona(ModeloAuditable):
    """
    Modelo Supertipo que concentra la información personal común de todos
    los individuos del sistema (Estudiantes, Encargados y Personal).
    Actúa como única fuente de verdad (3FN) para nombres, apellidos y correo.
    """
    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='persona',
        verbose_name='Cuenta de acceso (Usuario)',
        help_text='Cuenta de acceso opcional asignada a la persona.'
    )
    cui = models.CharField(
        max_length=13,
        unique=True,
        validators=[MinLengthValidator(13), validador_cui_renap],
        verbose_name='CUI / DPI',
        help_text='Código Único de Identificación (DPI o CUI MINEDUC de 13 dígitos).'
    )
    nombres = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2)],
        verbose_name='Nombres'
    )
    apellidos = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2)],
        verbose_name='Apellidos'
    )
    fecha_nacimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de nacimiento'
    )
    genero = models.CharField(
        max_length=1,
        choices=GeneroChoices.choices,
        blank=True,
        verbose_name='Género'
    )
    direccion = models.TextField(
        max_length=300,
        blank=True,
        verbose_name='Dirección'
    )
    telefono_principal = models.CharField(
        max_length=8,
        blank=True,
        validators=[MinLengthValidator(8), validador_telefono_guatemala],
        verbose_name='Teléfono principal'
    )
    telefono_secundario = models.CharField(
        max_length=8,
        blank=True,
        validators=[MinLengthValidator(8), validador_telefono_guatemala],
        verbose_name='Teléfono secundario'
    )
    correo = models.EmailField(
        max_length=254,
        blank=True,
        verbose_name='Correo de contacto / comercial',
        help_text='Correo electrónico de contacto, independiente del email de usuario.'
    )

    class Meta:
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} (CUI: {self.cui})"

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"

    def save(self, *args, **kwargs):
        cui_anterior = None
        if self.pk:
            cui_anterior = Persona.objects.filter(pk=self.pk).values_list('cui', flat=True).first()
        super().save(*args, **kwargs)
        # sincronizacion hacia el usuario cuando se actualiza la persona
        if self.usuario_id:
            try:
                usuario = self.usuario
                campos_actualizar = []
                if (
                    self.cui
                    and not usuario.is_superuser
                    and usuario.username != self.cui
                    and (cui_anterior == usuario.username or usuario.username.isdigit())
                    and not usuario.__class__.objects.filter(username=self.cui).exclude(pk=usuario.pk).exists()
                ):
                    usuario.username = self.cui
                    campos_actualizar.append('username')
                if usuario.first_name != self.nombres:
                    usuario.first_name = self.nombres
                    campos_actualizar.append('first_name')
                if usuario.last_name != self.apellidos:
                    usuario.last_name = self.apellidos
                    campos_actualizar.append('last_name')
                if self.correo and usuario.email != self.correo:
                    usuario.email = self.correo
                    campos_actualizar.append('email')
                if campos_actualizar:
                    usuario.save(update_fields=campos_actualizar)
            except Exception:
                pass



class TipoDocumentoExpedienteChoices(models.TextChoices):
    """Catálogo normalizado (1FN/4FN) de documentos de expediente para Estudiantes y Personal."""
    CERT_NACIMIENTO_RENAP      = 'DOC_CERT_NACIMIENTO_RENAP',      'Certificado de Nacimiento RENAP'
    DPI_ENCARGADO              = 'DOC_DPI_ENCARGADO',              'Fotocopia DPI Encargado'
    CERTIFICADO_GRADO_ANTERIOR = 'DOC_CERTIFICADO_GRADO_ANTERIOR', 'Certificado del Grado Anterior'
    DIPLOMA_PRIMARIA           = 'DOC_DIPLOMA_PRIMARIA',           'Diploma de Primaria'
    CODIGO_MINEDUC             = 'DOC_CODIGO_MINEDUC',             'Constancia Código Personal MINEDUC'
    DPI_PERSONAL               = 'DOC_DPI_PERSONAL',               'Fotocopia DPI / CUI (RENAP)'
    NIT_SAT                    = 'DOC_NIT_SAT',                    'Constancia de NIT (RTU SAT)'
    TITULO_ACADEMICO           = 'DOC_TITULO_ACADEMICO',           'Fotocopia Título Académico / Cédula Docente'
    COLEGIADO_ACTIVO           = 'DOC_COLEGIADO_ACTIVO',           'Constancia Colegiado Activo / Registro MINEDUC'
    ANTECEDENTES_PENALES       = 'DOC_ANTECEDENTES_PENALES',       'Antecedentes Penales (Vigentes)'
    ANTECEDENTES_POLICIALES    = 'DOC_ANTECEDENTES_POLICIALES',    'Antecedentes Policiales (Vigentes)'
    CONTRATO_FISICO            = 'DOC_CONTRATO_FISICO',            'Contrato Físico Firmado'
    TARJETA_SALUD              = 'DOC_TARJETA_SALUD',              'Tarjeta de Salud / Sanidad'


class DocumentoExpediente(ModeloAuditable):
    """
    Relación normalizada en 4FN para el hecho multivaluado Persona ->> DocumentoExpediente.
    Elimina los grupos repetitivos de columnas booleanas doc_* en Estudiante y Personal.
    """
    persona = models.ForeignKey(
        Persona,
        on_delete=models.CASCADE,
        related_name='documentos_expediente',
        verbose_name='Persona'
    )
    tipo_documento = models.CharField(
        max_length=50,
        choices=TipoDocumentoExpedienteChoices.choices,
        verbose_name='Tipo de documento'
    )
    entregado = models.BooleanField(
        default=True,
        verbose_name='¿Entregado?'
    )

    class Meta:
        verbose_name = 'Documento de Expediente'
        verbose_name_plural = 'Documentos de Expediente'
        unique_together = [['persona', 'tipo_documento']]
        ordering = ['persona', 'tipo_documento']

    def __str__(self):
        estado = 'Entregado' if self.entregado else 'Pendiente'
        return f"{self.persona.nombre_completo} — {self.get_tipo_documento_display()} ({estado})"


class TipoVinculoContactoChoices(models.TextChoices):
    """Tipos de vínculo para contactos familiares o de emergencia asociados a una Persona."""
    PADRE      = 'PADRE',      'Padre'
    MADRE      = 'MADRE',      'Madre'
    EMERGENCIA = 'EMERGENCIA', 'Contacto de Emergencia'


class ContactoPersona(ModeloAuditable):
    """
    Relación normalizada en 3FN y 4FN para el hecho multivaluado Persona ->> ContactoPersona.
    Elimina la dependencia transitiva (Persona -> nombre_contacto -> telefono_contacto)
    y los campos repetitivos de padre, madre y emergencia en Estudiante y Personal.
    """
    persona = models.ForeignKey(
        Persona,
        on_delete=models.CASCADE,
        related_name='contactos_registrados',
        verbose_name='Persona'
    )
    tipo_vinculo = models.CharField(
        max_length=20,
        choices=TipoVinculoContactoChoices.choices,
        verbose_name='Tipo de vínculo'
    )
    nombre_completo = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(3)],
        verbose_name='Nombre completo del contacto'
    )
    telefono = models.CharField(
        max_length=8,
        blank=True,
        validators=[MinLengthValidator(8), validador_telefono_guatemala],
        verbose_name='Teléfono del contacto'
    )

    class Meta:
        verbose_name = 'Contacto de Persona'
        verbose_name_plural = 'Contactos de Personas'
        unique_together = [['persona', 'tipo_vinculo']]
        ordering = ['persona', 'tipo_vinculo']

    def __str__(self):
        return f"{self.persona.nombre_completo} — {self.get_tipo_vinculo_display()}: {self.nombre_completo}"

