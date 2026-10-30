"""
APPS/disciplina/forms.py

Formularios para el registro de incidentes disciplinarios y emisión de citaciones
a padres de familia o encargados con soporte de Tailwind CSS y validaciones operativas
conforme al Acuerdo Ministerial 01-2011 del MINEDUC (Guatemala).
"""
from datetime import date
from django import forms
from django.utils import timezone
from APPS.core.forms import TailwindFormMixin
from APPS.core.validadores import limpiar_texto_longitud
from APPS.disciplina.models import IncidenteDisciplinario, CitacionPadre, EstadoCitacionChoices
from APPS.estudiantes.models import Estudiante
from APPS.academico.models import CicloEscolar


class IncidenteDisciplinarioForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para reportar o actualizar una falta disciplinaria de un estudiante."""

    class Meta:
        model = IncidenteDisciplinario
        fields = [
            'estudiante',
            'ciclo_escolar',
            'fecha',
            'hora',
            'lugar',
            'tipo_falta',
            'categoria',
            'descripcion_hechos',
            'descargo_estudiante',
            'medida_formativa',
            'requiere_citacion',
            'esta_resuelto',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora': forms.TimeInput(attrs={'type': 'time'}),
            'lugar': forms.TextInput(attrs={
                'minlength': '3',
                'maxlength': '150',
                'placeholder': 'Ej. Aula 102, Patio Central, Laboratorio de Computación',
            }),
            'descripcion_hechos': forms.Textarea(attrs={
                'rows': 3,
                'minlength': '10',
                'maxlength': '1000',
                'placeholder': 'Relate con claridad y objetividad los hechos observados (10 a 1,000 caracteres)...',
            }),
            'descargo_estudiante': forms.Textarea(attrs={
                'rows': 2,
                'maxlength': '1000',
                'placeholder': 'Declaración u observaciones expresadas por el estudiante durante la audiencia...',
            }),
            'medida_formativa': forms.Textarea(attrs={
                'rows': 2,
                'maxlength': '1000',
                'placeholder': 'Acción correctiva pedagógica acordada (ej. amonestación escrita, labor formativa)...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estudiante'].queryset = Estudiante.objects.filter(
            persona__esta_eliminado=False,
            estado_estudiante='ACTIVO'
        ).select_related('persona').order_by('persona__apellidos', 'persona__nombres')
        self.fields['estudiante'].widget.attrs.update({
            'class': 'searchable-select',
            'data-placeholder': 'Buscar estudiante por nombre, DPI o código MINEDUC...',
        })

        self.fields['ciclo_escolar'].queryset = CicloEscolar.objects.all().order_by('-estado_activo', '-anio')
        if not self.initial.get('ciclo_escolar') and not getattr(self.instance, 'ciclo_escolar_id', None):
            ciclo_activo = CicloEscolar.objects.filter(estado_activo=True).first()
            if ciclo_activo:
                self.fields['ciclo_escolar'].initial = ciclo_activo

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha > date.today():
            raise forms.ValidationError('La fecha del incidente disciplinario no puede ser una fecha futura.')
        return fecha

    def clean_lugar(self):
        lugar = self.cleaned_data.get('lugar')
        if lugar:
            return limpiar_texto_longitud(lugar, 'El lugar de los hechos', min_length=3, max_length=150, obligatorio=True)
        return lugar

    def clean_descripcion_hechos(self):
        desc = self.cleaned_data.get('descripcion_hechos')
        if desc:
            return limpiar_texto_longitud(
                desc,
                nombre_campo='La descripción de los hechos',
                min_length=10,
                max_length=1000,
                obligatorio=True,
            )
        return desc

    def clean_descargo_estudiante(self):
        val = self.cleaned_data.get('descargo_estudiante')
        if val:
            return limpiar_texto_longitud(val, 'El descargo del estudiante', min_length=3, max_length=1000)
        return val

    def clean_medida_formativa(self):
        val = self.cleaned_data.get('medida_formativa')
        if val:
            return limpiar_texto_longitud(val, 'La medida formativa', min_length=3, max_length=1000)
        return val

    def clean(self):
        cleaned_data = super().clean()
        requiere_citacion = cleaned_data.get('requiere_citacion')
        esta_resuelto = cleaned_data.get('esta_resuelto')
        fecha = cleaned_data.get('fecha')
        ciclo = cleaned_data.get('ciclo_escolar')

        # si requiere citacion y no hay citacion atendida, no debe marcarse como resuelto inicialmente
        if requiere_citacion and esta_resuelto:
            tiene_citacion_atendida = (
                getattr(self.instance, 'citacion', None) and
                self.instance.citacion.estado == EstadoCitacionChoices.ATENDIDA
            )
            if not tiene_citacion_atendida:
                self.add_error(
                    'esta_resuelto',
                    'Un incidente que requiere citación al padre de familia o encargado no puede darse por resuelto y cerrado antes de celebrar la comparecencia y suscribir compromisos.'
                )

        # validacion del rango de fechas respecto al ciclo escolar seleccionado
        if fecha and ciclo:
            if ciclo.fecha_inicio and fecha < ciclo.fecha_inicio:
                self.add_error(
                    'fecha',
                    f'La fecha ({fecha.strftime("%d/%m/%Y")}) es anterior a la fecha de inicio del ciclo escolar {ciclo.anio} ({ciclo.fecha_inicio.strftime("%d/%m/%Y")}).'
                )
            if ciclo.fecha_fin and fecha > ciclo.fecha_fin:
                self.add_error(
                    'fecha',
                    f'La fecha ({fecha.strftime("%d/%m/%Y")}) es posterior a la fecha de finalización del ciclo escolar {ciclo.anio} ({ciclo.fecha_fin.strftime("%d/%m/%Y")}).'
                )

        return cleaned_data


class CitacionPadreForm(TailwindFormMixin, forms.ModelForm):
    """Formulario para emitir y registrar el resultado de una citación a padres de familia o encargados."""

    class Meta:
        model = CitacionPadre
        fields = [
            'fecha_hora_citacion',
            'motivo_citacion',
            'lugar',
            'atendido_por',
            'estado',
            'acuerdos_alcanzados',
            'observaciones_seguimiento',
            'notificacion_enviada',
        ]
        widgets = {
            'fecha_hora_citacion': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'motivo_citacion': forms.TextInput(attrs={
                'minlength': '5',
                'maxlength': '255',
                'placeholder': 'Motivo formal para comparecencia del padre de familia o encargado',
            }),
            'lugar': forms.TextInput(attrs={
                'minlength': '3',
                'maxlength': '150',
                'placeholder': 'Ej. Dirección / Coordinación Pedagógica',
            }),
            'acuerdos_alcanzados': forms.Textarea(attrs={
                'rows': 3,
                'maxlength': '1000',
                'placeholder': 'Acuerdos formales de apoyo mutuo y compromisos de convivencia firmados...',
            }),
            'observaciones_seguimiento': forms.Textarea(attrs={
                'rows': 2,
                'maxlength': '1000',
                'placeholder': 'Notas internas para dar seguimiento en las próximas semanas...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_hora_citacion'].input_formats = [
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
        ]
        # formatear el valor inicial de fecha_hora_citacion para el input html5 datetime-local
        if self.instance and self.instance.pk and self.instance.fecha_hora_citacion:
            fecha_local = timezone.localtime(self.instance.fecha_hora_citacion) if timezone.is_aware(self.instance.fecha_hora_citacion) else self.instance.fecha_hora_citacion
            self.initial['fecha_hora_citacion'] = fecha_local.strftime('%Y-%m-%dT%H:%M')

        from django.contrib.auth import get_user_model
        UsuarioModel = get_user_model()
        # solo personal autorizado del plantel (no cuentas de estudiantes ni encargados)
        self.fields['atendido_por'].queryset = UsuarioModel.objects.filter(
            is_active=True
        ).exclude(
            rol__in=['ESTUDIANTE', 'ENCARGADO']
        ).order_by('first_name', 'last_name')

    def clean_motivo_citacion(self):
        motivo = self.cleaned_data.get('motivo_citacion')
        if motivo:
            return limpiar_texto_longitud(motivo, 'El motivo de la citación', min_length=5, max_length=255, obligatorio=True)
        return motivo

    def clean_lugar(self):
        lugar = self.cleaned_data.get('lugar')
        if lugar:
            return limpiar_texto_longitud(lugar, 'El lugar de reunión', min_length=3, max_length=150, obligatorio=True)
        return lugar

    def clean_acuerdos_alcanzados(self):
        val = self.cleaned_data.get('acuerdos_alcanzados')
        if val:
            return limpiar_texto_longitud(val, 'Los acuerdos alcanzados', min_length=3, max_length=1000)
        return val

    def clean_observaciones_seguimiento(self):
        val = self.cleaned_data.get('observaciones_seguimiento')
        if val:
            return limpiar_texto_longitud(val, 'Las observaciones de seguimiento', min_length=3, max_length=1000)
        return val

    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get('estado')
        acuerdos = cleaned_data.get('acuerdos_alcanzados')
        fecha_hora = cleaned_data.get('fecha_hora_citacion')

        # si se marca como atendida, los acuerdos son obligatorios conforme a la normativa
        if estado == EstadoCitacionChoices.ATENDIDA and not acuerdos:
            self.add_error(
                'acuerdos_alcanzados',
                'Debe registrar los acuerdos y compromisos asumidos cuando la citación se marca como Atendida conforme al Acuerdo 01-2011.'
            )

        # validar que una nueva citacion programada no sea en el pasado
        if not self.instance.pk and fecha_hora:
            ahora = timezone.now()
            # margen de 15 minutos de tolerancia
            if fecha_hora < (ahora - timezone.timedelta(minutes=15)):
                self.add_error(
                    'fecha_hora_citacion',
                    'La fecha y hora de una nueva citación no puede programarse en el pasado.'
                )

        return cleaned_data


# alias para compatibilidad con llamadas previas
IncidenteConductualForm = IncidenteDisciplinarioForm
