"""
portal/forms.py

Formularios del Portal Web Público Institucional con validaciones de longitud
y formato para datos de Guatemala.
"""
from django import forms
from APPS.core.forms import TailwindFormMixin
from APPS.core.validadores import limpiar_texto_longitud
from APPS.portal.models import SolicitudContacto


class SolicitudContactoForm(TailwindFormMixin, forms.ModelForm):
    """
    Formulario público para que padres de familia o encargados y prospectos
    envíen dudas, consultas o solicitudes de información sobre inscripciones.
    """
    # campo de seguridad para deteccion de envios automatizados
    website_url = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'tabindex': '-1',
            'autocomplete': 'off',
            'style': 'display:none !important;',
            'class': 'hidden',
        })
    )

    class Meta:
        model = SolicitudContacto
        fields = ['nombre_remitente', 'correo', 'telefono', 'asunto', 'mensaje']
        labels = {
            'nombre_remitente': 'Nombre Completo',
            'correo': 'Correo Electrónico',
            'telefono': 'Teléfono o WhatsApp (8 dígitos)',
            'asunto': 'Asunto o Motivo de Consulta',
            'mensaje': 'Mensaje o Consulta Detallada',
        }
        widgets = {
            'nombre_remitente': forms.TextInput(attrs={
                'minlength': '3',
                'maxlength': '150',
                'placeholder': 'Ej. Juan Antonio Pérez Gómez',
                'required': True,
            }),
            'correo': forms.EmailInput(attrs={
                'maxlength': '254',
                'placeholder': 'ejemplo@correo.com',
                'required': True,
            }),
            'telefono': forms.TextInput(attrs={
                'minlength': '8',
                'maxlength': '8',
                'pattern': r'\d{8}',
                'inputmode': 'numeric',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '').slice(0, 8)",
                'placeholder': 'Ej. 55551234',
                'title': 'Ingrese un número telefónico de Guatemala de exactamente 8 dígitos numéricos.',
                'required': True,
            }),
            'asunto': forms.TextInput(attrs={
                'minlength': '3',
                'maxlength': '150',
                'placeholder': 'Ej. Información sobre inscripción para Primero Básico',
                'required': True,
            }),
            'mensaje': forms.Textarea(attrs={
                'rows': 4,
                'minlength': '10',
                'maxlength': '1000',
                'placeholder': 'Escriba aquí su consulta o dudas respecto a cuotas escolares, requisitos, papelería o becas...',
                'required': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'telefono' in self.fields:
            self.fields['telefono'].validators = []

    def clean_nombre_remitente(self):
        nombre = self.cleaned_data.get('nombre_remitente')
        if nombre:
            return limpiar_texto_longitud(
                nombre,
                nombre_campo='El nombre del remitente',
                min_length=3,
                max_length=150,
                obligatorio=True,
                evitar_solo_numeros=True,
            )
        return nombre

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if correo:
            correo = correo.strip().lower()
            if len(correo) > 254:
                raise forms.ValidationError('El correo electrónico no puede exceder los 254 caracteres.')
        return correo

    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono')
        if tel:
            limpio = tel.strip()
            digits = ''.join(c for c in limpio if c.isdigit())
            if len(digits) < 8:
                raise forms.ValidationError('Por favor ingrese un número de teléfono válido (mínimo 8 dígitos).')
            if len(limpio) != 8 or not limpio.isdigit():
                raise forms.ValidationError('El número de teléfono o celular en Guatemala debe contener exactamente 8 dígitos numéricos.')
            return limpio
        return tel

    def clean_asunto(self):
        asunto = self.cleaned_data.get('asunto')
        if asunto:
            return limpiar_texto_longitud(asunto, 'El asunto', min_length=3, max_length=150)
        return 'Consulta de Admisión e Información'

    def clean_mensaje(self):
        mensaje = self.cleaned_data.get('mensaje')
        if mensaje:
            return limpiar_texto_longitud(
                mensaje,
                nombre_campo='El mensaje o consulta',
                min_length=10,
                max_length=1000,
                obligatorio=True,
            )
        return mensaje

    def clean_website_url(self):
        val = self.cleaned_data.get('website_url')
        if val:
            raise forms.ValidationError('Solicitud descartada por detección de actividad automatizada (Spam).')
        return val
