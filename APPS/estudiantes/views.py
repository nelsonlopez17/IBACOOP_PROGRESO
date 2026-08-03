"""
APPS/estudiantes/views.py

Vistas Basadas en Clases (CBV) para la gestión de Estudiantes y Encargados.
Implementa transacciones atómicas (transaction.atomic()) y la creación automatizada
de cuentas de Usuario (AbstractUser) vinculadas para acceso al sistema.
"""
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages

from APPS.usuarios.models import Usuario, RolChoices
from APPS.core.models import Persona
from APPS.core.forms import PersonaForm
from APPS.estudiantes.models import Estudiante, Encargado, EstudianteEncargado
from APPS.estudiantes.forms import EstudianteForm, EncargadoForm


class EstudianteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista todos los estudiantes activos en la institución."""
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.view_estudiante'
    model = Estudiante
    template_name = 'estudiantes/estudiante_list.html'
    context_object_name = 'estudiantes'
    paginate_by = 15

    def get_queryset(self):
        return Estudiante.objects.select_related('persona', 'persona__usuario').filter(esta_eliminado=False)


class EstudianteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    CBV para la inscripción de un nuevo Estudiante.
    Procesa en una transacción atómica:
      1. La cuenta de Usuario (username = codigo_mineduc, rol = ESTUDIANTE).
      2. La información personal (Persona).
      3. El expediente académico (Estudiante).
    """
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.add_estudiante'
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'estudiantes/estudiante_form.html'
    success_url = reverse_lazy('estudiantes:estudiante_list')

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
                estudiante_data = form.cleaned_data
                codigo_mineduc = estudiante_data['codigo_mineduc']
                clave_temporal = "Estudiante.2026!"

                # 1. Crear la cuenta de Usuario
                usuario = Usuario.objects.create_user(
                    username=codigo_mineduc,
                    email=persona_data.get('correo', ''),
                    password=clave_temporal,
                    first_name=persona_data['nombres'],
                    last_name=persona_data['apellidos'],
                    rol=RolChoices.ESTUDIANTE
                )

                # 2. Crear Persona vinculada al Usuario
                persona = persona_form.save(commit=False)
                persona.usuario = usuario
                persona.save()

                # 3. Crear Subtipo Estudiante vinculado a Persona
                estudiante = form.save(commit=False)
                estudiante.persona = persona
                estudiante.save()

            messages.success(
                self.request,
                f"Estudiante '{persona.nombre_completo}' inscrito exitosamente. "
                f"Cuenta de acceso autogenerada -> Usuario: {usuario.username} | Clave Temporal: {clave_temporal}"
            )
            return super().form_valid(form)

        except Exception as e:
            messages.error(self.request, f"Error al inscribir al estudiante: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        messages.error(self.request, "Por favor corrija los errores marcados en el formulario.")
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


class EncargadoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    CBV para el registro de un nuevo Encargado / Tutor Legal.
    Procesa en una transacción atómica:
      1. La cuenta de Usuario (username = CUI/DPI, rol = ENCARGADO).
      2. La información personal (Persona).
      3. El registro de tutor (Encargado).
    """
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.add_encargado'
    model = Encargado
    form_class = EncargadoForm
    template_name = 'estudiantes/encargado_form.html'
    success_url = reverse_lazy('estudiantes:estudiante_list')

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
                cui = persona_data['cui']
                clave_temporal = "Encargado.2026!"

                # 1. Crear cuenta de Usuario autogenerada (Username = CUI/DPI)
                usuario = Usuario.objects.create_user(
                    username=cui,
                    email=persona_data.get('correo', ''),
                    password=clave_temporal,
                    first_name=persona_data['nombres'],
                    last_name=persona_data['apellidos'],
                    rol=RolChoices.ENCARGADO
                )

                # 2. Crear Persona vinculada al Usuario
                persona = persona_form.save(commit=False)
                persona.usuario = usuario
                persona.save()

                # 3. Crear Subtipo Encargado vinculado a Persona
                encargado = form.save(commit=False)
                encargado.persona = persona
                encargado.save()

            messages.success(
                self.request,
                f"Encargado '{persona.nombre_completo}' registrado exitosamente. "
                f"Cuenta de acceso autogenerada -> Usuario: {usuario.username} | Clave Temporal: {clave_temporal}"
            )
            return super().form_valid(form)

        except Exception as e:
            messages.error(self.request, f"Error al registrar al encargado: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        messages.error(self.request, "Por favor corrija los errores marcados en el formulario.")
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )
