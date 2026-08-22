"""
APPS/estudiantes/forms.py

Formularios para el registro y gestión de Estudiantes y Encargados.
Hereda de TailwindFormMixin (APPS.core.forms) para la inyección automática de estilos visuales.
"""
from django import forms
from APPS.core.forms import TailwindFormMixin, PersonaForm
from APPS.estudiantes.models import Estudiante, Encargado, EstudianteEncargado
from APPS.academico.models import Seccion


class EstudianteForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para capturar los datos académicos y de expediente de un Estudiante."""

    seccion_asignada = forms.ModelChoiceField(
        queryset=Seccion.objects.filter(esta_eliminado=False).select_related('grado').order_by('grado__orden', 'letra'),
        required=False,
        label='Grado y Sección Académica Asignada (Matrícula Inmediata)',
        help_text='Seleccione para matricular e inscribir al alumno en el Módulo Académico con 1 solo clic.'
    )

    class Meta:
        model = Estudiante
        fields = [
            'codigo_mineduc',
            'estado_estudiante',
            'encargado',
            'nombre_padre',
            'telefono_padre',
            'nombre_madre',
            'telefono_madre',
            'historial_medico',
            'doc_cert_nacimiento_renap',
            'doc_dpi_encargado',
            'doc_certificado_grado_anterior',
            'doc_diploma_primaria',
            'doc_codigo_mineduc',
            'estado_activo',
        ]
        labels = {
            'codigo_mineduc': 'Código Oficial MINEDUC',
            'estado_estudiante': 'Estado Académico del Alumno',
            'encargado': 'Encargado / Tutor Legal Principal',
            'nombre_padre': 'Nombre Completo del Padre',
            'telefono_padre': 'Teléfono del Padre',
            'nombre_madre': 'Nombre Completo de la Madre',
            'telefono_madre': 'Teléfono de la Madre',
            'historial_medico': 'Historial Médico / Observaciones de Salud',
            'doc_cert_nacimiento_renap': 'Certificado de Nacimiento RENAP (con CUI)',
            'doc_dpi_encargado': 'Fotocopia de DPI del Encargado / Padre',
            'doc_certificado_grado_anterior': 'Certificado de Estudios del Grado Anterior',
            'doc_diploma_primaria': 'Diploma de Educación Primaria (para 1ro Básico)',
            'doc_codigo_mineduc': 'Constancia de Código Personal MINEDUC (SIRE)',
            'estado_activo': '¿Estudiante Activo en el Instituto?',
        }
        widgets = {
            'historial_medico': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Alergias, medicamentos, antecedentes u observaciones médicas...'}),
            'nombre_padre': forms.TextInput(attrs={'placeholder': 'Nombre completo del padre'}),
            'telefono_padre': forms.TextInput(attrs={'placeholder': 'Ej. 5555-5555'}),
            'nombre_madre': forms.TextInput(attrs={'placeholder': 'Nombre completo de la madre'}),
            'telefono_madre': forms.TextInput(attrs={'placeholder': 'Ej. 4444-4444'}),
        }

    def clean_codigo_mineduc(self):
        codigo = self.cleaned_data.get('codigo_mineduc')
        if codigo:
            codigo = codigo.strip().upper()
        return codigo

    def clean_encargado(self):
        encargado = self.cleaned_data.get('encargado')
        if not encargado:
            raise forms.ValidationError('Debe seleccionar obligatoriamente un Encargado / Tutor Legal Principal para el alumno.')
        return encargado


class EncargadoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para capturar los datos de un Encargado / Tutor Legal (Subtipo)."""

    class Meta:
        model = Encargado
        fields = [
            'lugar_de_trabajo',
        ]
        labels = {
            'lugar_de_trabajo': 'Lugar de trabajo / Empresa',
        }
