"""
APPS/inventario/urls.py

Configuración de URLs del Módulo de Inventario y Control de Activos.
"""
from django.urls import path
from APPS.inventario import views

app_name = 'inventario'

urlpatterns = [
    path('', views.ArticuloInventarioListView.as_view(), name='articulo_list'),
    path('mis-articulos/', views.MisArticulosAsignadosListView.as_view(), name='mis_articulos'),
    path('nuevo/', views.ArticuloInventarioCreateView.as_view(), name='articulo_create'),
    path('<int:pk>/', views.ArticuloInventarioDetailView.as_view(), name='articulo_detail'),
    path('<int:pk>/editar/', views.ArticuloInventarioUpdateView.as_view(), name='articulo_update'),

    path('movimiento/nuevo/', views.MovimientoInventarioCreateView.as_view(), name='movimiento_create'),

    path('reporte/pdf/', views.descargar_inventario_pdf, name='inventario_pdf'),
    path('movimiento/<int:pk>/pdf/', views.descargar_movimiento_pdf, name='movimiento_pdf'),
]
