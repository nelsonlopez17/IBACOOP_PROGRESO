"""
Vistas para administrar los usuarios del sistema.
Todas las pantallas están protegidas para que solo usuarios autorizados y con permisos puedan ingresar.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from APPS.usuarios.models import Usuario
from APPS.usuarios.forms import CustomUserCreationForm, CustomUserChangeForm


class UsuarioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para mostrar el listado de usuarios registrados.

    Seguridad:
        - Requiere haber iniciado sesión.
        - Requiere permiso para ver usuarios.
        - Deniega el acceso si el usuario no tiene permiso.
    """
    model = Usuario
    template_name = 'usuarios/usuario_list.html'
    context_object_name = 'usuarios'
    paginate_by = 10
    permission_required = 'usuarios.view_usuario'
    raise_exception = True

    def get_queryset(self):
        # Carga eficiente de datos para acelerar la respuesta de la lista
        return Usuario.objects.all().prefetch_related('groups').order_by('-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Gestión de Usuarios'
        return context


class UsuarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Vista para registrar un nuevo usuario en el sistema.

    Seguridad:
        - Requiere haber iniciado sesión.
        - Requiere permiso para agregar usuarios.
        - Deniega el acceso si el usuario no tiene permiso.
    """
    model = Usuario
    form_class = CustomUserCreationForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuarios:usuario_list')
    permission_required = 'usuarios.add_usuario'
    raise_exception = True
    success_message = "El usuario '%(username)s' fue creado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Crear Nuevo Usuario'
        context['accion'] = 'Crear'
        return context


class UsuarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Vista para modificar los datos de un usuario existente.

    Seguridad:
        - Requiere haber iniciado sesión.
        - Requiere permiso para modificar usuarios.
        - Deniega el acceso si el usuario no tiene permiso.
    """
    model = Usuario
    form_class = CustomUserChangeForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuarios:usuario_list')
    permission_required = 'usuarios.change_usuario'
    raise_exception = True
    success_message = "El usuario '%(username)s' fue actualizado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Usuario: {self.object.username}"
        context['accion'] = 'Guardar Cambios'
        return context
