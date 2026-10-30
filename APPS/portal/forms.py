"""
portal/forms.py

Formularios del Portal Web Público Institucional con validaciones de longitud,
seguridad anti-spam y formato para datos de Guatemala.
"""
import hashlib
import re
import time
from django import forms
from django.core import signing
from django.core.cache import cache
from APPS.core.forms import TailwindFormMixin
from APPS.core.validadores import limpiar_texto_longitud
from APPS.portal.models import SolicitudContacto, ConfiguracionPortal, FotoGaleria, ContenidoWeb

PALABRAS_SPAM = [
    'casino', 'viagra', 'cialis', 'cryptocurrency', 'crypto trading', 'bitcoin',
    'buy backlinks', 'seo ranking', 'telegram bot', 'adult dating', 'betting',
    'poker', 'porn', 'xxx', 'escort', 'loans', 'forex', 'lottery', 'binary options',
    'whatsapp group', 'earn money', 'passive income', 'guest post', 'backlink',
    'pharmacy', 'web traffic', 'apuestas online', 'hack', 'préstamos inmediatos',
    'dinero fácil', 'ganar dinero rápido', 'make money online', 'drug store',
    'weight loss', 'ketosis pills', 'invest in crypto', 'satta matka',
]


class SolicitudContactoForm(TailwindFormMixin, forms.ModelForm):
    """
    Formulario público para que padres de familia o encargados y solicitantes de información
    envíen dudas, consultas o solicitudes de información sobre inscripciones.
    """
    # campos trampa invisibles para deteccion de bots automatizados (honeypot)
    website_url = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'tabindex': '-1',
            'autocomplete': 'off',
            'style': 'display:none !important; position: absolute; left: -9999px;',
            'class': 'hidden',
        })
    )
    empresa_institucion = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'tabindex': '-1',
            'autocomplete': 'off',
            'style': 'display:none !important; position: absolute; left: -9999px;',
            'class': 'hidden',
        })
    )

    # token de seguridad firmado criptograficamente para verificar tiempo de llenado humano
    token_seguridad = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'class': 'hidden'})
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
        if not self.is_bound and not self.initial.get('token_seguridad'):
            self.fields['token_seguridad'].initial = signing.dumps(time.time())

    def clean_token_seguridad(self):
        token = self.cleaned_data.get('token_seguridad')
        if not token:
            if self.is_bound:
                raise forms.ValidationError('No se pudo verificar la autenticidad del formulario. Por favor recargue la página.')
            return token

        try:
            timestamp = signing.loads(token, max_age=7200)
            elapsed = time.time() - float(timestamp)
            if elapsed < 2.5:
                raise forms.ValidationError('El mensaje se envió de forma inmediata sin tiempo de lectura humana. Por favor verifique sus datos e intente de nuevo.')
        except forms.ValidationError:
            raise
        except signing.SignatureExpired:
            raise forms.ValidationError('El formulario ha expirado por inactividad. Por favor recargue la página e intente de nuevo.')
        except Exception:
            raise forms.ValidationError('Fallo de validación de seguridad anti-spam. Por favor recargue la página.')

        return token

    def clean_nombre_remitente(self):
        nombre = self.cleaned_data.get('nombre_remitente')
        if nombre:
            nombre = limpiar_texto_longitud(
                nombre,
                nombre_campo='El nombre del remitente',
                min_length=3,
                max_length=150,
                obligatorio=True,
                evitar_solo_numeros=True,
            )
            # bloqueo de caracteres cirilicos / no occidentales comunmente usados por spambots
            if re.search(r'[\u0400-\u04FF]', nombre):
                raise forms.ValidationError('El nombre contiene caracteres no permitidos.')
            if re.search(r'(https?://|www\.)', nombre, re.IGNORECASE):
                raise forms.ValidationError('El nombre no puede contener enlaces o direcciones web.')
            nom_lower = nombre.lower()
            for spam_word in PALABRAS_SPAM:
                if spam_word in nom_lower:
                    raise forms.ValidationError('El nombre contiene términos no permitidos.')
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
            asunto = limpiar_texto_longitud(asunto, 'El asunto', min_length=3, max_length=150)
            if re.search(r'[\u0400-\u04FF]', asunto):
                raise forms.ValidationError('El asunto contiene caracteres no permitidos.')
            if re.search(r'(https?://|www\.)', asunto, re.IGNORECASE):
                raise forms.ValidationError('No se permiten enlaces o páginas web en el asunto.')
            asunto_lower = asunto.lower()
            for spam_word in PALABRAS_SPAM:
                if spam_word in asunto_lower:
                    raise forms.ValidationError('El asunto contiene términos bloqueados por el filtro de seguridad.')
        return asunto or 'Consulta de Admisión e Información'

    def clean_mensaje(self):
        mensaje = self.cleaned_data.get('mensaje')
        if mensaje:
            mensaje = limpiar_texto_longitud(
                mensaje,
                nombre_campo='El mensaje o consulta',
                min_length=10,
                max_length=1000,
                obligatorio=True,
            )
            # bloqueo de caracteres cirilicos / no occidentales
            if re.search(r'[\u0400-\u04FF]', mensaje):
                raise forms.ValidationError('El mensaje contiene caracteres no permitidos por el filtro de seguridad.')

            # deteccion de hipervinculos externos y etiquetas html/bbcode
            urls_encontradas = re.findall(r'(https?://|www\.)', mensaje, re.IGNORECASE)
            if len(urls_encontradas) > 1:
                raise forms.ValidationError('Por medidas de seguridad escolar, no se permite incluir múltiples enlaces web en el mensaje.')
            elif len(urls_encontradas) == 1:
                raise forms.ValidationError('Por medidas de seguridad escolar, no se permite incluir enlaces web en el mensaje.')

            if re.search(r'(\[url=|<a\s+href=)', mensaje, re.IGNORECASE):
                raise forms.ValidationError('No se permite el uso de etiquetas de hipervínculos en el mensaje.')

            msg_lower = mensaje.lower()
            for spam_word in PALABRAS_SPAM:
                if spam_word in msg_lower:
                    raise forms.ValidationError('El mensaje contiene términos bloqueados por el filtro de seguridad.')

        return mensaje

    def clean_website_url(self):
        val = self.cleaned_data.get('website_url')
        if val:
            raise forms.ValidationError('Solicitud descartada por detección de actividad automatizada (Spam).')
        return val

    def clean_empresa_institucion(self):
        val = self.cleaned_data.get('empresa_institucion')
        if val:
            raise forms.ValidationError('Solicitud descartada por detección de actividad automatizada (Spam).')
        return val

    def clean(self):
        cleaned_data = super().clean()
        correo = cleaned_data.get('correo')
        mensaje = cleaned_data.get('mensaje')
        if correo and mensaje:
            content_hash = hashlib.md5(f"{correo}:{mensaje.strip().lower()}".encode('utf-8')).hexdigest()
            cache_key = f"portal_msg_hash_{content_hash}"
            if cache.get(cache_key):
                raise forms.ValidationError('Ya hemos recibido esta misma consulta recientemente. Nuestro equipo le responderá a la brevedad.')
        return cleaned_data


class ConfiguracionPortalForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para que la Dirección y Secretaría modifiquen la configuración del portal."""

    class Meta:
        model = ConfiguracionPortal
        fields = [
            'nombre_instituto', 'lema', 'hero_titulo', 'hero_descripcion',
            'mision', 'vision',
            # plan de estudios
            'plan_estudios_subtitulo',
            'descripcion_primero_basico', 'puntos_primero_basico',
            'descripcion_segundo_basico', 'puntos_segundo_basico',
            'descripcion_tercero_basico', 'puntos_tercero_basico',
            # requisitos de inscripcion
            'requisitos_subtitulo', 'requisitos_primero_basico', 'requisitos_traslados',
            # cuotas y atencion
            'telefono_principal', 'telefono_whatsapp',
            'correo_contacto', 'direccion_fisica', 'horario_atencion', 'jornada',
            'cuota_inscripcion', 'cuota_mensual', 'inscripciones_abiertas',
            'ciclo_escolar_activo', 'mostrar_cintillo_alerta', 'tipo_cintillo_alerta',
            'texto_cintillo_alerta', 'enlace_cintillo',
        ]
        widgets = {
            'hero_titulo': forms.TextInput(attrs={'placeholder': 'Ej. Instituto Básico por Cooperativa de Enseñanza...'}),
            'hero_descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripción destacada en la portada principal...'}),
            'mision': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Redacte la misión institucional...'}),
            'vision': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Redacte la visión institucional...'}),
            # plan de estudios
            'plan_estudios_subtitulo': forms.TextInput(attrs={'placeholder': 'Ej. Enseñanza integral orientada al desarrollo de competencias...'}),
            'descripcion_primero_basico': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descripción formativa de Primero Básico...'}),
            'puntos_primero_basico': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Una materia o aspecto por línea:\nMatemáticas y Razonamiento Lógico\n...'}),
            'descripcion_segundo_basico': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descripción formativa de Segundo Básico...'}),
            'puntos_segundo_basico': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Una materia o aspecto por línea:\nCiencias Naturales y Experimentación\n...'}),
            'descripcion_tercero_basico': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descripción formativa de Tercero Básico...'}),
            'puntos_tercero_basico': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Una materia o aspecto por línea:\nÁlgebra, Geometría y Estadística\n...'}),
            # requisitos de inscripcion
            'requisitos_subtitulo': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Indicación introductoria para la entrega del expediente...'}),
            'requisitos_primero_basico': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Un requisito por línea:\nCertificado de Nacimiento RENAP...\nDiploma de conclusión de Primaria...'}),
            'requisitos_traslados': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Un requisito por línea:\nCertificados de grados previos...\nSolvencia económica...'}),
            # contacto y avisos
            'texto_cintillo_alerta': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ej. ¡Inscripciones abiertas para el Ciclo Escolar 2026! Cupo limitado en Primero Básico.'}),
            'horario_atencion': forms.TextInput(attrs={'placeholder': 'Ej. Lunes a Viernes de 13:00 a 18:00 hrs'}),
            'jornada': forms.TextInput(attrs={'placeholder': 'Ej. Vespertina'}),
            'direccion_fisica': forms.TextInput(attrs={'placeholder': 'Colonia El Progreso, Escuintla'}),
            'enlace_cintillo': forms.TextInput(attrs={'placeholder': 'Ej. /admisiones/ o https://...'}),
        }


class FotoGaleriaForm(TailwindFormMixin, forms.ModelForm):
    """
    Formulario de alta y edición de fotografías para la galería.
    Recibe la URL externa (Google Drive, Cloudinary u otro servidor).
    """

    class Meta:
        model = FotoGaleria
        fields = ['titulo', 'descripcion', 'url_imagen', 'categoria', 'destacada_portada', 'orden', 'activo', 'fecha']
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Ej. Laboratorio de computación ciclo 2026'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Breve reseña o pie de foto explicativo...'}),
            'url_imagen': forms.URLInput(attrs={
                'placeholder': 'https://drive.google.com/file/d/... o URL directa de la imagen',
                'class': 'font-mono text-xs',
            }),
            'fecha': forms.DateInput(attrs={'type': 'date'}),
        }
        help_texts = {
            'url_imagen': 'Pegue el enlace compartido de Google Drive (asegúrese que esté configurado como "Cualquier persona con el enlace puede ver") o la URL directa de la foto.',
            'destacada_portada': 'Si se activa, la imagen se mostrará en la sección de galería destacada de la portada principal.',
        }


class ContenidoWebForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para la redacción y publicación de comunicados y noticias."""

    class Meta:
        model = ContenidoWeb
        fields = ['seccion', 'titulo', 'cuerpo', 'imagen_url', 'publicado', 'fecha_publicacion']
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Ej. Comunicado sobre entrega de boletas de calificaciones'}),
            'cuerpo': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Redacte aquí el texto del comunicado o noticia...'}),
            'imagen_url': forms.URLInput(attrs={'placeholder': 'https://... (URL de imagen o Google Drive opcional)'}),
            'fecha_publicacion': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class AtenderSolicitudContactoForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para que secretaría gestione una solicitud de información de un padre de familia o encargado."""

    class Meta:
        model = SolicitudContacto
        fields = ['atendido', 'notas_seguimiento']
        widgets = {
            'notas_seguimiento': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Anote el resultado del contacto: Ej. Se llamó al encargado, se resolvieron dudas sobre cuotas y papelería, vendrá a inscribir el jueves...',
            }),
        }
