"""
APPS/estudiantes/views.py

Vistas Basadas en Clases (CBV) y vistas de reportes para la gestión del Registro de Alumnos.
Implementa transacciones atómicas (transaction.atomic()), contraseñas temporales aleatorias
y generación de expedientes/credenciales oficiales en PDF.
"""
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, ListView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages

from APPS.usuarios.models import Usuario, RolChoices
from APPS.core.models import Persona
from APPS.core.forms import PersonaForm
from APPS.estudiantes.models import Estudiante, Encargado, EstadoEstudianteChoices
from APPS.estudiantes.forms import EstudianteForm, EncargadoForm
from APPS.estudiantes.reports import (
    generar_password_temporal,
    generar_pdf_expediente_estudiante,
    generar_pdf_credenciales_acceso
)


class EstudianteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista todos los estudiantes registrados en el padrón del instituto."""
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.view_estudiante'
    model = Estudiante
    template_name = 'estudiantes/estudiante_list.html'
    context_object_name = 'estudiantes'
    paginate_by = 15

    def get_queryset(self):
        qs = Estudiante.objects.select_related(
            'persona', 'persona__usuario', 'encargado', 'encargado__persona'
        ).filter(esta_eliminado=False)

        # Búsqueda por texto (nombre, apellido, CUI, código MINEDUC)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(persona__nombres__icontains=q) |
                Q(persona__apellidos__icontains=q) |
                Q(persona__cui__icontains=q) |
                Q(codigo_mineduc__icontains=q)
            )

        # Filtro por estado del estudiante
        estado = self.request.GET.get('estado', '').strip()
        if estado:
            qs = qs.filter(estado_estudiante=estado)

        # Filtro por estado de expediente (papelería incompleta)
        papeleria = self.request.GET.get('papeleria', '').strip()
        if papeleria == 'incompleta':
            qs = qs.filter(
                Q(doc_cert_nacimiento_renap=False) |
                Q(doc_dpi_encargado=False) |
                Q(doc_certificado_grado_anterior=False) |
                Q(doc_diploma_primaria=False) |
                Q(doc_codigo_mineduc=False)
            )
        elif papeleria == 'completa':
            qs = qs.filter(
                doc_cert_nacimiento_renap=True,
                doc_dpi_encargado=True,
                doc_certificado_grado_anterior=True,
                doc_diploma_primaria=True,
                doc_codigo_mineduc=True
            )

        return qs.order_by('persona__apellidos', 'persona__nombres')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['estado_filtro'] = self.request.GET.get('estado', '')
        context['papeleria_filtro'] = self.request.GET.get('papeleria', '')
        context['estados_list'] = EstadoEstudianteChoices.choices
        return context


class EstudianteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Muestra el Expediente Digital 360° completo del alumno."""
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.view_estudiante'
    model = Estudiante
    template_name = 'estudiantes/estudiante_detail.html'
    context_object_name = 'estudiante'

    def get_queryset(self):
        return Estudiante.objects.select_related(
            'persona', 'persona__usuario', 'encargado', 'encargado__persona'
        ).filter(esta_eliminado=False)


class EstudianteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    CBV para el nuevo Registro de Alumno en el Padrón Escolar.
    Genera automáticamente contraseñas temporales aleatorias y seguras.
    """
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.add_estudiante'
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'estudiantes/estudiante_form.html'

    def get_context_data(self, **kwargs):
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
        # Validar edad del estudiante (< 18 años para Ciclo Básico Regular)
        fecha_nac = persona_form.cleaned_data.get('fecha_nacimiento')
        if fecha_nac:
            from datetime import date
            edad = (date.today() - fecha_nac).days // 365
            if edad >= 18:
                persona_form.add_error('fecha_nacimiento', f'El estudiante tiene {edad} años. Para el Ciclo Básico diurno regular la edad debe ser menor a 18 años (< 18).')
                return self.forms_invalid(form, persona_form)
            elif edad < 10:
                persona_form.add_error('fecha_nacimiento', f'El estudiante tiene {edad} años. La edad mínima para Ciclo Básico es de 10 años.')
                return self.forms_invalid(form, persona_form)

        try:
            with transaction.atomic():
                persona_data = persona_form.cleaned_data
                estudiante_data = form.cleaned_data
                codigo_mineduc = estudiante_data['codigo_mineduc']
                
                # Generación de contraseña aleatoria única y segura
                clave_temporal = generar_password_temporal()

                # 1. Crear la cuenta de Usuario (username = CUI de 13 dígitos)
                usuario = Usuario.objects.create_user(
                    username=persona_data['cui'],
                    email=persona_data.get('correo', ''),
                    password=clave_temporal,
                    first_name=persona_data['nombres'],
                    last_name=persona_data['apellidos'],
                    rol=RolChoices.ESTUDIANTE,
                    debe_cambiar_password=True
                )

                # 2. Crear Persona vinculada al Usuario
                persona = persona_form.save(commit=False)
                persona.usuario = usuario
                persona.save()

                # 3. Crear Subtipo Estudiante vinculado a Persona
                estudiante = form.save(commit=False)
                estudiante.persona = persona
                estudiante.save()

                # Almacenar contraseña temporal en la sesión para la primera descarga de PDF
                self.request.session[f'temp_pwd_estudiante_{estudiante.pk}'] = clave_temporal

            messages.success(
                self.request,
                f"¡Alumno '{persona.nombre_completo}' registrado exitosamente! "
                f"Cuenta autogenerada → Usuario (CUI): {usuario.username} | Clave Temporal: {clave_temporal}. "
                f"📌 RECUERDE: Descargue e imprima la Constancia de Credenciales de Acceso (PDF) para entregarla al tutor legal."
            )
            # Redirigir directamente al Expediente 360° del alumno recién creado
            return redirect('estudiantes:estudiante_detail', pk=estudiante.pk)

        except Exception as e:
            messages.error(self.request, f"Error al registrar al alumno: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        messages.error(self.request, "Por favor corrija los errores marcados en el formulario.")
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


class EstudianteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edición del Expediente y Papelería del Alumno."""
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.change_estudiante'
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'estudiantes/estudiante_form.html'
    success_url = reverse_lazy('estudiantes:estudiante_list')

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
        # Validar edad del estudiante (< 18 años para Ciclo Básico Regular)
        fecha_nac = persona_form.cleaned_data.get('fecha_nacimiento')
        if fecha_nac:
            from datetime import date
            edad = (date.today() - fecha_nac).days // 365
            if edad >= 18:
                persona_form.add_error('fecha_nacimiento', f'El estudiante tiene {edad} años. Para el Ciclo Básico diurno regular la edad debe ser menor a 18 años (< 18).')
                return self.forms_invalid(form, persona_form)
            elif edad < 10:
                persona_form.add_error('fecha_nacimiento', f'El estudiante tiene {edad} años. La edad mínima para Ciclo Básico es de 10 años.')
                return self.forms_invalid(form, persona_form)

        try:
            with transaction.atomic():
                persona = persona_form.save()
                estudiante = form.save()

            messages.success(
                self.request,
                f"Expediente del alumno '{persona.nombre_completo}' actualizado correctamente."
            )
            return redirect('estudiantes:estudiante_detail', pk=estudiante.pk)
        except Exception as e:
            messages.error(self.request, f"Error al actualizar el expediente: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        messages.error(self.request, "Por favor corrija los errores marcados en el formulario.")
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


class EncargadoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    CBV para el registro de un nuevo Encargado / Tutor Legal.
    Genera automáticamente contraseñas temporales aleatorias y seguras.
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
                
                # Generación de contraseña aleatoria única y segura
                clave_temporal = generar_password_temporal()

                # 1. Crear cuenta de Usuario (con cambio obligatorio de clave)
                usuario = Usuario.objects.create_user(
                    username=cui,
                    email=persona_data.get('correo', ''),
                    password=clave_temporal,
                    first_name=persona_data['nombres'],
                    last_name=persona_data['apellidos'],
                    rol=RolChoices.ENCARGADO,
                    debe_cambiar_password=True
                )

                # 2. Crear Persona vinculada al Usuario
                persona = persona_form.save(commit=False)
                persona.usuario = usuario
                persona.save()

                # 3. Crear Subtipo Encargado vinculado a Persona
                encargado = form.save(commit=False)
                encargado.persona = persona
                encargado.save()

                # Guardar clave en sesión para eventual constancia
                self.request.session[f'temp_pwd_tutor_{encargado.pk}'] = clave_temporal

            messages.success(
                self.request,
                f"Encargado '{persona.nombre_completo}' registrado exitosamente. "
                f"Cuenta autogenerada → Usuario (DPI): {usuario.username} | Clave Temporal: {clave_temporal}"
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


def buscar_encargado_api(request):
    """Endpoint de búsqueda dinámica HTMX para seleccionar tutor legal por CUI o Nombre."""
    q = request.GET.get('q', '').strip()
    encargados = []
    if len(q) >= 2:
        encargados = Encargado.objects.select_related('persona').filter(
            esta_eliminado=False
        ).filter(
            Q(persona__nombres__icontains=q) |
            Q(persona__apellidos__icontains=q) |
            Q(persona__cui__icontains=q)
        )[:8]
    return render(request, 'estudiantes/partials/encargado_search_results.html', {'encargados': encargados})


@login_required
@permission_required('estudiantes.view_estudiante', raise_exception=True)
def descargar_expediente_pdf(request, pk):
    """Genera y descarga la Ficha Única del Expediente del Alumno en PDF."""
    estudiante = get_object_or_404(
        Estudiante.objects.select_related('persona', 'encargado', 'encargado__persona'),
        pk=pk,
        esta_eliminado=False
    )
    return generar_pdf_expediente_estudiante(estudiante)


@login_required
@permission_required('estudiantes.view_estudiante', raise_exception=True)
def descargar_credenciales_pdf(request, pk):
    """Genera y descarga el Comprobante de Credenciales de Acceso en PDF."""
    estudiante = get_object_or_404(
        Estudiante.objects.select_related('persona', 'encargado', 'encargado__persona'),
        pk=pk,
        esta_eliminado=False
    )
    
    # Recuperar claves temporales recién generadas de la sesión si existen
    clave_temp_est = request.session.get(f'temp_pwd_estudiante_{pk}')
    clave_temp_tutor = None
    if estudiante.encargado_id:
        clave_temp_tutor = request.session.get(f'temp_pwd_tutor_{estudiante.encargado_id}')

    return generar_pdf_credenciales_acceso(
        estudiante,
        clave_temporal_estudiante=clave_temp_est,
        clave_temporal_tutor=clave_temp_tutor
    )
