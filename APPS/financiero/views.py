"""
APPS/financiero/views.py

Vistas Basadas en Clases (CBV) para la gestión del Módulo Financiero / Cuentas por Cobrar.
Incluye: Catálogo de Conceptos, Emisión Masiva e Individual de Cargos, Estado de Cuenta Corriente del Estudiante,
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
from django.core.exceptions import PermissionDenied
from datetime import datetime
from django.utils import timezone
from django.views import View
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, FormView, TemplateView

from APPS.financiero.models import (
    ConceptoPago, CuentaPorCobrar, Abono, BecaDescuento, EstadoPagoChoices, CategoriaConceptoChoices, MetodoPagoChoices
)
from APPS.financiero.forms import (
    ConceptoPagoForm, CuentaPorCobrarForm, GenerarCobroMasivoForm, AbonoForm, BecaDescuentoForm
)
from APPS.financiero.reports import generar_pdf_recibo_pago, generar_pdf_solvencia_estudiante
from APPS.academico.models import CicloEscolar, AsignacionEstudiante
from APPS.estudiantes.models import Estudiante
from APPS.rrhh.models import (
    Planilla, Personal, EstadoLaboralChoices, MesChoices, TipoPlanillaChoices
)
from APPS.rrhh.forms import (
    PlanillaGenerarMasivaForm, PlanillaUpdateForm
)
from APPS.rrhh.reportes import generar_pdf_comprobante_planilla



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
    """Creación de un nuevo concepto de pago (cuota/actividad)."""

    model = ConceptoPago
    form_class = ConceptoPagoForm
    template_name = 'financiero/concepto_form.html'
    permission_required = 'financiero.add_conceptopago'
    raise_exception = True
    success_url = reverse_lazy('financiero:concepto_list')

    def form_valid(self, form):
        concepto = form.save()
        messages.success(
            self.request,
            f'✓ Concepto de cobro "{concepto.nombre}" guardado en el catálogo. '
            f'Puedes aplicarlo a un grado o sección con el botón "Cobrar a Grado".'
        )
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
        concepto_id = self.request.GET.get('concepto')
        if concepto_id:
            try:
                c = ConceptoPago.objects.get(pk=concepto_id, esta_eliminado=False)
                initial['concepto'] = c.pk
                initial['monto_total'] = c.monto_estandar
            except ConceptoPago.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        cuenta = form.save(commit=False)
        if not cuenta.monto_total and cuenta.concepto and cuenta.concepto.monto_estandar:
            cuenta.monto_total = cuenta.concepto.monto_estandar
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
        import json
        conceptos_precios = {
            str(c.id): str(c.monto_estandar)
            for c in ConceptoPago.objects.filter(esta_eliminado=False)
        }
        context['conceptos_precios_json'] = json.dumps(conceptos_precios)
        return context


class GenerarCobroMasivoView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Vista para la emisión masiva de cobros por Grado, Sección o a todos los estudiantes activos.
    Permite generar cuotas masivas como Inscripción, Cuota Mensual o Acto de Graduación.
    """

    form_class = GenerarCobroMasivoForm
    template_name = 'financiero/generar_cobro_masivo.html'
    permission_required = 'financiero.add_cuentaporcobrar'
    raise_exception = True
    success_url = reverse_lazy('financiero:cuentaporcobrar_list')

    def get_initial(self):
        initial = super().get_initial()
        concepto_id = self.request.GET.get('concepto')
        if concepto_id:
            try:
                c = ConceptoPago.objects.get(pk=concepto_id, esta_eliminado=False)
                initial['concepto'] = c
                initial['monto_override'] = c.monto_estandar
            except ConceptoPago.DoesNotExist:
                pass
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Emisión Masiva de Cuentas por Cobrar'
        import json
        from APPS.academico.models import Seccion
        secciones = list(Seccion.objects.filter(esta_eliminado=False).values('id', 'grado_id', 'letra'))
        context['secciones_json'] = json.dumps(secciones)
        return context

    def form_valid(self, form):
        concepto = form.cleaned_data['concepto']
        ciclo = form.cleaned_data['ciclo_escolar']
        grado = form.cleaned_data['grado']
        seccion = form.cleaned_data['seccion']
        monto_custom = form.cleaned_data['monto_override']
        fecha_limite = form.cleaned_data['fecha_limite_pago']

        monto_aplicar = monto_custom if monto_custom is not None else concepto.monto_estandar

        # obtener estudiantes para la asignacion de cuotas
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
                    # evitar duplicar el mismo cobro en el ciclo para el estudiante
                existe = CuentaPorCobrar.objects.filter(
                    estudiante=estudiante,
                    concepto=concepto,
                    ciclo_escolar=ciclo,
                    esta_eliminado=False
                ).exists()

                if not existe:
                    # verificar si el estudiante cuenta con beca activa
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

    def has_permission(self):
        if super().has_permission():
            return True
        try:
            from APPS.usuarios.permisos import es_titular_o_encargado_de_estudiante
            return es_titular_o_encargado_de_estudiante(self.request.user, self.get_object())
        except Exception:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.object

        cuentas = CuentaPorCobrar.objects.filter(
            estudiante=estudiante,
            esta_eliminado=False
        ).select_related('concepto', 'ciclo_escolar').order_by('-ciclo_escolar__anio', 'fecha_limite_pago')

        agg_totales = cuentas.aggregate(
            sum_total=Sum('monto_total'),
            sum_saldo=Sum('saldo_pendiente')
        )

        total_deuda = agg_totales['sum_total'] or Decimal('0.00')
        saldo_pendiente_total = agg_totales['sum_saldo'] or Decimal('0.00')
        total_pagado = total_deuda - saldo_pendiente_total

        # determinacion del estado de solvencia escolar
        es_solvente = (saldo_pendiente_total == Decimal('0.00'))

        abonos_historial = Abono.objects.filter(
            cuenta_por_cobrar__estudiante=estudiante,
            esta_eliminado=False
        ).select_related('cuenta_por_cobrar__concepto').order_by('-fecha_pago', '-creado_en')

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

        with transaction.atomic():
            # bloqueo pesimista para prevenir condiciones de carrera en el pago
            cuenta = CuentaPorCobrar.objects.select_for_update().get(pk=self.cuenta_por_cobrar.pk)
            if abono.monto_pagado > cuenta.saldo_pendiente:
                messages.error(
                    self.request,
                    f'El monto a abonar (Q{abono.monto_pagado}) excede el saldo pendiente actual (Q{cuenta.saldo_pendiente}).'
                )
                return self.form_invalid(form)
            abono.cuenta_por_cobrar = cuenta
            abono.save()

        messages.success(
            self.request,
            f'✓ {abono.get_metodo_pago_display()} por Q{abono.monto_pagado} registrado con éxito con comprobante "{abono.numero_boleta}".'
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
        metodo = self.request.GET.get('metodo')
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

        if metodo:
            qs = qs.filter(metodo_pago=metodo)

        if fecha_desde:
            qs = qs.filter(fecha_pago__gte=fecha_desde)

        if fecha_hasta:
            qs = qs.filter(fecha_pago__lte=fecha_hasta)

        return qs.order_by('-fecha_pago', '-creado_en')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Recibos de Cobro (Caja e Ingresos)'
        context['q'] = self.request.GET.get('q', '')
        context['metodos_pago'] = MetodoPagoChoices.choices
        context['metodo_sel'] = self.request.GET.get('metodo', '')
        context['fecha_desde'] = self.request.GET.get('fecha_desde', '')
        context['fecha_hasta'] = self.request.GET.get('fecha_hasta', '')
        return context



@login_required
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

    from APPS.usuarios.permisos import es_titular_o_encargado_de_estudiante
    user = request.user
    es_personal = user.has_perm('financiero.view_abono') or user.is_superuser or user.rol in ['ADMINISTRADOR', 'DIRECTOR', 'CONTADOR', 'SECRETARIA']
    est = abono.cuenta_por_cobrar.estudiante
    es_duenio = es_titular_o_encargado_de_estudiante(user, est)

    if not (es_personal or es_duenio):
        raise PermissionDenied("No tiene autorización para descargar o visualizar este recibo de pago.")

    return generar_pdf_recibo_pago(abono)


@login_required
def descargar_solvencia_pdf(request, pk):
    """Servicio HTTP para descargar o visualizar la Constancia de Solvencia Financiera en PDF."""
    estudiante = get_object_or_404(Estudiante, pk=pk, persona__esta_eliminado=False)

    from APPS.usuarios.permisos import es_titular_o_encargado_de_estudiante
    user = request.user
    es_personal = user.has_perm('financiero.view_cuentaporcobrar') or user.is_superuser or user.rol in ['ADMINISTRADOR', 'DIRECTOR', 'CONTADOR', 'SECRETARIA']
    es_duenio = es_titular_o_encargado_de_estudiante(user, estudiante)

    if not (es_personal or es_duenio):
        raise PermissionDenied("No tiene autorización para descargar la solvencia de este estudiante.")
    
    # verificar que el estudiante no mantenga saldos pendientes
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
    """Emisión en lote del Calendario Anual de 10 Cuotas Mensuales (Enero a Octubre)."""

    template_name = 'financiero/calendario_anual_form.html'
    permission_required = 'financiero.add_cuentaporcobrar'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Generación de Calendario Anual de Cuotas Mensuales'
        context['ciclos'] = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).order_by('-anio')
        context['ciclo_activo'] = CicloEscolar.objects.filter(estado_activo=True, esta_eliminado=False).first()
        context['concepto_colegiatura'] = ConceptoPago.objects.filter(
            categoria_concepto=CategoriaConceptoChoices.COLEGIATURA,
            esta_eliminado=False
        ).first() or ConceptoPago.objects.filter(nombre__icontains='cuota', esta_eliminado=False).first()
        return context

    def post(self, request, *args, **kwargs):
        ciclo_id = request.POST.get('ciclo_escolar')
        concepto_id = request.POST.get('concepto')
        try:
            dia_vencimiento = int(request.POST.get('dia_vencimiento', 5))
        except (TypeError, ValueError):
            messages.error(request, 'El día límite de vencimiento debe ser un número entero entre 1 y 28.')
            return redirect('financiero:calendario_anual')

        if dia_vencimiento < 1 or dia_vencimiento > 28:
            messages.error(request, 'El día límite de vencimiento debe estar comprendido entre 1 y 28.')
            return redirect('financiero:calendario_anual')

        ciclo = get_object_or_404(CicloEscolar, pk=ciclo_id, estado_activo=True, esta_eliminado=False)
        concepto = get_object_or_404(ConceptoPago, pk=concepto_id, esta_eliminado=False)

        estudiantes = Estudiante.objects.filter(
            asignaciones__ciclo_escolar=ciclo,
            persona__esta_eliminado=False,
            estado_estudiante='ACTIVO'
        ).distinct()

        if not estudiantes.exists():
            messages.error(request, 'No se encontraron estudiantes activos asignados al ciclo seleccionado.')
            return redirect('financiero:calendario_anual')

        # meses correspondientes a cuotas escolares regulares
        nombres_meses = [
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre')
        ]

        total_emitidos = 0
        from datetime import date

        with transaction.atomic():
            for est in estudiantes:
                # verificar asignacion de beca vigente
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

                    # registrar cuota mensual si no existe previamente
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
            f'✓ Calendario Anual Generado: Se crearon {total_emitidos} cobros de cuotas mensuales (Enero-Octubre {ciclo.anio}).'
        )
        return redirect('financiero:cuentaporcobrar_list')


class AntiguedadSaldosView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Tablero ejecutivo de Antigüedad de Cartera y Saldos Vencidos."""

    template_name = 'financiero/antiguedad_saldos.html'
    permission_required = 'financiero.view_cuentaporcobrar'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Tablero de Saldos Vencidos y Morosidad'

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


# ==============================================================================
# VISTAS DE PLANILLAS DE SUELDOS (GESTIÓN FINANCIERA / NÓMINA)
# ==============================================================================

class PlanillaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Listado general de pagos de planilla mensuales del personal."""

    login_url = 'usuarios:login'
    permission_required = 'rrhh.view_planilla'
    raise_exception = True
    model = Planilla
    template_name = 'financiero/planilla_list.html'
    context_object_name = 'planillas'
    paginate_by = 30

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
        context['hoy'] = timezone.now().date()

        base_qs = self.get_queryset()
        total_planilla = sum(p.total_pagar for p in base_qs)
        context['total_planilla'] = total_planilla
        context['total_nomina'] = total_planilla
        context['total_empleados_planilla'] = base_qs.count()
        context['total_pagados'] = base_qs.filter(pagado=True).count()
        context['total_pendientes'] = base_qs.filter(pagado=False).count()
        return context


class PlanillaGenerarMasivaView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """Proceso automatizado de cálculo y emisión masiva de la planilla de sueldos (Ordinaria, Bono 14, Aguinaldo o Extraordinaria)."""

    login_url = 'usuarios:login'
    permission_required = 'rrhh.add_planilla'
    raise_exception = True
    form_class = PlanillaGenerarMasivaForm
    template_name = 'financiero/planilla_generar.html'
    success_url = reverse_lazy('financiero:planilla_list')

    def form_valid(self, form):
        ciclo = form.cleaned_data['ciclo_escolar']
        tipo_planilla = form.cleaned_data['tipo_planilla']
        mes = int(form.cleaned_data['mes_pagado'])
        bono_ley = form.cleaned_data['bonificacion_ley']
        descontar_igss = form.cleaned_data['descontar_igss']
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

                if tipo_planilla == TipoPlanillaChoices.BONO_14:
                    mes = MesChoices.JULIO
                    bono_inc = Decimal('0.00')
                    cuota_igss = Decimal('0.00')
                elif tipo_planilla == TipoPlanillaChoices.AGUINALDO:
                    mes = MesChoices.DICIEMBRE
                    bono_inc = Decimal('0.00')
                    cuota_igss = Decimal('0.00')
                elif tipo_planilla == TipoPlanillaChoices.EXTRAORDINARIA:
                    bono_inc = Decimal('0.00')
                    cuota_igss = Decimal('0.00')
                else:
                    bono_inc = bono_ley
                    cuota_igss = round(sueldo_base * Decimal('0.0483'), 2) if descontar_igss else Decimal('0.00')

                Planilla.objects.update_or_create(
                    personal=emp,
                    mes_pagado=mes,
                    ciclo_escolar=ciclo,
                    tipo_planilla=tipo_planilla,
                    defaults={
                        'bonificacion_incentivo': bono_inc,
                        'bonificaciones': Decimal('0.00'),
                        'descuento_igss': cuota_igss,
                        'descuento_anticipo': Decimal('0.00'),
                        'descuento_judicial': Decimal('0.00'),
                        'descuento_otros': Decimal('0.00'),
                        'motivo_otros_descuentos': '',
                        'descuentos': cuota_igss,
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
    template_name = 'financiero/planilla_form.html'
    success_url = reverse_lazy('financiero:planilla_list')

    def get_queryset(self):
        return Planilla.objects.select_related('personal__persona', 'personal__puesto', 'ciclo_escolar').filter(esta_eliminado=False)

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.pagado:
            messages.warning(
                request,
                f"La boleta de pago de {obj.personal.persona.nombre_completo} ({obj.get_mes_pagado_display()} {obj.ciclo_escolar.anio}) ya se encuentra en estado 'PAGADO' y no puede ser modificada."
            )
            return redirect('financiero:planilla_detail', pk=obj.pk)
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


class PlanillaLiquidarMasivoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Permite al Contador marcar como pagadas múltiples boletas de planilla en lote."""

    login_url = 'usuarios:login'
    permission_required = 'rrhh.change_planilla'

    def post(self, request, *args, **kwargs):
        ids = request.POST.getlist('planillas_ids')
        if not ids:
            messages.warning(request, "No seleccionó ninguna boleta de planilla para liquidar.")
            return redirect('financiero:planilla_list')

        fecha_pago_raw = request.POST.get('fecha_pago')
        try:
            fecha_pago = datetime.strptime(fecha_pago_raw, '%Y-%m-%d').date() if fecha_pago_raw else timezone.now().date()
        except (ValueError, TypeError):
            fecha_pago = timezone.now().date()

        with transaction.atomic():
            planillas = Planilla.objects.filter(pk__in=ids, esta_eliminado=False, pagado=False)
            conteo = planillas.count()
            total_liquidado = sum(p.total_pagar for p in planillas)
            planillas.update(
                pagado=True,
                fecha_pago=fecha_pago
            )

        messages.success(
            request,
            f"✓ Se cambiaron a estado 'PAGADO' {conteo} boletas de planilla (Total liquidado: Q {total_liquidado:,.2f}) con fecha {fecha_pago.strftime('%d/%m/%Y')}."
        )
        return redirect('financiero:planilla_list')


class PlanillaDetailView(LoginRequiredMixin, DetailView):
    """Vista de detalle / vista previa en pantalla de la Boleta de Pago de Planilla en Financiero."""

    login_url = 'usuarios:login'
    model = Planilla
    template_name = 'financiero/planilla_detail.html'
    context_object_name = 'planilla'

    def get_queryset(self):
        return Planilla.objects.select_related(
            'personal__persona', 'personal__puesto', 'ciclo_escolar'
        ).filter(esta_eliminado=False)

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        es_titular = getattr(obj.personal.persona, 'usuario_id', None) == request.user.id
        if not (request.user.has_perm('rrhh.view_planilla') or request.user.has_perm('financiero.view_cuentaporcobrar') or es_titular):
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
    es_titular = getattr(planilla.personal.persona, 'usuario_id', None) == request.user.id
    if not (request.user.has_perm('rrhh.view_planilla') or es_titular):
        raise PermissionDenied("No tiene autorización para descargar esta boleta de pago de planilla.")
    return generar_pdf_comprobante_planilla(planilla)

