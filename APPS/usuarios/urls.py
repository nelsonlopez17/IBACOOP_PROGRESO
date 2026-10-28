"""
APPS/usuarios/urls.py

Rutas URL para autenticación, administración de usuarios, control de accesos,
gestión de roles y grupos de permisos (RBAC), autoservicio de perfil ("Mi Perfil")
y descarga de comprobantes PDF de credenciales.
"""
from django.contrib.auth import views as auth_views
from django.urls import path

from APPS.usuarios import views

app_name = 'usuarios'

urlpatterns = [
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

    path('perfil/', views.MiPerfilView.as_view(), name='mi_perfil'),
    path('perfil/cambiar-password/', views.CambiarMiPasswordView.as_view(), name='cambiar_mi_password'),

    # Directorio y gestión de usuarios
    path('', views.UsuarioListView.as_view(), name='usuario_list'),
    path('crear/', views.UsuarioCreateView.as_view(), name='usuario_create'),
    path('<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update'),
    path('<int:pk>/toggle-activo/', views.UsuarioToggleActiveView.as_view(), name='usuario_toggle_active'),
    path('<int:pk>/reset-password/', views.UsuarioResetPasswordView.as_view(), name='usuario_reset_password'),
    path('<int:pk>/descargar-pdf/', views.UsuarioDescargarPdfCredencialesView.as_view(), name='usuario_descargar_pdf'),

    # Gestión de Roles y Grupos de Permisos
    path('roles/', views.GrupoListView.as_view(), name='grupo_list'),
    path('roles/crear/', views.GrupoCreateView.as_view(), name='grupo_create'),
    path('roles/<int:pk>/editar/', views.GrupoUpdateView.as_view(), name='grupo_update'),
    path('roles/<int:pk>/eliminar/', views.GrupoDeleteView.as_view(), name='grupo_delete'),

    path('usuarios/', views.UsuarioListView.as_view(), name='usuario_list_alias'),
    path('usuarios/crear/', views.UsuarioCreateView.as_view(), name='usuario_create_alias'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update_alias'),
]
