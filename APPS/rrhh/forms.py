"""
APPS/rrhh/forms.py

Formularios para la contratación y gestión de Personal laboral del Instituto El Progreso.
Hereda de TailwindFormMixin (APPS.core.forms) para la inyección de estilos corporativos.
"""
from django import forms
from APPS.core.forms import TailwindFormMixin
from APPS.rrhh.models import Personal, Puesto


class PersonalForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para capturar y modificar los datos laborales, custodia de contrato físico y papelería del Empleado."""

    class Meta:
        model = Personal
        fields = [
            'puesto',
            'nit',
            'fecha_contratacion',
            'estado_laboral',
            'salario_base_asignado',
            'numero_contrato_fisico',
            'ubicacion_expediente_fisico',
            'contacto_emergencia_nombre',
            'contacto_emergencia_telefono',
            # Checklist Papelería Obligatoria Nivel Medio
            'doc_dpi_personal',
            'doc_nit_sat',
            'doc_titulo_academico',
            'doc_colegiado_activo',
            'doc_antecedentes_penales',
            'doc_antecedentes_policiales',
            'doc_contrato_fisico',
            'doc_tarjeta_salud',
        ]
        labels = {
            'puesto': 'Puesto o Cargo Asignado',
            'nit': 'NIT (Número de Identificación Tributaria)',
            'fecha_contratacion': 'Fecha de Contratación',
            'estado_laboral': 'Estado Laboral',
            'salario_base_asignado': 'Salario Base Mensual (Q)',
            'numero_contrato_fisico': 'No. Correlativo de Contrato Físico',
            'ubicacion_expediente_fisico': 'Ubicación Físico (Archivador/Carpeta)',
            'contacto_emergencia_nombre': 'Nombre de Contacto de Emergencia',
            'contacto_emergencia_telefono': 'Teléfono de Contacto de Emergencia',
            'doc_dpi_personal': '1. Fotocopia de DPI / CUI (RENAP)',
            'doc_nit_sat': '2. Constancia de NIT (RTU SAT)',
            'doc_titulo_academico': '3. Fotocopia de Título Académico / Cédula Docente',
            'doc_colegiado_activo': '4. Constancia Colegiado Activo / Acreditación MINEDUC',
            'doc_antecedentes_penales': '5. Antecedentes Penales (Vigentes)',
            'doc_antecedentes_policiales': '6. Antecedentes Policiales (Vigentes)',
            'doc_contrato_fisico': '7. Contrato Físico Firmado',
            'doc_tarjeta_salud': '8. Tarjeta de Salud / Sanidad',
        }
        widgets = {
            'fecha_contratacion': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_salario_base_asignado(self):
        salario = self.cleaned_data.get('salario_base_asignado')
        if salario is not None and salario < 0:
            raise forms.ValidationError("El salario base asignado no puede ser un valor negativo.")
        return salario

    def clean_nit(self):
        nit = self.cleaned_data.get('nit', '').strip().upper()
        if nit and len(nit) < 3:
            raise forms.ValidationError("El NIT ingresado debe tener un formato válido.")
        return nit

