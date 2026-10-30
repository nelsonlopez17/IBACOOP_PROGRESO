"""
portal/urls.py

Rutas del Portal Web Público Institucional y del Módulo Administrativo de Gestión Web.
"""
from django.urls import path
from APPS.portal import views

app_name = 'portal'

urlpatterns = [
    # rutas publicas del portal
    path('', views.PortalIndexView.as_view(), name='index'),
    path('publicaciones/', views.PublicacionesPublicaListView.as_view(), name='publicaciones_todas'),
    path('publicacion/<int:pk>/', views.PublicacionDetallePublicaView.as_view(), name='publicacion_detalle'),
    path('nosotros/', views.NosotrosView.as_view(), name='nosotros'),
    path('oferta-academica/', views.OfertaAcademicaView.as_view(), name='oferta_academica'),
    path('admisiones/', views.AdmisionesView.as_view(), name='admisiones'),
    path('galeria/', views.GaleriaView.as_view(), name='galeria'),
    path('contacto/', views.ContactoView.as_view(), name='contacto'),

    # rutas de administracion interna del portal (direccion y secretaria)
    path('gestion/', views.PortalGestionDashboardView.as_view(), name='gestion_dashboard'),
    path('gestion/configuracion/', views.ConfiguracionPortalUpdateView.as_view(), name='gestion_configuracion'),

    # galeria de fotos (urls externas)
    path('gestion/galeria/', views.FotoGaleriaListView.as_view(), name='galeria_list'),
    path('gestion/galeria/nueva/', views.FotoGaleriaCreateView.as_view(), name='galeria_create'),
    path('gestion/galeria/<int:pk>/editar/', views.FotoGaleriaUpdateView.as_view(), name='galeria_update'),
    path('gestion/galeria/<int:pk>/eliminar/', views.FotoGaleriaDeleteView.as_view(), name='galeria_delete'),

    # publicaciones y comunicados
    path('gestion/publicaciones/', views.ContenidoWebListView.as_view(), name='publicaciones_list'),
    path('gestion/publicaciones/nueva/', views.ContenidoWebCreateView.as_view(), name='publicaciones_create'),
    path('gestion/publicaciones/<int:pk>/editar/', views.ContenidoWebUpdateView.as_view(), name='publicaciones_update'),
    path('gestion/publicaciones/<int:pk>/eliminar/', views.ContenidoWebDeleteView.as_view(), name='publicaciones_delete'),

    # bandeja de solicitudes de contacto
    path('gestion/solicitudes/', views.BandejaContactoListView.as_view(), name='solicitudes_list'),
    path('gestion/solicitudes/<int:pk>/', views.AtenderSolicitudContactoView.as_view(), name='solicitud_detalle'),
    path('gestion/solicitudes/<int:pk>/atender-rapido/', views.MarcarSolicitudAtendidaRapidoView.as_view(), name='solicitud_marcar_atendido'),
]
