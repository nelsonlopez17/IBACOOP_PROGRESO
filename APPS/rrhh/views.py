"""
APPS/rrhh/views.py

Vistas Basadas en Clases (CBV) para Recursos Humanos y Contratación de Personal.
Implementa la creación transaccional atómica (transaction.atomic()) y la autogeneración
inteligente de usernames (ej. jgomez) con manejo de duplicados y asignación dinámica de rol.
"""
import unicodedata
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages

from APPS.usuarios.models import Usuario, RolChoices
from APPS.core.models import Persona
from APPS.rrhh.models import Personal, Puesto
from APPS.core.forms import PersonaForm
from APPS.rrhh.forms import PersonalForm


def normalizar_cadena(texto: str) -> str:
    """Elimina tildes, acentos y caracteres especiales dejando únicamente letras minúsculas."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFD', texto)
    sin_tildes = ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return ''.join([c for c in sin_tildes if c.isalnum()]).lower()


def mapear_rol_segun_puesto(puesto: Puesto) -> str:
    """
    Determina dinámicamente el RolChoices adecuado analizando la descripción o título del Puesto.
    """
    nombre_puesto = puesto.nombre_puesto.upper()
    
    if "DIRECTOR" in nombre_puesto or "DIRECTORA" in nombre_puesto:
        return RolChoices.DIRECTOR
    elif "SECRETARIA" in nombre_puesto or "SECRETARIO" in nombre_puesto:
        return RolChoices.SECRETARIA
    elif "CONTADOR" in nombre_puesto or "CONTADORA" in nombre_puesto:
        return RolChoices.CONTADOR
    elif any(k in nombre_puesto for k in ["DOCENTE", "PROFESOR", "PROFESORA", "CATEDRATICO", "MAESTRO"]):
        return RolChoices.DOCENTE
    else:
        return RolChoices.DOCENTE  # Rol por defecto para personal general


class PersonalListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista todos los colaboradores activos de la institución."""
    login_url = 'usuarios:login'
    permission_required = 'rrhh.view_personal'
    model = Personal
    template_name = 'rrhh/personal_list.html'
    context_object_name = 'personal_list'
    paginate_by = 15

    def get_queryset(self):
        return Personal.objects.select_related('persona', 'puesto', 'persona__usuario').filter(esta_eliminado=False)


class PersonalCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    CBV para la contratación y registro de un nuevo colaborador (Personal).
    Procesa en una transacción atómica:
      1. Generación inteligente de username (ej. jgomez / jgomez456 en colisión) y mapeo dinámico de rol.
      2. Creación del registro Persona.
      3. Creación del registro Personal.
    """
    login_url = 'usuarios:login'
    permission_required = 'rrhh.add_personal'
    model = Personal
    form_class = PersonalForm
    template_name = 'rrhh/personal_form.html'
    success_url = reverse_lazy('rrhh:personal_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'persona_form' not in context:
            context['persona_form'] = PersonaForm(self.request.POST or None)
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        persona_form = PersonaForm(request.POST)

        if form.is_valid() and persona_form.is_valid():
            return self.forms_valid(form, persona_form)
        else:
            return self.forms_invalid(form, persona_form)

    def forms_valid(self, form, persona_form):
        try:
            with transaction.atomic():
                persona_data = persona_form.cleaned_data
                personal_data = form.cleaned_data
                puesto_seleccionado = personal_data['puesto']
                
                # 1. Generar Username base: 1ra letra primer nombre + primer apellido
                primer_nombre = normalizar_cadena(persona_data['nombres'].split()[0])
                primer_apellido = normalizar_cadena(persona_data['apellidos'].split()[0])
                username_base = f"{primer_nombre[0] if primer_nombre else 'e'}{primer_apellido}"

                # Manejo inteligente de colisiones / duplicados usando CUI
                cui = persona_data.get('cui', '000')
                username_final = username_base
                if Usuario.objects.filter(username=username_final).exists():
                    # Añadir últimos 3 dígitos del DPI/CUI
                    ultimos_digitos = cui[-3:] if len(cui) >= 3 else '123'
                    username_final = f"{username_base}{ultimos_digitos}"

                # En caso extremo de persistir colisión, agregar número secuencial
                contador = 1
                username_candidato = username_final
                while Usuario.objects.filter(username=username_candidato).exists():
                    username_candidato = f"{username_final}{contador}"
                    contador += 1
                username_final = username_candidato

                # 2. Mapeo dinámico de rol según el puesto
                rol_asignado = mapear_rol_segun_puesto(puesto_seleccionado)
                clave_temporal = "Empleado.2026!"

                # 3. Crear cuenta de Usuario
                usuario = Usuario.objects.create_user(
                    username=username_final,
                    email=persona_data.get('correo', ''),
                    password=clave_temporal,
                    first_name=persona_data['nombres'],
                    last_name=persona_data['apellidos'],
                    rol=rol_asignado
                )

                # 4. Crear Persona vinculada al Usuario
                persona = persona_form.save(commit=False)
                persona.usuario = usuario
                persona.save()

                # 5. Crear Subtipo Personal vinculado a Persona
                personal = form.save(commit=False)
                personal.persona = persona
                personal.save()

            messages.success(
                self.request,
                f"Colaborador '{persona.nombre_completo}' contratado exitosamente como '{puesto_seleccionado.nombre_puesto}'. "
                f"Cuenta de acceso autogenerada -> Usuario: {usuario.username} | Rol: {rol_asignado} | Clave Temporal: {clave_temporal}"
            )
            return super().form_valid(form)

        except Exception as e:
            messages.error(self.request, f"Error al registrar al colaborador: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        messages.error(self.request, "Por favor corrija los errores marcados en el formulario.")
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )
