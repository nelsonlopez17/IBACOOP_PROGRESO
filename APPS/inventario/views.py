"""
APPS/inventario/views.py

Vistas Basadas en Clases (CBV) para el Módulo de Inventario y Control de Activos.
Incluye:
  1. ArticuloInventarioListView: Catálogo de artículos con filtros, búsqueda y alertas de stock bajo.
  2. ArticuloInventarioCreateView y UpdateView: Altas y modificaciones de bienes.
  3. ArticuloInventarioDetailView: Ficha 360° del bien con historial de transacciones y auditoría.
  4. MovimientoInventarioCreateView: Registro de entradas, salidas, consumos y asignaciones con actualización de stock.
  5. Descarga de Reportes en PDF (Catálogo completo y Vales de Resguardo).
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from APPS.inventario.models import (
    ArticuloInventario, MovimientoInventario, CategoriaChoices, TipoMovimientoChoices
)
from APPS.inventario.forms import ArticuloInventarioForm, MovimientoInventarioForm
from APPS.inventario.reportes import generar_pdf_reporte_inventario, generar_pdf_comprobante_movimiento


class ArticuloInventarioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista todos los artículos del inventario institucional con opciones de búsqueda y filtrado."""

    model = ArticuloInventario
    template_name = 'inventario/articulo_list.html'
    context_object_name = 'articulos'
    permission_required = 'inventario.view_articuloinventario'
    raise_exception = True
    paginate_by = 15

    def get_queryset(self):
        qs = ArticuloInventario.objects.filter(esta_eliminado=False)

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(codigo_unico__icontains=q) |
                Q(nombre__icontains=q) |
                Q(descripcion__icontains=q)
            )

        categoria = self.request.GET.get('categoria', '').strip()
        if categoria:
            qs = qs.filter(categoria=categoria)

        alerta = self.request.GET.get('alerta', '').strip()
        if alerta == '1':
            qs = qs.filter(stock_actual__lte=F('stock_minimo_alerta'))

        return qs.order_by('categoria', 'nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Control de Inventario y Bienes'
        context['q'] = self.request.GET.get('q', '')
        context['categoria_actual'] = self.request.GET.get('categoria', '')
        context['alerta_filtro'] = self.request.GET.get('alerta', '')
        context['categorias'] = CategoriaChoices.choices
        
        base_qs = ArticuloInventario.objects.filter(esta_eliminado=False)
        context['total_articulos'] = base_qs.count()
        context['articulos_alerta_count'] = base_qs.filter(stock_actual__lte=F('stock_minimo_alerta')).count()
        return context


class ArticuloInventarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Creación de un nuevo artículo en el inventario."""

    model = ArticuloInventario
    form_class = ArticuloInventarioForm
    template_name = 'inventario/articulo_form.html'
    permission_required = 'inventario.add_articuloinventario'
    raise_exception = True
    success_url = reverse_lazy('inventario:articulo_list')

    def form_valid(self, form):
        articulo = form.save()
        messages.success(self.request, f'✓ Artículo "{articulo.nombre}" registrado exitosamente en el inventario.')
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Registrar Nuevo Artículo'
        context['boton_label'] = 'Guardar Artículo'
        return context


class ArticuloInventarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Edición de datos de un artículo existente."""

    model = ArticuloInventario
    form_class = ArticuloInventarioForm
    template_name = 'inventario/articulo_form.html'
    permission_required = 'inventario.change_articuloinventario'
    raise_exception = True

    def get_queryset(self):
        return ArticuloInventario.objects.filter(esta_eliminado=False)

    def form_valid(self, form):
        articulo = form.save()
        messages.success(self.request, f'✓ Artículo "{articulo.nombre}" actualizado correctamente.')
        return redirect('inventario:articulo_detail', pk=articulo.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Editar Artículo — {self.object.nombre}'
        context['boton_label'] = 'Actualizar Cambios'
        return context


class ArticuloInventarioDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Ficha detallada del artículo con historial auditado de movimientos."""

    model = ArticuloInventario
    template_name = 'inventario/articulo_detail.html'
    context_object_name = 'articulo'
    permission_required = 'inventario.view_articuloinventario'
    raise_exception = True

    def get_queryset(self):
        return ArticuloInventario.objects.filter(esta_eliminado=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f'Detalle del Artículo — {self.object.nombre}'
        context['movimientos'] = self.object.movimientos.filter(
            esta_eliminado=False
        ).select_related('personal_responsable__persona', 'personal_responsable__puesto').order_by('-fecha')[:20]
        context['historial'] = self.object.history.all().order_by('-history_date')[:10]
        return context


class MovimientoInventarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Registro de transacciones de inventario con actualización atómica de stock."""

    model = MovimientoInventario
    form_class = MovimientoInventarioForm
    template_name = 'inventario/movimiento_form.html'
    permission_required = 'inventario.add_movimientoinventario'
    raise_exception = True
    success_url = reverse_lazy('inventario:articulo_list')

    def get_initial(self):
        initial = super().get_initial()
        articulo_pk = self.request.GET.get('articulo')
        if articulo_pk:
            initial['articulo'] = articulo_pk
        return initial

    def form_valid(self, form):
        movimiento = form.save(commit=False)
        movimiento.fecha = timezone.now()

        with transaction.atomic():
            articulo = movimiento.articulo
            tipo = movimiento.tipo_movimiento
            cantidad = movimiento.cantidad

            if tipo in [TipoMovimientoChoices.ENTRADA, TipoMovimientoChoices.DEVOLUCION]:
                articulo.stock_actual += cantidad
            elif tipo in [TipoMovimientoChoices.SALIDA, TipoMovimientoChoices.ASIGNACION, TipoMovimientoChoices.BAJA]:
                articulo.stock_actual = max(articulo.stock_actual - cantidad, 0)
            elif tipo == TipoMovimientoChoices.AJUSTE:
                articulo.stock_actual = cantidad

            articulo.save(update_fields=['stock_actual', 'actualizado_en'])
            movimiento.save()

        messages.success(
            self.request,
            f'✓ Transacción "{movimiento.get_tipo_movimiento_display()}" registrada correctamente. '
            f'Stock actualizado de {articulo.nombre}: {articulo.stock_actual} {articulo.unidad_medida}.'
        )
        return redirect('inventario:articulo_detail', pk=articulo.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Registrar Transacción de Inventario'
        return context


@login_required
@permission_required('inventario.view_articuloinventario', raise_exception=True)
def descargar_inventario_pdf(request):
    """Genera y descarga el reporte en PDF del catálogo de inventario."""
    articulos = ArticuloInventario.objects.filter(esta_eliminado=False).order_by('categoria', 'nombre')
    
    cat = request.GET.get('categoria', '').strip()
    if cat:
        articulos = articulos.filter(categoria=cat)

    pdf_buffer = generar_pdf_reporte_inventario(articulos, titulo="Catálogo e Informe de Existencias")
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"Inventario_IBACOOP_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
@permission_required('inventario.view_movimientoinventario', raise_exception=True)
def descargar_movimiento_pdf(request, pk):
    """Genera y descarga el vale o comprobante de resguardo del movimiento en PDF."""
    movimiento = get_object_or_404(
        MovimientoInventario.objects.select_related(
            'articulo', 'personal_responsable__persona', 'personal_responsable__puesto'
        ),
        pk=pk,
        esta_eliminado=False
    )
    pdf_buffer = generar_pdf_comprobante_movimiento(movimiento)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"Vale_Resguardo_{movimiento.pk:06d}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
