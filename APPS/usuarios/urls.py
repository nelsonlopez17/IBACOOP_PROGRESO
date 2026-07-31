"""
APPS/usuarios/urls.py

Rutas URL para autenticación y administración de usuarios.
"""
from django.contrib.auth import views as auth_views
from django.urls import path

from APPS.usuarios import views

app_name = 'usuarios'

urlpatterns = [
    # Autenticación nativa (Login / Logout)
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='usuarios/login.html',
            redirect_authenticated_user=True
        ),
        name='login'
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),

    # Gestión (CRUD) de Usuarios
    path('', views.UsuarioListView.as_view(), name='usuario_list'),
    path('crear/', views.UsuarioCreateView.as_view(), name='usuario_create'),
    path('<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update'),

    # Alias por compatibilidad de rutas
    path('usuarios/', views.UsuarioListView.as_view(), name='usuario_list_alias'),
    path('usuarios/crear/', views.UsuarioCreateView.as_view(), name='usuario_create_alias'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update_alias'),
]
