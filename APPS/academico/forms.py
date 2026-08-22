"""
APPS/academico/forms.py

Formularios para la gestión del Módulo Académico del Instituto El Progreso.
Hereda de TailwindFormMixin (APPS.core.forms) para la inyección automática de estilos visuales.
"""
from decimal import Decimal
from django import forms

from APPS.core.forms import TailwindFormMixin
from APPS.academico.models import (
    CicloEscolar, BloqueAcademico, Grado, Seccion, Curso,
    AsignacionEstudiante, AsignacionDocente, NotaBloque, NotaFinalCurso, AsistenciaEstudiantil
)
from APPS.estudiantes.models import Estudiante
from APPS.rrhh.models import Personal


class CicloEscolarForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para aperturar o editar un Ciclo Escolar."""

    class Meta:
        model = CicloEscolar
        fields = ['anio', 'fecha_inicio', 'fecha_fin', 'estado_activo']
        labels = {
            'anio': 'Año Lectivo / Ciclo Escolar',
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_fin': 'Fecha de Finalización',
            'estado_activo': '¿Marcar como Ciclo Activo en el Sistema?',
        }
        widgets = {
            'anio': forms.NumberInput(attrs={'placeholder': 'Ej. 2026', 'min': '2020', 'max': '2050'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_anio(self):
        anio = self.cleaned_data.get('anio')
        if anio:
            qs = CicloEscolar.objects.filter(anio=anio, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f'El ciclo escolar {anio} ya se encuentra registrado.')
        return anio


class GradoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para gestionar los grados del Nivel Básico."""

    class Meta:
        model = Grado
        fields = ['nombre', 'orden']
        labels = {
            'nombre': 'Nombre del Grado Escolar',
            'orden': 'Orden de la Jerarquía (1, 2, 3...)',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej. Primero Básico, Segundo Básico'}),
            'orden': forms.NumberInput(attrs={'placeholder': '1', 'min': '1'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            nombre = nombre.strip()
            qs = Grado.objects.filter(nombre__iexact=nombre, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Ya existe un grado registrado con este nombre.')
        return nombre


class SeccionForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para gestionar las secciones dentro de un grado."""

    class Meta:
        model = Seccion
        fields = ['grado', 'letra', 'cupo_maximo']
        labels = {
            'grado': 'Grado Escolar Perteneciente',
            'letra': 'Letra de Sección (A, B, C...)',
            'cupo_maximo': 'Cupo Máximo de Estudiantes',
        }
        widgets = {
            'letra': forms.TextInput(attrs={'placeholder': 'Ej. A', 'maxlength': '1'}),
            'cupo_maximo': forms.NumberInput(attrs={'placeholder': '35', 'min': '1'}),
        }

    def clean_letra(self):
        letra = self.cleaned_data.get('letra')
        if letra:
            letra = letra.strip().upper()
        return letra

    def clean(self):
        cleaned_data = super().clean()
        grado = cleaned_data.get('grado')
        letra = cleaned_data.get('letra')

        if grado and letra:
            qs = Seccion.objects.filter(grado=grado, letra=letra, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f'La sección {letra} ya existe para {grado.nombre}.')
        return cleaned_data


class CursoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para crear y editar asignaturas del Pensum MINEDUC."""

    class Meta:
        model = Curso
        fields = ['grado', 'nombre_curso', 'codigo_curso']
        labels = {
            'grado': 'Grado del Pensum',
            'nombre_curso': 'Nombre de la Asignatura / Curso',
            'codigo_curso': 'Código del Curso (MINEDUC)',
        }
        widgets = {
            'nombre_curso': forms.TextInput(attrs={'placeholder': 'Ej. Matemáticas I, Comunicación y Lenguaje I'}),
            'codigo_curso': forms.TextInput(attrs={'placeholder': 'Ej. MAT-101'}),
        }

    def clean_codigo_curso(self):
        codigo = self.cleaned_data.get('codigo_curso')
        if codigo:
            codigo = codigo.strip().upper()
            qs = Curso.objects.filter(codigo_curso=codigo, esta_eliminado=False)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f'El código de curso "{codigo}" ya está en uso.')
        return codigo


class AsignacionEstudianteForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para inscribir a un alumno en una Sección para un Ciclo Lectivo."""

    class Meta:
        model = AsignacionEstudiante
        fields = ['estudiante', 'seccion', 'ciclo_escolar']
        labels = {
            'estudiante': 'Estudiante a Inscribir',
            'seccion': 'Grado y Sección Asignada',
            'ciclo_escolar': 'Ciclo Escolar Lectivo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estudiante'].queryset = Estudiante.objects.filter(
            persona__esta_eliminado=False,
            estado_estudiante='ACTIVO'
        ).select_related('persona').order_by('persona__apellidos', 'persona__nombres')
        
        self.fields['seccion'].queryset = Seccion.objects.filter(
            esta_eliminado=False
        ).select_related('grado').order_by('grado__orden', 'letra')
        
        self.fields['ciclo_escolar'].queryset = CicloEscolar.objects.filter(esta_eliminado=False)

        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True, esta_eliminado=False)
            if not self.is_bound and not self.initial.get('ciclo_escolar'):
                self.initial['ciclo_escolar'] = ciclo_activo
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            pass

    def clean(self):
        cleaned_data = super().clean()
        estudiante = cleaned_data.get('estudiante')
        ciclo = cleaned_data.get('ciclo_escolar')
        seccion = cleaned_data.get('seccion')

        if estudiante and ciclo:
            qs = AsignacionEstudiante.objects.filter(
                estudiante=estudiante,
                ciclo_escolar=ciclo,
                esta_eliminado=False
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'El estudiante {estudiante.persona.nombre_completo} ya está inscrito en el ciclo escolar {ciclo.anio}.'
                )

        # Validar cupo máximo de la sección
        if seccion and ciclo and not (self.instance and self.instance.pk):
            inscritos_actuales = AsignacionEstudiante.objects.filter(
                seccion=seccion,
                ciclo_escolar=ciclo,
                esta_eliminado=False
            ).count()
            if inscritos_actuales >= seccion.cupo_maximo:
                raise forms.ValidationError(
                    f'La sección {seccion} ha alcanzado su cupo máximo de {seccion.cupo_maximo} estudiantes.'
                )
        return cleaned_data


class AsignacionDocenteForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para asignar la carga académica a un docente."""

    class Meta:
        model = AsignacionDocente
        fields = ['personal', 'curso', 'seccion', 'ciclo_escolar']
        labels = {
            'personal': 'Docente Asignado',
            'curso': 'Curso / Materia del Pensum',
            'seccion': 'Grado y Sección',
            'ciclo_escolar': 'Ciclo Escolar Lectivo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['personal'].queryset = Personal.objects.filter(
            persona__esta_eliminado=False,
            estado_laboral='ACTIVO'
        ).select_related('persona').order_by('persona__apellidos', 'persona__nombres')

        self.fields['curso'].queryset = Curso.objects.filter(
            esta_eliminado=False
        ).select_related('grado').order_by('grado__orden', 'nombre_curso')

        self.fields['seccion'].queryset = Seccion.objects.filter(
            esta_eliminado=False
        ).select_related('grado').order_by('grado__orden', 'letra')

        self.fields['ciclo_escolar'].queryset = CicloEscolar.objects.filter(esta_eliminado=False)

        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True, esta_eliminado=False)
            if not self.is_bound and not self.initial.get('ciclo_escolar'):
                self.initial['ciclo_escolar'] = ciclo_activo
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            pass

    def clean(self):
        cleaned_data = super().clean()
        personal = cleaned_data.get('personal')
        curso = cleaned_data.get('curso')
        seccion = cleaned_data.get('seccion')
        ciclo = cleaned_data.get('ciclo_escolar')

        if curso and seccion and curso.grado != seccion.grado:
            raise forms.ValidationError(
                f'El curso "{curso.nombre_curso}" pertenece a {curso.grado.nombre}, pero ha seleccionado la sección {seccion}.'
            )

        if personal and curso and seccion and ciclo:
            qs = AsignacionDocente.objects.filter(
                personal=personal,
                curso=curso,
                seccion=seccion,
                ciclo_escolar=ciclo,
                esta_eliminado=False
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'El docente {personal.persona.nombre_completo} ya tiene asignada la materia {curso.nombre_curso} en {seccion} para el ciclo {ciclo.anio}.'
                )
        return cleaned_data


class NotaRecuperacionForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para ingresar pruebas de recuperación a una NotaFinalCurso."""

    class Meta:
        model = NotaFinalCurso
        fields = ['nota_recuperacion_1', 'nota_recuperacion_2']
        labels = {
            'nota_recuperacion_1': 'Nota Pruebas de Recuperación 1 (0-100 pts)',
            'nota_recuperacion_2': 'Nota Pruebas de Recuperación 2 (0-100 pts)',
        }
        widgets = {
            'nota_recuperacion_1': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0', 'max': '100'}),
            'nota_recuperacion_2': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0', 'max': '100'}),
        }


class AsistenciaSeccionForm(TailwindFormMixin, forms.Form):
    """Formulario para la captura diaria masiva de asistencia por sección."""

    seccion = forms.ModelChoiceField(
        queryset=Seccion.objects.filter(esta_eliminado=False).select_related('grado'),
        label='Seleccionar Sección'
    )
    curso = forms.ModelChoiceField(
        queryset=Curso.objects.filter(esta_eliminado=False).select_related('grado'),
        label='Seleccionar Curso'
    )
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha de Asistencia'
    )
