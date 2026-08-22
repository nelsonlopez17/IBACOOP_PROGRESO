"""
APPS/financiero/views.py

Vistas Basadas en Clases (CBV) para la gestión del Módulo Financiero / Cuentas por Cobrar.
Incluye: Catálogo de Conceptos, Emisión Masiva e Individual de Cargos, Estado de Cuenta Corriente del Alumno,
Registro de Abonos y Generación de Recibos/Solvencias en PDF.
"""
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, FormView, TemplateView

from APPS.financiero.models import (
    ConceptoPago, CuentaPorCobrar, Abono, BecaDescuento, EstadoPagoChoices, CategoriaConceptoChoices
)
from APPS.financiero.forms import (
    ConceptoPagoForm, CuentaPorCobrarForm, GenerarCobroMasivoForm, AbonoForm, BecaDescuentoForm
)
from APPS.financiero.reports import generar_pdf_recibo_pago, generar_pdf_solvencia_estudiante
from APPS.academico.models import CicloEscolar, AsignacionEstudiante
from APPS.estudiantes.models import Estudiante


# ──────────────────────────────────────────────────────────────────────────────
# 1. CATALOGO DE CONCEPTOS DE PAGO (TARIFARIO)
# ──────────────────────────────────────────────────────────────────────────────

class ConceptoPagoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de conceptos de cobro registrados en el catálogo del instituto."""

    model = ConceptoPago
    template_name = 'financiero/concepto_list.html'
    context_object_name = 'conceptos'
    permission_required = 'financiero.view_conceptopago'
    raise_exception = True
    paginate_by = 20

    def get_queryset(self):
        qs = ConceptoPago.objects.filter(esta_eliminado=False)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(nombre__icontains=q.strip())
        return qs.order_by('nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Catálogo de Conceptos de Cobro'
        context['q'] = self.request.GET.get('q', '')
        return context


class ConceptoPagoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Creación de un nuevo concepto de pago (arancel/actividad)."""

    model = ConceptoPago
    form_class = ConceptoPagoForm
    template_name = 'financiero/concepto_form.html'
    permission_required = 'financiero.add_conceptopago'
    raise_exception = True
    success_url = reverse_lazy('financiero:concepto_list')

    def form_valid(self, form):
        concepto = form.save()
        messages.success(self.request, f'✓ Concepto de cobro "{concepto.nombre}" creado exitosamente.')
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Nuevo Concepto de Cobro'
        context['boton_label'] = 'Guardar Concepto'
        return context


class ConceptoPagoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edición o actualización del monto estándar de un concepto de cobro."""

    model = ConceptoPago
    form_class = ConceptoPagoForm
    template_name = 'financiero/concepto_form.html'
    permission_required = 'financiero.change_conceptopago'
    raise_exception = True
    success_url = reverse_lazy('financiero:concepto_list')

    def get_queryset(self):
        return ConceptoPago.objects.filter(esta_eliminado=False)

    def form_valid(self, form):
        concepto = form.save(commit=False)
        concepto.usuario_modificacion = self.request.user
        concepto.save()
        messages.success(self.request, f'✓ Concepto de cobro "{concepto.nombre}" actualizado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar Concepto: {self.object.nombre}'
        context['boton_label'] = 'Actualizar Concepto'
        return context


# ──────────────────────────────────────────────────────────────────────────────
# 2. CUENTAS POR COBRAR Y GENERACIÓN DE CARGOS
# ──────────────────────────────────────────────────────────────────────────────

class CuentaPorCobrarListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listado general de deudas u obligaciones financieras registradas."""

    model = CuentaPorCobrar
    template_name = 'financiero/cuentaporcobrar_list.html'
    context_object_name = 'cuentas'
    permission_required = 'financiero.view_cuentaporcobrar'
    raise_exception = True
    paginate_by = 25

    def get_queryset(self):
        qs = CuentaPorCobrar.objects.filter(
            esta_eliminado=False
        ).select_related(
            'estudiante__persona', 'concepto', 'ciclo_escolar'
        )

        q = self.request.GET.get('q')
        estado = self.request.GET.get('estado')
        ciclo_id = self.request.GET.get('ciclo')

        if q:
            query = q.strip()
            qs = qs.filter(
                Q(estudiante__persona__nombres__icontains=query) |
                Q(estudiante__persona__apellidos__icontains=query) |
                Q(estudiante__persona__cui__icontains=query) |
                Q(estudiante__codigo_mineduc__icontains=query) |
                Q(concepto__nombre__icontains=query)
            )

        if estado:
            qs = qs.filter(estado_pago=estado)

        if ciclo_id:
            qs = qs.filter(ciclo_escolar_id=ciclo_id)

        return qs.order_by('-creado_en')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Gestión de Cuentas por Cobrar'
        context['q'] = self.request.GET.get('q', '')
        context['estado_sel'] = self.request.GET.get('estado', '')
        context['ciclo_sel'] = self.request.GET.get('ciclo', '')
        context['ciclos'] = CicloEscolar.objects.filter(esta_eliminado=False)
        context['estados_pago'] = EstadoPagoChoices.choices
        return context


class CuentaPorCobrarCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Asignación individual de un cargo o deuda a un estudiante específico."""

    model = CuentaPorCobrar
    form_class = CuentaPorCobrarForm
    template_name = 'financiero/cuentaporcobrar_form.html'
    permission_required = 'financiero.add_cuentaporcobrar'
    raise_exception = True

    def get_initial(self):
        initial = super().get_initial()
        estudiante_id = self.request.GET.get('estudiante')
        if estudiante_id:
            initial['estudiante'] = estudiante_id
        return initial

    def form_valid(self, form):
        cuenta = form.save(commit=False)
        cuenta.saldo_pendiente = cuenta.monto_total
        cuenta.save()

        messages.success(
            self.request,
            f'✓ Cargo de {cuenta.concepto.nombre} por Q{cuenta.monto_total} asignado a {cuenta.estudiante.persona.nombre_completo}.'
        )
        return redirect('financiero:estudiante_cuenta_corriente', pk=cuenta.estudiante.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Asignar Cargo Individual a Estudiante'
        return context


class GenerarCobroMasivoView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Vista para la emisión masiva de cobros por Grado, Sección o a todos los alumnos activos.
    Permite generar cuotas masivas como Inscripción, Colegiatura o Acto de Graduación.
    """

    form_class = GenerarCobroMasivoForm
    template_name = 'financiero/generar_cobro_masivo.html'
    permission_required = 'financiero.add_cuentaporcobrar'
    raise_exception = True
    success_url = reverse_lazy('financiero:cuentaporcobrar_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Emisión Masiva de Cuentas por Cobrar'
        return context

    def form_valid(self, form):
        concepto = form.cleaned_data['concepto']
        ciclo = form.cleaned_data['ciclo_escolar']
        grado = form.cleaned_data['grado']
        seccion = form.cleaned_data['seccion']
        monto_custom = form.cleaned_data['monto_override']
        fecha_limite = form.cleaned_data['fecha_limite_pago']

        monto_aplicar = monto_custom if monto_custom is not None else concepto.monto_estandar

        # Obtener estudiantes a los cuales asignar la deuda
        if seccion:
            estudiantes_qs = Estudiante.objects.filter(
                asignaciones__seccion=seccion,
                asignaciones__ciclo_escolar=ciclo,
                persona__esta_eliminado=False,
                estado_estudiante='ACTIVO'
            )
        elif grado:
            estudiantes_qs = Estudiante.objects.filter(
                asignaciones__seccion__grado=grado,
                asignaciones__ciclo_escolar=ciclo,
                persona__esta_eliminado=False,
                estado_estudiante='ACTIVO'
            )
        else:
            # Todos los estudiantes activos en el ciclo
            estudiantes_qs = Estudiante.objects.filter(
                asignaciones__ciclo_escolar=ciclo,
                persona__esta_eliminado=False,
                estado_estudiante='ACTIVO'
            )

        estudiantes_qs = estudiantes_qs.distinct()

        if not estudiantes_qs.exists():
            messages.warning(
                self.request,
                'No se encontraron estudiantes activos asignados al filtro seleccionado para emitir los cobros.'
            )
            return self.form_invalid(form)

        creados_count = 0
        omitidos_count = 0

        with transaction.atomic():
            for estudiante in estudiantes_qs:
                # Evitar duplicar la misma deuda en el mismo ciclo para el mismo estudiante
                existe = CuentaPorCobrar.objects.filter(
                    estudiante=estudiante,
                    concepto=concepto,
                    ciclo_escolar=ciclo,
                    esta_eliminado=False
                ).exists()

                if not existe:
                    # Verificar si el estudiante cuenta con un convenio o beca activa
                    from APPS.financiero.models import BecaDescuento
                    monto_final = monto_aplicar
                    beca = BecaDescuento.objects.filter(
                        estudiante=estudiante,
                        esta_activo=True,
                        esta_eliminado=False
                    ).filter(Q(concepto=concepto) | Q(concepto__isnull=True)).first()

                    if beca:
                        monto_final = beca.calcular_monto_con_descuento(monto_aplicar)

                    CuentaPorCobrar.objects.create(
                        estudiante=estudiante,
                        concepto=concepto,
                        ciclo_escolar=ciclo,
                        monto_total=monto_final,
                        saldo_pendiente=monto_final,
                        fecha_limite_pago=fecha_limite,
                        estado_pago=EstadoPagoChoices.PENDIENTE
                    )
                    creados_count += 1
                else:
                    omitidos_count += 1

        msg = f'✓ Se emitieron exitosamente {creados_count} cuentas por cobrar para "{concepto.nombre}".'
        if omitidos_count > 0:
            msg += f' ({omitidos_count} cuentas fueron omitidas por estar registradas previamente).'

        messages.success(self.request, msg)
        return super().form_valid(form)


# ──────────────────────────────────────────────────────────────────────────────
# 3. ESTADO DE CUENTA CORRIENTE DEL ALUMNO
# ──────────────────────────────────────────────────────────────────────────────

class EstudianteCuentaCorrienteDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Vista detallada del Estado de Cuenta Corriente del Estudiante.
    Muestra semaforización de solvencia (SOLVENTE vs PENDIENTE), matriz de cuotas e historial de abonos.
    """

    model = Estudiante
    template_name = 'financiero/estudiante_cuenta_corriente.html'
    context_object_name = 'estudiante'
    permission_required = 'financiero.view_cuentaporcobrar'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object

        # Cuentas por cobrar activas del alumno
        cuentas = CuentaPorCobrar.objects.filter(
            estudiante=estudiante,
            esta_eliminado=False
        ).select_related('concepto', 'ciclo_escolar').order_by('-ciclo_escolar__anio', 'fecha_limite_pago')

        # Totales financieros
        agg_totales = cuentas.aggregate(
            sum_total=Sum('monto_total'),
            sum_saldo=Sum('saldo_pendiente')
        )

        total_deuda = agg_totales['sum_total'] or Decimal('0.00')
        saldo_pendiente_total = agg_totales['sum_saldo'] or Decimal('0.00')
        total_pagado = total_deuda - saldo_pendiente_total

        # Estado Global de Solvencia
        es_solvente = (saldo_pendiente_total == Decimal('0.00'))

        # Historial de abonos registrados a este estudiante
        abonos_historial = Abono.objects.filter(
            cuenta_por_cobrar__estudiante=estudiante,
            esta_eliminado=False
        ).select_related('cuenta_por_cobrar__concepto').order_by('-fecha_pago', '-creado_en')

        # Ciclo activo para constancia de solvencia
        ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()

        context['titulo_pagina'] = f'Estado de Cuenta Corriente — {estudiante.persona.nombre_completo}'
        context['cuentas'] = cuentas
        context['total_deuda'] = total_deuda
        context['total_pagado'] = total_pagado
        context['saldo_pendiente_total'] = saldo_pendiente_total
        context['es_solvente'] = es_solvente
        context['abonos_historial'] = abonos_historial
        context['ciclo_activo'] = ciclo_activo
        return context


# ──────────────────────────────────────────────────────────────────────────────
# 4. REGISTRO DE ABONOS / PAGOS Y REPORTES PDF
# ──────────────────────────────────────────────────────────────────────────────

class AbonoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Formulario para registrar un abono o pago parcial/total a una CuentaPorCobrar.
    Recalcula automáticamente el saldo pendiente y actualiza el estado de la deuda.
    """

    model = Abono
    form_class = AbonoForm
    template_name = 'financiero/abono_form.html'
    permission_required = 'financiero.add_abono'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.cuenta_por_cobrar = get_object_or_404(
            CuentaPorCobrar,
            pk=self.kwargs.get('cuentaporcobrar_pk'),
            esta_eliminado=False
        )
        if self.cuenta_por_cobrar.estado_pago == EstadoPagoChoices.PAGADO:
            messages.info(request, f'La cuenta por cobrar "{self.cuenta_por_cobrar.concepto.nombre}" ya se encuentra totalmente saldada.')
            return redirect('financiero:estudiante_cuenta_corriente', pk=self.cuenta_por_cobrar.estudiante.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['cuenta_por_cobrar'] = self.cuenta_por_cobrar
        return kwargs

    def form_valid(self, form):
        abono = form.save(commit=False)
        abono.cuenta_por_cobrar = self.cuenta_por_cobrar

        with transaction.atomic():
            abono.save()  # El método save() del modelo Abono actualiza la CuentaPorCobrar

        messages.success(
            self.request,
            f'✓ Abono por Q{abono.monto_pagado} registrado con éxito con boleta "{abono.numero_boleta}".'
        )
        return redirect('financiero:estudiante_cuenta_corriente', pk=self.cuenta_por_cobrar.estudiante.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cuenta'] = self.cuenta_por_cobrar
        context['estudiante'] = self.cuenta_por_cobrar.estudiante
        context['titulo_pagina'] = f'Registrar Pago: {self.cuenta_por_cobrar.concepto.nombre}'
        return context


class AbonoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Historial e inspección general de abonos/pagos registrados (Arqueo y Conciliación)."""

    model = Abono
    template_name = 'financiero/abono_list.html'
    context_object_name = 'abonos'
    permission_required = 'financiero.view_abono'
    raise_exception = True
    paginate_by = 25

    def get_queryset(self):
        qs = Abono.objects.filter(
            esta_eliminado=False
        ).select_related(
            'cuenta_por_cobrar__estudiante__persona',
            'cuenta_por_cobrar__concepto'
        )

        q = self.request.GET.get('q')
        fecha_desde = self.request.GET.get('fecha_desde')
        fecha_hasta = self.request.GET.get('fecha_hasta')

        if q:
            query = q.strip()
            qs = qs.filter(
                Q(numero_boleta__icontains=query) |
                Q(cuenta_por_cobrar__estudiante__persona__nombres__icontains=query) |
                Q(cuenta_por_cobrar__estudiante__persona__apellidos__icontains=query) |
                Q(cuenta_por_cobrar__estudiante__persona__cui__icontains=query) |
                Q(cuenta_por_cobrar__concepto__nombre__icontains=query)
            )

        if fecha_desde:
            qs = qs.filter(fecha_pago__gte=fecha_desde)

        if fecha_hasta:
            qs = qs.filter(fecha_pago__lte=fecha_hasta)

        return qs.order_by('-fecha_pago', '-creado_en')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Historial General de Pagos'
        context['q'] = self.request.GET.get('q', '')
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')
        return context


# ──────────────────────────────────────────────────────────────────────────────
# 5. VISTAS PARA DESCARGA DE REPORTES PDF
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required('financiero.view_abono', raise_exception=True)
def descargar_recibo_pdf(request, pk):
    """Servicio HTTP para descargar o visualizar el Recibo Oficial de Pago en PDF."""
    abono = get_object_or_404(
        Abono.objects.select_related(
            'cuenta_por_cobrar__estudiante__persona',
            'cuenta_por_cobrar__concepto',
            'cuenta_por_cobrar__ciclo_escolar'
        ),
        pk=pk,
        esta_eliminado=False
    )
    return generar_pdf_recibo_pago(abono)


@login_required
@permission_required('financiero.view_cuentaporcobrar', raise_exception=True)
def descargar_solvencia_pdf(request, pk):
    """Servicio HTTP para descargar o visualizar la Constancia de Solvencia Financiera en PDF."""
    estudiante = get_object_or_404(Estudiante, pk=pk, persona__esta_eliminado=False)
    
    # Verificar que el estudiante no tenga saldos pendientes acumulados
    pendientes = CuentaPorCobrar.objects.filter(
        estudiante=estudiante,
        esta_eliminado=False,
        saldo_pendiente__gt=Decimal('0.00')
    )

    if pendientes.exists():
        messages.error(
            request,
            f'No se puede generar la solvencia. El estudiante {estudiante.persona.nombre_completo} posee pagos pendientes de saldo.'
        )
        return redirect('financiero:estudiante_cuenta_corriente', pk=estudiante.pk)

    ciclo_activo = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
    if not ciclo_activo:
        messages.error(request, 'No hay un ciclo escolar activo configurado en el sistema.')
        return redirect('financiero:estudiante_cuenta_corriente', pk=estudiante.pk)

    return generar_pdf_solvencia_estudiante(estudiante, ciclo_activo)


# ──────────────────────────────────────────────────────────────────────────────
# 6. FUNCIONALIDADES ENTERPRISE: BECAS, CALENDARIO ANUAL Y ANTIGÜEDAD DE SALDOS
# ──────────────────────────────────────────────────────────────────────────────

class BecaDescuentoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista las becas y convenios de descuento otorgados a estudiantes."""

    model = BecaDescuento
    template_name = 'financiero/beca_list.html'
    context_object_name = 'becas'
    permission_required = 'financiero.view_cuentaporcobrar'
    raise_exception = True
    paginate_by = 25

    def get_queryset(self):
        qs = BecaDescuento.objects.filter(
            esta_eliminado=False
        ).select_related('estudiante__persona', 'concepto')

        q = self.request.GET.get('q')
        if q:
            query = q.strip()
            qs = qs.filter(
                Q(estudiante__persona__nombres__icontains=query) |
                Q(estudiante__persona__apellidos__icontains=query) |
                Q(motivo_convenio__icontains=query)
            )
        return qs.order_by('estudiante__persona__apellidos')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Convenios y Becas de Descuento'
        context['q'] = self.request.GET.get('q', '')
        return context


class BecaDescuentoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Registro de una nueva beca o convenio de descuento."""

    model = BecaDescuento
    form_class = BecaDescuentoForm
    template_name = 'financiero/beca_form.html'
    permission_required = 'financiero.add_cuentaporcobrar'
    raise_exception = True
    success_url = reverse_lazy('financiero:beca_list')

    def form_valid(self, form):
        beca = form.save()
        messages.success(
            self.request,
            f'✓ Beca/Convenio asignado exitosamente a {beca.estudiante.persona.nombre_completo}.'
        )
        return super().form_valid(form)


class GenerarCalendarioAnualView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Emisión en lote del Calendario Anual de 10 Colegiaturas (Enero a Octubre)."""

    template_name = 'financiero/calendario_anual_form.html'
    permission_required = 'financiero.add_cuentaporcobrar'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Generación de Calendario Anual de Colegiaturas'
        context['ciclos'] = CicloEscolar.objects.filter(esta_eliminado=False).order_by('-anio')
        context['ciclo_activo'] = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        context['concepto_colegiatura'] = ConceptoPago.objects.filter(
            categoria_concepto=CategoriaConceptoChoices.COLEGIATURA,
            esta_eliminado=False
        ).first() or ConceptoPago.objects.filter(nombre__icontains='colegiatura', esta_eliminado=False).first()
        return context

    def post(self, request, *args, **kwargs):
        ciclo_id = request.POST.get('ciclo_escolar')
        concepto_id = request.POST.get('concepto')
        dia_vencimiento = int(request.POST.get('dia_vencimiento', 5))

        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id, esta_eliminado=False)
        concepto = get_object_or_404(ConceptoPago, pk=concepto_id, esta_eliminado=False)

        estudiantes = Estudiante.objects.filter(
            asignaciones__ciclo_escolar=ciclo,
            persona__esta_eliminado=False,
            estado_estudiante='ACTIVO'
        ).distinct()

        if not estudiantes.exists():
            messages.error(request, 'No se encontraron estudiantes activos asignados al ciclo seleccionado.')
            return redirect('financiero:calendario_anual')

        # Meses de colegiatura habituales (Enero=1 a Octubre=10)
        nombres_meses = [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre')
        ]

        total_emitidos = 0
        from datetime import date

        with transaction.atomic():
            for est in estudiantes:
                # Revisar si tiene beca activa
                beca = BecaDescuento.objects.filter(
                    estudiante=est,
                    esta_activo=True,
                    esta_eliminado=False
                ).filter(Q(concepto=concepto) | Q(concepto__isnull=True)).first()

                monto_mensual = concepto.monto_estandar
                if beca:
                    monto_mensual = beca.calcular_monto_con_descuento(monto_mensual)

                for num_mes, nombre_mes in nombres_meses:
                    try:
                        f_limite = date(ciclo.anio, num_mes, min(dia_vencimiento, 28))
                    except ValueError:
                        f_limite = date(ciclo.anio, num_mes, 28)

                    # Crear sólo si no existe esa mensualidad para ese alumno y ciclo
                    existe = CuentaPorCobrar.objects.filter(
                        estudiante=est,
                        concepto=concepto,
                        ciclo_escolar=ciclo,
                        mes_aplicacion=num_mes,
                        esta_eliminado=False
                    ).exists()

                    if not existe:
                        CuentaPorCobrar.objects.create(
                            estudiante=est,
                            concepto=concepto,
                            ciclo_escolar=ciclo,
                            monto_total=monto_mensual,
                            saldo_pendiente=monto_mensual,
                            fecha_limite_pago=f_limite,
                            mes_aplicacion=num_mes,
                            estado_pago=EstadoPagoChoices.PENDIENTE
                        )
                        total_emitidos += 1

        messages.success(
            request,
            f'✓ Calendario Anual Generado: Se crearon {total_emitidos} cobros de mensualidades (Enero-Octubre {ciclo.anio}).'
        )
        return redirect('financiero:cuentaporcobrar_list')


class AntiguedadSaldosView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Tablero ejecutivo de Antigüedad de Cartera y Saldos Vencidos."""

    template_name = 'financiero/antiguedad_saldos.html'
    permission_required = 'financiero.view_cuentaporcobrar'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Antigüedad de Saldos y Cartera Pendiente'

        from datetime import date
        hoy = date.today()

        cuentas_pendientes = CuentaPorCobrar.objects.filter(
            esta_eliminado=False,
            saldo_pendiente__gt=Decimal('0.00')
        ).select_related('estudiante__persona', 'concepto', 'ciclo_escolar')

        total_al_dia = Decimal('0.00')
        total_1_30 = Decimal('0.00')
        total_31_60 = Decimal('0.00')
        total_61_90 = Decimal('0.00')
        total_mas_90 = Decimal('0.00')

        detalles_alumnos = {}

        for c in cuentas_pendientes:
            dias_atraso = 0
            if c.fecha_limite_pago and c.fecha_limite_pago < hoy:
                dias_atraso = (hoy - c.fecha_limite_pago).days

            s_id = c.estudiante.pk
            if s_id not in detalles_alumnos:
                detalles_alumnos[s_id] = {
                    'estudiante': c.estudiante,
                    'total_saldo': Decimal('0.00'),
                    'al_dia': Decimal('0.00'),
                    'venc_1_30': Decimal('0.00'),
                    'venc_31_60': Decimal('0.00'),
                    'venc_61_90': Decimal('0.00'),
                    'venc_mas_90': Decimal('0.00'),
                }

            row = detalles_alumnos[s_id]
            row['total_saldo'] += c.saldo_pendiente

            if dias_atraso == 0:
                total_al_dia += c.saldo_pendiente
                row['al_dia'] += c.saldo_pendiente
            elif 1 <= dias_atraso <= 30:
                total_1_30 += c.saldo_pendiente
                row['venc_1_30'] += c.saldo_pendiente
            elif 31 <= dias_atraso <= 60:
                total_31_60 += c.saldo_pendiente
                row['venc_31_60'] += c.saldo_pendiente
            elif 61 <= dias_atraso <= 90:
                total_61_90 += c.saldo_pendiente
                row['venc_61_90'] += c.saldo_pendiente
            else:
                total_mas_90 += c.saldo_pendiente
                row['venc_mas_90'] += c.saldo_pendiente

        context['total_cartera'] = total_al_dia + total_1_30 + total_31_60 + total_61_90 + total_mas_90
        context['total_al_dia'] = total_al_dia
        context['total_1_30'] = total_1_30
        context['total_31_60'] = total_31_60
        context['total_61_90'] = total_61_90
        context['total_mas_90'] = total_mas_90
        context['alumnos_antiguedad'] = sorted(detalles_alumnos.values(), key=lambda x: x['total_saldo'], reverse=True)
        return context
