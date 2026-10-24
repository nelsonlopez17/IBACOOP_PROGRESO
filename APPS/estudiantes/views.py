"""
APPS/estudiantes/views.py

Vistas Basadas en Clases (CBV) y vistas de reportes para la gestión del Registro de Estudiantes.
Implementa transacciones atómicas (transaction.atomic()), contraseñas temporales aleatorias
y generación de expedientes/credenciales oficiales en PDF.
"""
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, ListView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages

from django.core.exceptions import PermissionDenied
from APPS.usuarios.models import Usuario, RolChoices
from APPS.usuarios.permisos import es_titular_o_encargado_de_estudiante
from APPS.core.models import Persona
from APPS.core.forms import PersonaForm
from APPS.estudiantes.models import Estudiante, Encargado, EstadoEstudianteChoices
from APPS.estudiantes.forms import EstudianteForm, EncargadoForm
from APPS.estudiantes.reports import (
    generar_password_temporal,
    generar_pdf_expediente_estudiante,
    generar_pdf_credenciales_acceso,
    generar_pdf_credenciales_encargado
)


class EstudianteListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista todos los estudiantes registrados en el padrón del instituto."""
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.view_estudiante'
    raise_exception = True
    model = Estudiante
    template_name = 'estudiantes/estudiante_list.html'
    context_object_name = 'estudiantes'
    paginate_by = 15

    def get_queryset(self):
        qs = Estudiante.objects.select_related(
            'persona', 'persona__usuario', 'encargado', 'encargado__persona'
        ).filter(esta_eliminado=False)

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(persona__nombres__icontains=q) |
                Q(persona__apellidos__icontains=q) |
                Q(persona__cui__icontains=q) |
                Q(codigo_mineduc__icontains=q)
            )

        estado = self.request.GET.get('estado', EstadoEstudianteChoices.ACTIVO).strip().upper() or EstadoEstudianteChoices.ACTIVO
        if estado != 'TODOS':
            qs = qs.filter(estado_estudiante=estado)

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
        estado_filtro = self.request.GET.get('estado', EstadoEstudianteChoices.ACTIVO).strip().upper() or EstadoEstudianteChoices.ACTIVO
        context['q'] = self.request.GET.get('q', '')
        context['estado_filtro'] = estado_filtro
        context['papeleria_filtro'] = self.request.GET.get('papeleria', '')
        context['estados_list'] = EstadoEstudianteChoices.choices
        context['total_estudiantes'] = Estudiante.objects.filter(esta_eliminado=False).count()
        context['activos_count'] = Estudiante.objects.filter(esta_eliminado=False, estado_estudiante=EstadoEstudianteChoices.ACTIVO).count()
        context['retirados_count'] = Estudiante.objects.filter(esta_eliminado=False, estado_estudiante=EstadoEstudianteChoices.RETIRADO).count()
        
        nuevo_enc_pk = self.request.session.pop('nuevo_encargado_pk', None)
        if nuevo_enc_pk:
            context['nuevo_encargado_pk'] = nuevo_enc_pk
        return context


class EstudianteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Muestra el Expediente Digital 360° completo del estudiante."""
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.view_estudiante'
    raise_exception = True
    model = Estudiante
    template_name = 'estudiantes/estudiante_detail.html'
    context_object_name = 'estudiante'

    def has_permission(self):
        user = self.request.user
        if super().has_permission() or getattr(user, 'rol', None) == RolChoices.DOCENTE:
            return True
        try:
            estudiante = self.get_object()
            return es_titular_o_encargado_de_estudiante(user, estudiante)
        except Exception:
            return False

    def get_queryset(self):
        return Estudiante.objects.select_related(
            'persona', 'persona__usuario', 'encargado', 'encargado__persona'
        ).filter(esta_eliminado=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object
        context['clave_temp_est'] = self.request.session.get(f'temp_pwd_estudiante_{estudiante.pk}')
        if estudiante.encargado_id:
            context['clave_temp_tutor'] = self.request.session.get(f'temp_pwd_tutor_{estudiante.encargado_id}')

        from APPS.academico.models import CicloEscolar, AsignacionEstudiante, AsistenciaEstudiantil
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True, esta_eliminado=False)
            context['asignacion_actual'] = AsignacionEstudiante.objects.filter(
                estudiante=estudiante,
                ciclo_escolar=ciclo_activo,
                esta_eliminado=False
            ).select_related('seccion__grado').first()
        except Exception:
            context['asignacion_actual'] = None

        asistencias_qs = AsistenciaEstudiantil.objects.filter(
            asignacion_estudiante__estudiante=estudiante,
            esta_eliminado=False
        )
        context['asistencias_presente_count'] = asistencias_qs.filter(presente=True).count()
        context['asistencias_justificadas_count'] = asistencias_qs.filter(presente=False, justificado=True).count()
        context['asistencias_ausentes_count'] = asistencias_qs.filter(presente=False, justificado=False).count()

        return context



class EstudianteCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    CBV para el nuevo Registro de Estudiante en el Padrón Escolar.
    Genera automáticamente contraseñas temporales aleatorias y seguras.
    """
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.add_estudiante'
    raise_exception = True
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
        # validar edad del estudiante para ciclo basico
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
                
                # generacion de contrasena temporal segura
                clave_temporal = generar_password_temporal()

                # creacion de cuenta de usuario con identificador unico
                usuario = Usuario.objects.create_user(
                    username=persona_data['cui'],
                    email=persona_data.get('correo', ''),
                    password=clave_temporal,
                    first_name=persona_data['nombres'],
                    last_name=persona_data['apellidos'],
                    rol=RolChoices.ESTUDIANTE,
                    debe_cambiar_password=True
                )

                persona = persona_form.save(commit=False)
                persona.usuario = usuario
                persona.save()

                estudiante = form.save(commit=False)
                estudiante.persona = persona
                estudiante.save()

                # generacion automatica de cuotas de primer ingreso
                try:
                    from APPS.financiero.models import ConceptoPago, CuentaPorCobrar, EstadoPagoChoices, CategoriaConceptoChoices
                    from APPS.academico.models import CicloEscolar, AsignacionEstudiante, Curso, NotaFinalCurso

                    ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
                    
                    # busqueda de conceptos de cobro aplicables a la inscripcion
                    conceptos_iniciales = list(ConceptoPago.objects.filter(
                        aplica_al_inscribir_seccion=True,
                        esta_eliminado=False
                    ))

                    if not conceptos_iniciales:
                        c_matr = ConceptoPago.objects.filter(
                            categoria_concepto=CategoriaConceptoChoices.MATRICULA,
                            esta_eliminado=False
                        ).first() or ConceptoPago.objects.filter(
                            nombre__icontains='inscripci',
                            esta_eliminado=False
                        ).first()
                        if c_matr:
                            conceptos_iniciales = [c_matr]

                    if ciclo_activo and conceptos_iniciales:
                        for concepto in conceptos_iniciales:
                            CuentaPorCobrar.objects.create(
                                estudiante=estudiante,
                                concepto=concepto,
                                ciclo_escolar=ciclo_activo,
                                monto_total=concepto.monto_estandar,
                                saldo_pendiente=concepto.monto_estandar,
                                estado_pago=EstadoPagoChoices.PENDIENTE
                            )

                    # inscripcion academica en la seccion seleccionada
                    seccion_asignada = form.cleaned_data.get('seccion_asignada')
                    if seccion_asignada and ciclo_activo:
                        asig_acad, _ = AsignacionEstudiante.objects.get_or_create(
                            estudiante=estudiante,
                            ciclo_escolar=ciclo_activo,
                            defaults={
                                'seccion': seccion_asignada
                            }
                        )
                        cursos = Curso.objects.filter(grado=seccion_asignada.grado, esta_eliminado=False)
                        for curso in cursos:
                            NotaFinalCurso.objects.get_or_create(
                                asignacion_estudiante=asig_acad,
                                curso=curso
                            )
                except Exception as ex_fin:
                    pass

                # almacenar clave temporal en sesion para descarga de comprobante
                self.request.session[f'temp_pwd_estudiante_{estudiante.pk}'] = clave_temporal

            messages.success(
                self.request,
                f"¡Estudiante '{persona.nombre_completo}' registrado exitosamente! "
                f"Cuenta autogenerada → Usuario (CUI): {usuario.username} | Clave Temporal: {clave_temporal}. "
                f"📌 RECUERDE: Descargue e imprima la Constancia de Credenciales de Acceso (PDF) para entregarla al padre de familia o encargado."
            )
            return redirect('estudiantes:estudiante_detail', pk=estudiante.pk)

        except Exception as e:
            messages.error(self.request, f"Error al registrar al estudiante: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


class EstudianteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edición del Expediente y Papelería del Estudiante."""
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
        # validar edad del estudiante para ciclo basico
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

                if persona.usuario:
                    es_activo = (
                        estudiante.estado_estudiante == EstadoEstudianteChoices.ACTIVO
                        and bool(getattr(estudiante, 'estado_activo', True))
                    )
                    if persona.usuario.is_active != es_activo:
                        persona.usuario.is_active = es_activo
                        persona.usuario.save(update_fields=['is_active'])

            messages.success(
                self.request,
                f"Expediente del estudiante '{persona.nombre_completo}' actualizado correctamente."
            )
            return redirect('estudiantes:estudiante_detail', pk=estudiante.pk)
        except Exception as e:
            messages.error(self.request, f"Error al actualizar el expediente: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


class EncargadoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    CBV para el registro de un nuevo Padre de Familia o Encargado.
    Genera automáticamente contraseñas temporales aleatorias y seguras.
    """
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.add_encargado'
    model = Encargado
    form_class = EncargadoForm
    template_name = 'estudiantes/encargado_form.html'
    success_url = reverse_lazy('estudiantes:encargado_list')

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
        fecha_nac = persona_form.cleaned_data.get('fecha_nacimiento')
        if fecha_nac:
            from datetime import date
            edad = (date.today() - fecha_nac).days // 365
            if edad < 18:
                persona_form.add_error(
                    'fecha_nacimiento',
                    f'El Padre de Familia o Encargado tiene {edad} años. En Guatemala debe ser mayor de edad (mínimo 18 años).'
                )
                return self.forms_invalid(form, persona_form)

        try:
            with transaction.atomic():
                persona_data = persona_form.cleaned_data
                cui = persona_data['cui']
                
                # generacion de contrasena temporal segura
                clave_temporal = generar_password_temporal()

                usuario = Usuario.objects.create_user(
                    username=cui,
                    email=persona_data.get('correo', ''),
                    password=clave_temporal,
                    first_name=persona_data['nombres'],
                    last_name=persona_data['apellidos'],
                    rol=RolChoices.ENCARGADO,
                    debe_cambiar_password=True
                )

                persona = persona_form.save(commit=False)
                persona.usuario = usuario
                persona.save()

                encargado = form.save(commit=False)
                encargado.persona = persona
                encargado.save()

                # almacenar clave en sesion para emision de constancia
                self.request.session[f'temp_pwd_tutor_{encargado.pk}'] = clave_temporal
                self.request.session['nuevo_encargado_pk'] = encargado.pk

            messages.success(
                self.request,
                f"Encargado '{persona.nombre_completo}' registrado exitosamente. "
                f"Cuenta autogenerada → Usuario (DPI): {usuario.username} | Clave Temporal: {clave_temporal}."
            )
            return redirect('estudiantes:encargado_list')

        except Exception as e:
            messages.error(self.request, f"Error al registrar al encargado: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


class EncargadoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Directorio de Padres de Familia o Encargados oficiales del instituto.
    Permite visualizar a los encargados con separación de activos e inactivos
    (según estado de sus estudiantes a cargo y estado de su usuario).
    """
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.view_encargado'
    raise_exception = True
    model = Encargado
    template_name = 'estudiantes/encargado_list.html'
    context_object_name = 'encargados'
    paginate_by = 20

    def get_queryset(self):
        qs = Encargado.objects.filter(
            esta_eliminado=False,
            persona__esta_eliminado=False
        ).select_related(
            'persona', 'persona__usuario'
        ).prefetch_related(
            'estudiantes__persona'
        ).annotate(
            estudiantes_activos_num=Count(
                'estudiantes',
                filter=Q(estudiantes__estado_estudiante=EstadoEstudianteChoices.ACTIVO, estudiantes__esta_eliminado=False),
                distinct=True
            ),
            estudiantes_total_num=Count(
                'estudiantes',
                filter=Q(estudiantes__esta_eliminado=False),
                distinct=True
            )
        )

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(persona__nombres__icontains=q) |
                Q(persona__apellidos__icontains=q) |
                Q(persona__cui__icontains=q) |
                Q(persona__telefono_principal__icontains=q) |
                Q(persona__correo__icontains=q) |
                Q(lugar_de_trabajo__icontains=q) |
                Q(estudiantes__persona__nombres__icontains=q) |
                Q(estudiantes__persona__apellidos__icontains=q)
            ).distinct()

        estado_filtro = self.request.GET.get('estado', 'ACTIVO').strip().upper()
        if estado_filtro == 'ACTIVO':
            qs = qs.filter(
                estudiantes_activos_num__gt=0
            ).exclude(
                persona__usuario__is_active=False
            )
        elif estado_filtro == 'INACTIVO':
            qs = qs.filter(
                Q(estudiantes_activos_num=0) | Q(persona__usuario__is_active=False)
            )

        return qs.order_by('persona__apellidos', 'persona__nombres')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estado_filtro = self.request.GET.get('estado', 'ACTIVO').strip().upper()
        if estado_filtro not in ['ACTIVO', 'INACTIVO', 'TODOS']:
            estado_filtro = 'ACTIVO'

        base_qs = Encargado.objects.filter(
            esta_eliminado=False,
            persona__esta_eliminado=False
        ).annotate(
            estudiantes_activos_num=Count(
                'estudiantes',
                filter=Q(estudiantes__estado_estudiante=EstadoEstudianteChoices.ACTIVO, estudiantes__esta_eliminado=False),
                distinct=True
            )
        )

        activos_count = base_qs.filter(
            estudiantes_activos_num__gt=0
        ).exclude(
            persona__usuario__is_active=False
        ).count()

        inactivos_count = base_qs.filter(
            Q(estudiantes_activos_num=0) | Q(persona__usuario__is_active=False)
        ).count()

        total_encargados = base_qs.count()

        context['q'] = self.request.GET.get('q', '')
        context['estado_filtro'] = estado_filtro
        context['activos_count'] = activos_count
        context['inactivos_count'] = inactivos_count
        context['total_encargados'] = total_encargados

        nuevo_enc_pk = self.request.session.pop('nuevo_encargado_pk', None)
        if nuevo_enc_pk:
            context['nuevo_encargado_pk'] = nuevo_enc_pk
        return context


class EncargadoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Muestra el expediente digital y perfil completo del Padre de Familia o Encargado."""
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.view_encargado'
    raise_exception = True
    model = Encargado
    template_name = 'estudiantes/encargado_detail.html'
    context_object_name = 'encargado'

    def get_queryset(self):
        return Encargado.objects.select_related(
            'persona', 'persona__usuario'
        ).prefetch_related(
            'estudiantes__persona'
        ).filter(esta_eliminado=False, persona__esta_eliminado=False)


class EncargadoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edición de la ficha y datos del Padre de Familia o Encargado."""
    login_url = 'usuarios:login'
    permission_required = 'estudiantes.change_encargado'
    raise_exception = True
    model = Encargado
    form_class = EncargadoForm
    template_name = 'estudiantes/encargado_form.html'

    def get_success_url(self):
        return reverse('estudiantes:encargado_detail', kwargs={'pk': self.object.pk})

    def get_queryset(self):
        return Encargado.objects.select_related(
            'persona', 'persona__usuario'
        ).filter(esta_eliminado=False, persona__esta_eliminado=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'persona_form' not in context:
            persona_form = PersonaForm(self.request.POST or None, instance=self.object.persona)
            if 'cui' in persona_form.fields:
                persona_form.fields['cui'].disabled = True
            context['persona_form'] = persona_form
        context['es_edicion'] = True
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        persona_form = PersonaForm(request.POST, instance=self.object.persona)
        if 'cui' in persona_form.fields:
            persona_form.fields['cui'].disabled = True

        if form.is_valid() and persona_form.is_valid():
            return self.forms_valid(form, persona_form)
        else:
            return self.forms_invalid(form, persona_form)

    def forms_valid(self, form, persona_form):
        fecha_nac = persona_form.cleaned_data.get('fecha_nacimiento')
        if fecha_nac:
            from datetime import date
            edad = (date.today() - fecha_nac).days // 365
            if edad < 18:
                persona_form.add_error(
                    'fecha_nacimiento',
                    f'El Padre de Familia o Encargado tiene {edad} años. En Guatemala debe ser mayor de edad (mínimo 18 años).'
                )
                return self.forms_invalid(form, persona_form)

        try:
            with transaction.atomic():
                persona = persona_form.save()
                encargado = form.save()

            messages.success(
                self.request,
                f"Datos del Padre de Familia o Encargado '{persona.nombre_completo}' actualizados exitosamente."
            )
            return redirect('estudiantes:encargado_detail', pk=encargado.pk)

        except Exception as e:
            messages.error(self.request, f"Error al actualizar al encargado: {str(e)}")
            return self.forms_invalid(form, persona_form)

    def forms_invalid(self, form, persona_form):
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


@login_required
@permission_required('estudiantes.view_encargado', raise_exception=True)
def buscar_encargado_api(request):
    """Endpoint de búsqueda dinámica HTMX para seleccionar encargado por CUI o Nombre."""
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
def descargar_expediente_pdf(request, pk):
    """Genera y descarga la Ficha Única del Expediente del Estudiante en PDF."""
    estudiante = get_object_or_404(
        Estudiante.objects.select_related('persona', 'encargado', 'encargado__persona'),
        pk=pk,
        esta_eliminado=False
    )
    if not (request.user.has_perm('estudiantes.view_estudiante') or es_titular_o_encargado_de_estudiante(request.user, estudiante)):
        raise PermissionDenied("No tiene autorización para descargar la ficha de expediente de este estudiante.")
    return generar_pdf_expediente_estudiante(estudiante)


@login_required
@permission_required('estudiantes.view_estudiante', raise_exception=True)
def descargar_credenciales_pdf(request, pk):
    """Genera y descarga el Comprobante de Credenciales de Acceso en PDF (disponible solo en sesión de alta/reset)."""
    estudiante = get_object_or_404(
        Estudiante.objects.select_related('persona', 'encargado', 'encargado__persona'),
        pk=pk,
        esta_eliminado=False
    )
    
    # recuperar claves temporales de la sesion para la emision de constancia
    clave_temp_est = request.session.get(f'temp_pwd_estudiante_{pk}')
    clave_temp_tutor = None
    if estudiante.encargado_id:
        clave_temp_tutor = request.session.get(f'temp_pwd_tutor_{estudiante.encargado_id}')

    if not clave_temp_est and not clave_temp_tutor:
        messages.warning(
            request,
            "Las credenciales de primer ingreso ya no están activas en la sesión actual. "
            "Por políticas de seguridad (IAM), las contraseñas no se guardan en texto plano. "
            "Para generar un nuevo comprobante de acceso, utilice la opción 'Restablecer Contraseña' en el módulo de Gestión de Usuarios."
        )
        return redirect('estudiantes:estudiante_detail', pk=pk)

    return generar_pdf_credenciales_acceso(
        estudiante,
        clave_temporal_estudiante=clave_temp_est
    )


@login_required
@permission_required('estudiantes.view_encargado', raise_exception=True)
def descargar_credenciales_encargado_pdf(request, pk):
    """Genera y descarga el Comprobante de Credenciales de Acceso del Encargado en PDF."""
    encargado = get_object_or_404(
        Encargado.objects.select_related('persona', 'persona__usuario'),
        pk=pk,
        esta_eliminado=False
    )
    clave_temp = request.session.get(f'temp_pwd_tutor_{pk}')
    if not clave_temp:
        messages.warning(
            request,
            "Las credenciales temporales de primer ingreso del encargado ya no están activas en la sesión actual. "
            "Por políticas de seguridad (IAM), las contraseñas no se guardan en texto plano. "
            "Para generar un nuevo comprobante, utilice la opción 'Restablecer Contraseña' en Gestión de Usuarios."
        )
        return redirect('estudiantes:estudiante_list')

    return generar_pdf_credenciales_encargado(encargado, clave_temporal=clave_temp)


