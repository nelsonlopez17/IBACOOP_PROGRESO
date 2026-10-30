"""
APPS/rrhh/views.py

Vistas Basadas en Clases (CBV) para Recursos Humanos y Registro de Empleados.
Implementa el flujo completo (Receta Módulo Estudiantes):
  1. PersonalListView: Lista de empleados con búsqueda, filtros y badges.
  2. PersonalCreateView: Registro de Empleado con CUI como username y clave aleatoria.
  3. PersonalDetailView: Vista 360° del Empleado con checklist de expediente físico.
  4. PersonalUpdateView: Modificación atómica de datos personales y laborales.
  5. Descargas PDF: Ficha de Expediente y Comprobante de Credenciales.
"""
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView, DetailView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.contrib import messages

from APPS.usuarios.models import Usuario, RolChoices
from APPS.core.models import Persona
from APPS.academico.models import CicloEscolar
from APPS.rrhh.models import (
    Personal, Puesto, Planilla,
    EstadoLaboralChoices, MesChoices, TipoPlanillaChoices
)
from APPS.core.forms import PersonaForm
from APPS.rrhh.forms import (
    PersonalForm, PersonalBajaForm, PlanillaGenerarMasivaForm, PlanillaUpdateForm
)
from APPS.rrhh.reportes import (
    generar_password_temporal,
    generar_pdf_expediente_empleado,
    generar_pdf_credenciales_empleado,
    generar_pdf_comprobante_planilla
)


def asegurar_puestos_iniciales():
    """Garantiza la existencia de los puestos base institucionales en la base de datos."""
    if Puesto.objects.filter(esta_eliminado=False).count() == 0:
        puestos_default = [
            ('Director General', 'Dirección general, administrativa y académica del instituto.'),
            ('Docente / Catedrático', 'Personal docente encargados de impartir asignaturas del CNB Nivel Medio.'),
            ('Secretaria de Dirección', 'Gestión de expedientes de estudiantes, papelería oficial y archivo.'),
            ('Contador General', 'Administración de finanzas, cobro de cuotas escolares y planillas.'),
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
        return RolChoices.PERSONAL  # personal general / operativo sin acceso a notas ni finanzas




class PersonalListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista todos los empleados/colaboradores del instituto con filtro y búsqueda."""
    login_url = 'usuarios:login'
    permission_required = 'rrhh.view_personal'
    raise_exception = True
    model = Personal
    template_name = 'rrhh/personal_list.html'
    context_object_name = 'personal_list'
    paginate_by = 15

    def get_queryset(self):
        queryset = Personal.objects.select_related('persona', 'puesto', 'persona__usuario').filter(esta_eliminado=False)
        
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(persona__nombres__icontains=q) |
                Q(persona__apellidos__icontains=q) |
                Q(persona__cui__icontains=q) |
                Q(puesto__nombre_puesto__icontains=q)
            )

        estado = self.request.GET.get('estado', EstadoLaboralChoices.ACTIVO).strip().upper() or EstadoLaboralChoices.ACTIVO
        if estado != 'TODOS':
            queryset = queryset.filter(estado_laboral=estado)

        return queryset.order_by('persona__apellidos', 'persona__nombres')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estado_filtro = self.request.GET.get('estado', EstadoLaboralChoices.ACTIVO).strip().upper() or EstadoLaboralChoices.ACTIVO
        context['q'] = self.request.GET.get('q', '')
        context['estado_filtro'] = estado_filtro
        context['estados_laborales'] = EstadoLaboralChoices.choices
        context['total_empleados'] = Personal.objects.filter(esta_eliminado=False).count()
        context['activos_count'] = Personal.objects.filter(esta_eliminado=False, estado_laboral=EstadoLaboralChoices.ACTIVO).count()
        context['retirados_count'] = Personal.objects.filter(esta_eliminado=False, estado_laboral=EstadoLaboralChoices.RETIRADO).count()
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
    raise_exception = True
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

                # validar que no exista una cuenta previa con el mismo identificador
                if Usuario.objects.filter(username=cui).exists():
                    messages.error(self.request, f"Ya existe una cuenta registrada con el CUI/DPI '{cui}'.")
                    return self.forms_invalid(form, persona_form)

                # generacion de clave temporal segura y determinacion del rol
                clave_temporal = generar_password_temporal()
                rol_asignado = mapear_rol_segun_puesto(puesto_seleccionado)

                # creacion de cuenta de usuario correspondiente
                usuario = Usuario.objects.create_user(
                    username=cui,
                    email=persona_data.get('correo', ''),
                    password=clave_temporal,
                    first_name=persona_data['nombres'],
                    last_name=persona_data['apellidos'],
                    rol=rol_asignado
                )

                persona = persona_form.save(commit=False)
                persona.usuario = usuario
                persona.save()

                personal = form.save(commit=False)
                personal.persona = persona
                personal.save()

            # guardar clave temporal en sesion para descargar comprobante
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
        return self.render_to_response(
            self.get_context_data(form=form, persona_form=persona_form)
        )


class PersonalDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Ficha 360° del Empleado (Perfil, resguardo físico, checklist y cuenta asociada)."""
    login_url = 'usuarios:login'
    permission_required = 'rrhh.view_personal'
    raise_exception = True
    model = Personal
    template_name = 'rrhh/personal_detail.html'
    context_object_name = 'personal'

    def get_queryset(self):
        return Personal.objects.select_related('persona', 'puesto', 'persona__usuario').filter(esta_eliminado=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        personal = self.object
        # recuperar clave temporal de sesion si existe
        clave_temp_key = f'temp_pwd_personal_{personal.pk}'
        context['clave_temporal'] = self.request.session.get(clave_temp_key)
        context['baja_form'] = PersonalBajaForm()
        context['cursos_asignados'] = personal.asignaciones_docente.filter(
            esta_eliminado=False,
            ciclo_escolar__estado_activo=True
        ).select_related('curso', 'seccion', 'ciclo_escolar')
        return context


class PersonalBajaView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Procesa la desvinculación laboral (Baja / Retiro) del trabajador."""
    login_url = 'usuarios:login'
    permission_required = 'rrhh.change_personal'
    raise_exception = True
    form_class = PersonalBajaForm
    template_name = 'rrhh/personal_baja.html'

    def get_personal(self):
        return get_object_or_404(
            Personal.objects.select_related('persona', 'puesto', 'persona__usuario'),
            pk=self.kwargs['pk'],
            esta_eliminado=False
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        personal = self.get_personal()
        context['personal'] = personal
        context['cursos_asignados'] = personal.asignaciones_docente.filter(
            esta_eliminado=False,
            ciclo_escolar__estado_activo=True
        ).select_related('curso', 'seccion', 'ciclo_escolar')
        return context

    def form_valid(self, form):
        personal = self.get_personal()
        fecha_baja = form.cleaned_data['fecha_baja']
        estado_laboral = form.cleaned_data['estado_laboral']
        motivo_baja = form.cleaned_data['motivo_baja']
        desactivar_usuario = form.cleaned_data.get('desactivar_usuario', True)

        with transaction.atomic():
            personal.estado_laboral = estado_laboral
            personal.fecha_baja = fecha_baja
            personal.motivo_baja = motivo_baja
            personal.save()

            if desactivar_usuario and hasattr(personal.persona, 'usuario') and personal.persona.usuario:
                usuario = personal.persona.usuario
                if not usuario.is_superuser:
                    usuario.is_active = False
                    usuario.save()

        messages.success(
            self.request,
            f"Se ha registrado exitosamente la baja del colaborador '{personal.persona.nombre_completo}' "
            f"con estado '{personal.get_estado_laboral_display()}'. Su cuenta de usuario institucional ha sido desactivada."
        )
        return redirect('rrhh:personal_detail', pk=personal.pk)


class PersonalReactivarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Reactiva a un colaborador que se encontraba en estado de baja o retiro."""
    login_url = 'usuarios:login'
    permission_required = 'rrhh.change_personal'
    raise_exception = True

    def post(self, request, pk):
        personal = get_object_or_404(
            Personal.objects.select_related('persona', 'puesto', 'persona__usuario'),
            pk=pk,
            esta_eliminado=False
        )
        with transaction.atomic():
            personal.estado_laboral = EstadoLaboralChoices.ACTIVO
            personal.save()

            if hasattr(personal.persona, 'usuario') and personal.persona.usuario:
                usuario = personal.persona.usuario
                usuario.is_active = True
                usuario.save()

        messages.success(
            request,
            f"Colaborador '{personal.persona.nombre_completo}' reactivado exitosamente con estado 'Activo'. "
            f"Su cuenta institucional ha sido rehabilitada."
        )
        return redirect('rrhh:personal_detail', pk=personal.pk)


class PersonalUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """CBV para 'Modificar Datos del Empleado' (Actualización atómica de Persona y Personal)."""
    login_url = 'usuarios:login'
    permission_required = 'rrhh.change_personal'
    raise_exception = True
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

                # sincronizar datos actualizados en la cuenta de usuario vinculada
                if persona.usuario:
                    usuario = persona.usuario
                    usuario.first_name = persona.nombres
                    usuario.last_name = persona.apellidos
                    usuario.email = persona.correo or ''
                    # actualizar rol institucional si cambia el puesto laboral
                    usuario.rol = mapear_rol_segun_puesto(personal.puesto)
                    if not usuario.is_superuser:
                        usuario.is_active = (personal.estado_laboral == EstadoLaboralChoices.ACTIVO)
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



class PlanillaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listado general de pagos de planilla mensuales del personal."""

    login_url = 'usuarios:login'
    permission_required = 'rrhh.view_planilla'
    raise_exception = True
    model = Planilla
    template_name = 'rrhh/planilla_list.html'
    context_object_name = 'planillas'
    paginate_by = 25

    def get_queryset(self):
        qs = Planilla.objects.select_related(
            'personal__persona', 'personal__puesto', 'ciclo_escolar'
        ).filter(esta_eliminado=False)

        tipo = self.request.GET.get('tipo', '').strip()
        if tipo:
            qs = qs.filter(tipo_planilla=tipo)

        mes = self.request.GET.get('mes', '').strip()
        if mes:
            qs = qs.filter(mes_pagado=mes)

        ciclo = self.request.GET.get('ciclo', '').strip()
        if ciclo:
            qs = qs.filter(ciclo_escolar_id=ciclo)
        else:
            ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
            if ciclo_activo:
                qs = qs.filter(ciclo_escolar=ciclo_activo)

        pagado = self.request.GET.get('pagado', '').strip()
        if pagado == '1':
            qs = qs.filter(pagado=True)
        elif pagado == '0':
            qs = qs.filter(pagado=False)

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(personal__persona__nombres__icontains=q) |
                Q(personal__persona__apellidos__icontains=q) |
                Q(personal__persona__cui__icontains=q)
            )

        return qs.order_by('-mes_pagado', 'tipo_planilla', 'personal__persona__apellidos')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Gestión de Planillas de Sueldos'
        context['meses'] = MesChoices.choices
        context['tipos_planilla'] = TipoPlanillaChoices.choices
        context['ciclos'] = CicloEscolar.objects.filter(esta_eliminado=False).order_by('-anio')
        context['mes_filtro'] = self.request.GET.get('mes', '')
        context['tipo_filtro'] = self.request.GET.get('tipo', '')
        context['ciclo_filtro'] = self.request.GET.get('ciclo', '')
        context['pagado_filtro'] = self.request.GET.get('pagado', '')
        context['q'] = self.request.GET.get('q', '')

        base_qs = self.get_queryset()
        total_planilla = sum(p.total_pagar for p in base_qs)
        context['total_planilla'] = total_planilla
        context['total_nomina'] = total_planilla
        context['total_patronal'] = sum(p.total_cuota_patronal for p in base_qs)
        context['total_isr'] = sum(p.retencion_isr for p in base_qs)
        context['total_igss_laboral'] = sum(p.descuento_igss for p in base_qs)
        context['total_empleados_planilla'] = base_qs.count()
        context['total_pagados'] = base_qs.filter(pagado=True).count()
        return context


class PlanillaGenerarMasivaView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Proceso automatizado de cálculo y emisión masiva de la planilla de sueldos (Ordinaria, Bono 14, Aguinaldo o Extraordinaria)."""

    login_url = 'usuarios:login'
    permission_required = 'rrhh.add_planilla'
    raise_exception = True
    form_class = PlanillaGenerarMasivaForm
    template_name = 'rrhh/planilla_generar.html'
    success_url = reverse_lazy('rrhh:planilla_list')

    def form_valid(self, form):
        ciclo = form.cleaned_data['ciclo_escolar']
        tipo_planilla = form.cleaned_data['tipo_planilla']
        mes = int(form.cleaned_data['mes_pagado'])
        bono_ley = form.cleaned_data['bonificacion_ley']
        descontar_igss = form.cleaned_data['descontar_igss']
        calcular_cuota_patronal = form.cleaned_data.get('calcular_cuota_patronal', True)
        calcular_retencion_isr = form.cleaned_data.get('calcular_retencion_isr', True)
        prorratear_altas = form.cleaned_data.get('prorratear_altas', True)
        fecha_pago = form.cleaned_data['fecha_pago']

        empleados_activos = Personal.objects.filter(
            esta_eliminado=False,
            estado_laboral=EstadoLaboralChoices.ACTIVO
        ).select_related('persona', 'puesto')

        if not empleados_activos.exists():
            messages.error(self.request, "No hay personal con estado 'ACTIVO' registrado en el sistema.")
            return redirect('rrhh:personal_list')

        generados_count = 0
        with transaction.atomic():
            for emp in empleados_activos:
                sueldo_base = emp.salario_base_asignado
                dias_lab = 30
                sueldo_ord = sueldo_base
                bono_inc = Decimal('0.00')
                cuota_igss = Decimal('0.00')
                retencion_isr = Decimal('0.00')
                cuota_patronal_igss = Decimal('0.00')
                cuota_patronal_irtra = Decimal('0.00')
                cuota_patronal_intecap = Decimal('0.00')

                if tipo_planilla == TipoPlanillaChoices.BONO_14:
                    mes = MesChoices.JULIO
                    # computo legal dec. 42-92: del 1 de julio ano anterior al 30 de junio ciclo escolar (365 dias)
                    fecha_inicio_periodo = date(ciclo.anio - 1, 7, 1)
                    fecha_fin_periodo = date(ciclo.anio, 6, 30)
                    if emp.fecha_contratacion and emp.fecha_contratacion > fecha_inicio_periodo:
                        dias_efectivos = (fecha_fin_periodo - emp.fecha_contratacion).days + 1
                        dias_lab = max(1, min(365, dias_efectivos))
                        sueldo_ord = round(sueldo_base * (Decimal(str(dias_lab)) / Decimal('365')), 2)
                    else:
                        dias_lab = 365
                        sueldo_ord = sueldo_base

                elif tipo_planilla == TipoPlanillaChoices.AGUINALDO:
                    mes = MesChoices.DICIEMBRE
                    # computo legal dec. 76-78: del 1 de diciembre ano anterior al 30 de noviembre ciclo escolar (365 dias)
                    fecha_inicio_periodo = date(ciclo.anio - 1, 12, 1)
                    fecha_fin_periodo = date(ciclo.anio, 11, 30)
                    if emp.fecha_contratacion and emp.fecha_contratacion > fecha_inicio_periodo:
                        dias_efectivos = (fecha_fin_periodo - emp.fecha_contratacion).days + 1
                        dias_lab = max(1, min(365, dias_efectivos))
                        sueldo_ord = round(sueldo_base * (Decimal(str(dias_lab)) / Decimal('365')), 2)
                    else:
                        dias_lab = 365
                        sueldo_ord = sueldo_base

                elif tipo_planilla == TipoPlanillaChoices.EXTRAORDINARIA:
                    dias_lab = 30
                    sueldo_ord = sueldo_base

                else:  # tipoplanillachoices.ordinaria
                    # prorrateo si fue contratado en el mes que se esta liquidando
                    if prorratear_altas and emp.fecha_contratacion and (emp.fecha_contratacion.year == ciclo.anio and emp.fecha_contratacion.month == mes):
                        dia_inicio = emp.fecha_contratacion.day
                        dias_lab = max(1, min(30, 30 - dia_inicio + 1))
                        sueldo_ord = round((sueldo_base / Decimal('30')) * Decimal(str(dias_lab)), 2)
                        bono_inc = round((bono_ley / Decimal('30')) * Decimal(str(dias_lab)), 2)
                    else:
                        dias_lab = 30
                        sueldo_ord = sueldo_base
                        bono_inc = bono_ley

                    # retencion cuota laboral igss (4.83%)
                    if descontar_igss:
                        cuota_igss = round(sueldo_ord * Decimal('0.0483'), 2)

                    # retencion mensual isr asalariados (decreto 10-2012)
                    if calcular_retencion_isr and sueldo_base > Decimal('4000.00'):
                        renta_bruta_anual = sueldo_base * Decimal('12')
                        deduccion_sin_comprobacion = Decimal('48000.00')
                        deduccion_igss_anual = sueldo_base * Decimal('0.0483') * Decimal('12')
                        renta_imponible = max(Decimal('0.00'), renta_bruta_anual - deduccion_sin_comprobacion - deduccion_igss_anual)
                        impuesto_anual = renta_imponible * Decimal('0.05')
                        retencion_isr = round(impuesto_anual / Decimal('12'), 2)

                    # aportes y cargas patronales (12.67%)
                    if calcular_cuota_patronal:
                        cuota_patronal_igss = round(sueldo_ord * Decimal('0.1067'), 2)
                        cuota_patronal_irtra = round(sueldo_ord * Decimal('0.0100'), 2)
                        cuota_patronal_intecap = round(sueldo_ord * Decimal('0.0100'), 2)

                total_descuentos = cuota_igss + retencion_isr

                Planilla.objects.update_or_create(
                    personal=emp,
                    mes_pagado=mes,
                    ciclo_escolar=ciclo,
                    tipo_planilla=tipo_planilla,
                    defaults={
                        'salario_base': sueldo_base,
                        'dias_laborados': dias_lab,
                        'salario_ordinario': sueldo_ord,
                        'bonificacion_incentivo': bono_inc,
                        'bonificaciones': Decimal('0.00'),
                        'descuento_igss': cuota_igss,
                        'retencion_isr': retencion_isr,
                        'descuento_anticipo': Decimal('0.00'),
                        'descuento_judicial': Decimal('0.00'),
                        'descuento_otros': Decimal('0.00'),
                        'motivo_otros_descuentos': '',
                        'descuentos': total_descuentos,
                        'cuota_patronal_igss': cuota_patronal_igss,
                        'cuota_patronal_irtra': cuota_patronal_irtra,
                        'cuota_patronal_intecap': cuota_patronal_intecap,
                        'fecha_pago': fecha_pago,
                        'pagado': False,
                        'esta_eliminado': False,
                    }
                )
                generados_count += 1

        mes_nombre = dict(MesChoices.choices).get(mes, str(mes))
        tipo_nombre = dict(TipoPlanillaChoices.choices).get(tipo_planilla, tipo_planilla)
        messages.success(
            self.request,
            f"✓ {tipo_nombre} generada exitosamente para {generados_count} miembros del personal ({mes_nombre} {ciclo.anio})."
        )
        return redirect(f"{self.success_url}?mes={mes}&ciclo={ciclo.pk}&tipo={tipo_planilla}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Generación Masiva de Planilla de Sueldos'
        context['total_activos'] = Personal.objects.filter(
            esta_eliminado=False,
            estado_laboral=EstadoLaboralChoices.ACTIVO
        ).count()
        return context


class PlanillaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Ajuste individual de deducciones, bonos o estado de pago de una boleta de pago."""

    login_url = 'usuarios:login'
    permission_required = 'rrhh.change_planilla'
    raise_exception = True
    model = Planilla
    form_class = PlanillaUpdateForm
    template_name = 'rrhh/planilla_form.html'
    success_url = reverse_lazy('rrhh:planilla_list')

    def get_queryset(self):
        return Planilla.objects.select_related('personal__persona', 'personal__puesto', 'ciclo_escolar').filter(esta_eliminado=False)

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.pagado:
            messages.warning(
                request,
                f"La boleta de pago de {obj.personal.persona.nombre_completo} ({obj.get_mes_pagado_display()} {obj.ciclo_escolar.anio}) ya se encuentra en estado 'PAGADO' y no puede ser modificada."
            )
            return redirect('rrhh:planilla_detail', pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        planilla = form.save()
        messages.success(
            self.request,
            f"✓ Boleta de pago actualizada para {planilla.personal.persona.nombre_completo} (Total Líquido: Q{planilla.total_pagar:,.2f})."
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Ajuste de Planilla — {self.object.personal.persona.nombre_completo}'
        context['planilla'] = self.object
        return context


class PlanillaDetailView(LoginRequiredMixin, DetailView):
    """Vista de detalle / vista previa en pantalla de la Boleta de Pago de Planilla."""

    login_url = 'usuarios:login'
    model = Planilla
    template_name = 'rrhh/planilla_detail.html'
    context_object_name = 'planilla'

    def get_queryset(self):
        return Planilla.objects.select_related(
            'personal__persona', 'personal__puesto', 'ciclo_escolar'
        ).filter(esta_eliminado=False)

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        es_titular = getattr(obj.personal.persona, 'usuario_id', None) == request.user.id
        if not (request.user.has_perm('rrhh.view_planilla') or es_titular):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("No tiene autorización para visualizar los detalles de esta boleta de pago.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Detalle de Boleta — {self.object.personal.persona.nombre_completo}'
        return context


@xframe_options_sameorigin
@login_required(login_url='usuarios:login')
def descargar_comprobante_planilla_pdf(request, pk):
    """Genera y descarga la Boleta de Pago de Planilla en PDF con ReportLab."""
    planilla = get_object_or_404(
        Planilla.objects.select_related('personal__persona', 'personal__puesto', 'ciclo_escolar'),
        pk=pk,
        esta_eliminado=False
    )
    usuario_id = getattr(planilla.personal.persona, 'usuario_id', None)
    es_titular = (
        request.user.is_authenticated
        and usuario_id is not None
        and usuario_id == request.user.id
    )
    if not (request.user.has_perm('rrhh.view_planilla') or es_titular):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("No tiene autorización para descargar esta boleta de pago de planilla.")
    return generar_pdf_comprobante_planilla(planilla)




