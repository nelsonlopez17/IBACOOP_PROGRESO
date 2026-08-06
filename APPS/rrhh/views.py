"""
APPS/rrhh/views.py

Vistas Basadas en Clases (CBV) para Recursos Humanos y Registro de Empleados.
Implementa el flujo completo (Receta Módulo Alumnos):
  1. PersonalListView: Lista de empleados con búsqueda, filtros y badges.
  2. PersonalCreateView: Registro de Empleado con CUI como username y clave aleatoria.
  3. PersonalDetailView: Vista 360° del Empleado con checklist de expediente físico.
  4. PersonalUpdateView: Modificación atómica de datos personales y laborales.
  5. Descargas PDF: Ficha de Expediente y Comprobante de Credenciales.
"""
from django.db import transaction
from django.db.models import Q
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, ListView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages

from APPS.usuarios.models import Usuario, RolChoices
from APPS.core.models import Persona
from APPS.rrhh.models import Personal, Puesto, EstadoLaboralChoices
from APPS.core.forms import PersonaForm
from APPS.rrhh.forms import PersonalForm
from APPS.rrhh.reports import (
    generar_password_temporal,
    generar_pdf_expediente_empleado,
    generar_pdf_credenciales_empleado
)


def asegurar_puestos_iniciales():
    """Garantiza la existencia de los puestos base institucionales en la base de datos."""
    if Puesto.objects.filter(esta_eliminado=False).count() == 0:
        puestos_default = [
            ('Director General', 'Dirección general, administrativa y académica del instituto.'),
            ('Docente / Catedrático', 'Personal docente encargados de impartir asignaturas del CNB Nivel Medio.'),
            ('Secretaria de Dirección', 'Gestión de expedientes de alumnos, papelería oficial y archivo.'),
            ('Contador General', 'Administración de finanzas, cobro de colegiaturas y planillas.'),
            ('Coordinador Académico', 'Supervisión docente, horarios y planificación escolar.'),
            ('Auxiliar Administrativo', 'Apoyo operativo a secretaría y contabilidad.'),
            ('Personal de Servicios / Conserjería', 'Mantenimiento, instalaciones y servicios generales.'),
        ]
        for nombre, desc in puestos_default:
            Puesto.objects.get_or_create(nombre_puesto=nombre, defaults={'descripcion': desc})


def mapear_rol_segun_puesto(puesto: Puesto) -> str:
    """
    Determina dinámicamente el RolChoices adecuado analizando el nombre del Puesto.
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
        return RolChoices.PERSONAL  # Personal general / operativo sin acceso a notas ni finanzas




class PersonalListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista todos los empleados/colaboradores del instituto con filtro y búsqueda."""
    login_url = 'usuarios:login'
    permission_required = 'rrhh.view_personal'
    model = Personal
    template_name = 'rrhh/personal_list.html'
    context_object_name = 'personal_list'
    paginate_by = 15

    def get_queryset(self):
        queryset = Personal.objects.select_related('persona', 'puesto', 'persona__usuario').filter(esta_eliminado=False)
        
        # Filtro de Búsqueda (Buscador por Nombre, CUI, Puesto)
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(persona__nombres__icontains=q) |
                Q(persona__apellidos__icontains=q) |
                Q(persona__cui__icontains=q) |
                Q(puesto__nombre_puesto__icontains=q)
            )

        # Filtro por Estado Laboral
        estado = self.request.GET.get('estado', '').strip()
        if estado:
            queryset = queryset.filter(estado_laboral=estado)

        return queryset.order_by('persona__apellidos', 'persona__nombres')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['estado_filtro'] = self.request.GET.get('estado', '')
        context['estados_laborales'] = EstadoLaboralChoices.choices
        context['total_empleados'] = Personal.objects.filter(esta_eliminado=False).count()
        context['activos_count'] = Personal.objects.filter(esta_eliminado=False, estado_laboral=EstadoLaboralChoices.ACTIVO).count()
        return context


class PersonalCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    CBV para 'Registrar Empleado'.
    Crea atómicamente:
      1. Cuenta de Usuario con username = CUI y contraseña aleatoria.
      2. Registro de Persona.
      3. Registro de Personal con custodia de contrato y checklist de papelería.
    """
    login_url = 'usuarios:login'
    permission_required = 'rrhh.add_personal'
    model = Personal
    form_class = PersonalForm
    template_name = 'rrhh/personal_form.html'

    def get_context_data(self, **kwargs):
        asegurar_puestos_iniciales()
        context = super().get_context_data(**kwargs)
        if 'persona_form' not in context:
            context['persona_form'] = PersonaForm(self.request.POST or None)
        context['es_edicion'] = False
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
                cui = persona_data['cui']

                # 1. Validar que el CUI no tenga una cuenta existente
                if Usuario.objects.filter(username=cui).exists():
                    messages.error(self.request, f"Ya existe una cuenta registrada con el CUI/DPI '{cui}'.")
                    return self.forms_invalid(form, persona_form)

                # 2. Generar Contraseña Temporal Aleatoria y Mapear Rol
                clave_temporal = generar_password_temporal()
                rol_asignado = mapear_rol_segun_puesto(puesto_seleccionado)

                # 3. Crear cuenta de Usuario (username = CUI)
                usuario = Usuario.objects.create_user(
                    username=cui,
                    email=persona_data.get('correo', ''),
                    password=clave_temporal,
                    first_name=persona_data['nombres'],
                    last_name=persona_data['apellidos'],
                    rol=rol_asignado
                )

                # 4. Crear Persona
                persona = persona_form.save(commit=False)
                persona.usuario = usuario
                persona.save()

                # 5. Crear Personal
                personal = form.save(commit=False)
                personal.persona = persona
                personal.save()

            # Guardar la clave temporal en sesión para permitir descargar el PDF inmediatamente
            self.request.session[f'temp_pwd_personal_{personal.pk}'] = clave_temporal

            messages.success(
                self.request,
                f"Empleado '{persona.nombre_completo}' registrado exitosamente. "
                f"Cuenta generada -> Usuario (CUI): {usuario.username} | Rol: {rol_asignado} | Clave Temporal: {clave_temporal}"
            )
            return redirect('rrhh:personal_detail', pk=personal.pk)

        except Exception as e:
            messages.error(self.request, f"Error al registrar al empleado: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        messages.error(self.request, "Por favor corrija los errores marcados en el formulario.")
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


class PersonalDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Ficha 360° del Empleado (Perfil, resguardo físico, checklist y cuenta asociada)."""
    login_url = 'usuarios:login'
    permission_required = 'rrhh.view_personal'
    model = Personal
    template_name = 'rrhh/personal_detail.html'
    context_object_name = 'personal'

    def get_queryset(self):
        return Personal.objects.select_related('persona', 'puesto', 'persona__usuario').filter(esta_eliminado=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        personal = self.object
        # Recuperar clave temporal de sesión si se acaba de registrar
        clave_temp_key = f'temp_pwd_personal_{personal.pk}'
        context['clave_temporal'] = self.request.session.get(clave_temp_key)
        return context


class PersonalUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """CBV para 'Modificar Datos del Empleado' (Actualización atómica de Persona y Personal)."""
    login_url = 'usuarios:login'
    permission_required = 'rrhh.change_personal'
    model = Personal
    form_class = PersonalForm
    template_name = 'rrhh/personal_form.html'

    def get_queryset(self):
        return Personal.objects.select_related('persona', 'puesto', 'persona__usuario').filter(esta_eliminado=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'persona_form' not in context:
            context['persona_form'] = PersonaForm(
                self.request.POST or None,
                instance=self.object.persona
            )
        context['es_edicion'] = True
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        persona_form = PersonaForm(request.POST, instance=self.object.persona)

        if form.is_valid() and persona_form.is_valid():
            return self.forms_valid(form, persona_form)
        else:
            return self.forms_invalid(form, persona_form)

    def forms_valid(self, form, persona_form):
        try:
            with transaction.atomic():
                persona = persona_form.save()
                personal = form.save()

                # Sincronizar nombres/correo en el Usuario vinculado
                if persona.usuario:
                    usuario = persona.usuario
                    usuario.first_name = persona.nombres
                    usuario.last_name = persona.apellidos
                    usuario.email = persona.correo or ''
                    # Actualizar rol si cambió el puesto
                    usuario.rol = mapear_rol_segun_puesto(personal.puesto)
                    usuario.save()

            messages.success(
                self.request,
                f"Datos del empleado '{persona.nombre_completo}' actualizados exitosamente."
            )
            return redirect('rrhh:personal_detail', pk=personal.pk)

        except Exception as e:
            messages.error(self.request, f"Error al modificar los datos del empleado: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        messages.error(self.request, "Por favor corrija los errores marcados en el formulario.")
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


@login_required(login_url='usuarios:login')
@permission_required('rrhh.view_personal', raise_exception=True)
def descargar_expediente_pdf(request, pk):
    """Genera y descarga la Ficha de Expediente Físico del Empleado en PDF."""
    personal = get_object_or_404(
        Personal.objects.select_related('persona', 'puesto', 'persona__usuario'),
        pk=pk,
        esta_eliminado=False
    )
    return generar_pdf_expediente_empleado(personal)


@login_required(login_url='usuarios:login')
@permission_required('rrhh.view_personal', raise_exception=True)
def descargar_credenciales_pdf(request, pk):
    """
    Genera y descarga el Comprobante de Credenciales de Acceso en PDF.
    Por seguridad ISO 27001 / OWASP, solo está disponible inmediatamente tras el registro o un restablecimiento activo.
    """
    personal = get_object_or_404(
        Personal.objects.select_related('persona', 'puesto', 'persona__usuario'),
        pk=pk,
        esta_eliminado=False
    )
    clave_temp_key = f'temp_pwd_personal_{personal.pk}'
    clave_temporal = request.session.get(clave_temp_key)

    if not clave_temporal:
        messages.warning(
            request,
            "Las credenciales de primer ingreso ya fueron consumidas o no están activas en la sesión actual. "
            "Por políticas de seguridad (IAM), las contraseñas no se almacenan en texto plano. "
            "Para generar un nuevo comprobante de acceso, utilice la opción 'Restablecer Contraseña' en Gestión de Usuarios."
        )
        return redirect('rrhh:personal_detail', pk=pk)

    return generar_pdf_credenciales_empleado(personal, clave_temporal=clave_temporal)


