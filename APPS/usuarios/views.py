"""
APPS/usuarios/views.py

Vistas para administrar los usuarios del sistema, control de accesos (IAM),
restablecimiento de credenciales, cambio de estado, descarga de comprobantes PDF,
y autoservicio de perfil ("Mi Perfil") y cambio seguro de contraseña.
"""
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, TemplateView

from APPS.usuarios.models import Usuario, RolChoices
from APPS.usuarios.forms import CustomUserCreationForm, CustomUserChangeForm, MiPerfilContactoForm, MiPasswordChangeForm
from APPS.usuarios.utils import generar_clave_temporal, generar_pdf_credenciales_bytes


class UsuarioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para mostrar el directorio de usuarios con búsqueda, filtros y KPIs de seguridad.
    """
    model = Usuario
    template_name = 'usuarios/usuario_list.html'
    context_object_name = 'usuarios'
    paginate_by = 12
    permission_required = 'usuarios.view_usuario'
    raise_exception = True

    def get_queryset(self):
        queryset = Usuario.objects.select_related('persona').prefetch_related('groups').order_by('-date_joined')

        # Filtro de búsqueda textual
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q) |
                Q(persona__cui__icontains=q) |
                Q(persona__nombres__icontains=q) |
                Q(persona__apellidos__icontains=q)
            )

        # Filtro por Rol
        rol_filter = self.request.GET.get('rol', '').strip()
        if rol_filter:
            queryset = queryset.filter(rol=rol_filter)

        # Filtro por Estado (Activo / Inactivo)
        estado_filter = self.request.GET.get('estado', '').strip()
        if estado_filter == 'activo':
            queryset = queryset.filter(is_active=True)
        elif estado_filter == 'inactivo':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_users = Usuario.objects.all()

        # Cálculo de KPIs
        context['total_usuarios'] = all_users.count()
        context['activos_count'] = all_users.filter(is_active=True).count()
        context['inactivos_count'] = all_users.filter(is_active=False).count()
        context['estudiantes_count'] = all_users.filter(rol=RolChoices.ESTUDIANTE).count()
        context['encargados_count'] = all_users.filter(rol=RolChoices.ENCARGADO).count()

        # Opciones para selectores en template
        context['rol_choices'] = RolChoices.choices
        context['q_actual'] = self.request.GET.get('q', '')
        context['rol_actual'] = self.request.GET.get('rol', '')
        context['estado_actual'] = self.request.GET.get('estado', '')
        context['titulo_pagina'] = 'Directorio y Control de Acceso de Usuarios'
        return context


class UsuarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Vista para registrar cuentas puramente administrativas de TI / Soporte.
    """
    model = Usuario
    form_class = CustomUserCreationForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuarios:usuario_list')
    permission_required = 'usuarios.add_usuario'
    raise_exception = True
    success_message = "La cuenta administrativa '%(username)s' fue creada exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Crear Cuenta Administrativa / TI'
        context['accion'] = 'Crear Usuario'
        return context


class UsuarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Vista para modificar roles visuales, grupos de permisos de Django y estado de la cuenta.
    """
    model = Usuario
    form_class = CustomUserChangeForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuarios:usuario_list')
    permission_required = 'usuarios.change_usuario'
    raise_exception = True
    success_message = "Los datos del usuario '%(username)s' fueron actualizados exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = f"Editar Permisos y Accesos: {self.object.username}"
        context['accion'] = 'Guardar Cambios'
        return context


class UsuarioToggleActiveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Vista rápida para activar o bloquear la cuenta de acceso de un usuario.
    """
    permission_required = 'usuarios.change_usuario'
    raise_exception = True

    def post(self, request, pk, *args, **kwargs):
        usuario = get_object_or_404(Usuario, pk=pk)
        if usuario == request.user:
            messages.error(request, "No puedes desactivar tu propia cuenta de sesión actual.")
            return redirect('usuarios:usuario_list')

        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])

        estado_txt = "activada" if usuario.is_active else "bloqueada/desactivada"
        messages.success(request, f"La cuenta del usuario '{usuario.username}' fue {estado_txt} correctamente.")
        return redirect('usuarios:usuario_list')


class UsuarioResetPasswordView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista para blanquear la contraseña de un usuario, asignando una clave temporal,
    marcando la bandera de cambio obligatorio de clave y ofreciendo descarga en PDF.
    """
    template_name = 'usuarios/usuario_reset_password.html'
    permission_required = 'usuarios.change_usuario'
    raise_exception = True

    def get(self, request, pk, *args, **kwargs):
        usuario = get_object_or_404(Usuario, pk=pk)
        return self.render_to_response({'usuario_target': usuario})

    def post(self, request, pk, *args, **kwargs):
        usuario = get_object_or_404(Usuario, pk=pk)
        clave_temporal = generar_clave_temporal()

        usuario.set_password(clave_temporal)
        usuario.debe_cambiar_password = True
        usuario.save(update_fields=['password', 'debe_cambiar_password'])

        # Guardar en sesión para la descarga única del PDF
        request.session[f'temp_pass_{usuario.pk}'] = clave_temporal

        messages.success(
            request,
            f"Contraseña de '{usuario.username}' restablecida con éxito. Clave temporal asignada: {clave_temporal}"
        )
        return self.render_to_response({
            'usuario_target': usuario,
            'clave_temporal': clave_temporal,
            'exito': True
        })


class UsuarioDescargarPdfCredencialesView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Genera y descarga la ficha en formato PDF con las credenciales temporales del usuario.
    """
    permission_required = 'usuarios.change_usuario'
    raise_exception = True

    def get(self, request, pk, *args, **kwargs):
        usuario = get_object_or_404(Usuario, pk=pk)
        clave_temporal = request.session.get(f'temp_pass_{usuario.pk}')

        if not clave_temporal:
            messages.warning(request, "No hay una contraseña temporal reciente en sesión. Por favor genere un restablecimiento de clave.")
            return redirect('usuarios:usuario_list')

        pdf_bytes = generar_pdf_credenciales_bytes(usuario, clave_temporal)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Credenciales_{usuario.username}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


# ==============================================================================
# AUTOSERVICIO DE USUARIO: "MI PERFIL" Y CAMBIO DE CONTRASEÑA
# ==============================================================================

class MiPerfilView(LoginRequiredMixin, TemplateView):
    """
    Pantalla de Autoservicio para que cualquier usuario consulte su perfil,
    consulte sus datos protegidos y edite sus datos de contacto de emergencia.
    """
    template_name = 'usuarios/mi_perfil.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user

        persona = getattr(usuario, 'persona', None)
        if 'contacto_form' not in context:
            if persona:
                context['contacto_form'] = MiPerfilContactoForm(instance=persona)
            else:
                context['contacto_form'] = None

        context['persona'] = persona
        context['titulo_pagina'] = 'Mi Perfil de Usuario'
        return context

    def post(self, request, *args, **kwargs):
        usuario = request.user
        persona = getattr(usuario, 'persona', None)

        if not persona:
            messages.error(request, "No hay un expediente de información personal vinculado a su cuenta.")
            return redirect('usuarios:mi_perfil')

        contacto_form = MiPerfilContactoForm(request.POST, instance=persona)
        if contacto_form.is_valid():
            contacto_form.save()
            messages.success(request, "Sus datos de contacto fueron actualizados exitosamente.")
            return redirect('usuarios:mi_perfil')

        return self.render_to_response({'contacto_form': contacto_form, 'persona': persona})


class CambiarMiPasswordView(LoginRequiredMixin, PasswordChangeView):
    """
    Vista para que el usuario actualice su propia contraseña de acceso.
    Desmarca la bandera `debe_cambiar_password` tras completar el cambio exitosamente.
    """
    form_class = MiPasswordChangeForm
    template_name = 'usuarios/cambiar_mi_password.html'
    success_url = reverse_lazy('usuarios:mi_perfil')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if getattr(user, 'debe_cambiar_password', False):
            user.debe_cambiar_password = False
            user.save(update_fields=['debe_cambiar_password'])

        # Mantener la sesión activa tras el cambio de clave
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Su contraseña se ha actualizado correctamente. La cuenta ha sido asegurada.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo_pagina'] = 'Actualizar Mi Contraseña'
        return context
