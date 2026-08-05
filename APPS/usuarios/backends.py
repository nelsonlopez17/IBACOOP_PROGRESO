"""
APPS/usuarios/backends.py

Backend de Autenticación Personalizado (Login Multicriterio).
Permite a cualquier usuario (Estudiante, Encargado, Personal) iniciar sesión
tecleando indistintamente su CUI / DPI (username) O su Correo Electrónico.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q


class CUIOrEmailModelBackend(ModelBackend):
    """
    Backend de autenticación que busca al usuario por CUI/Username O por Email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if not username or not password:
            return None

        username_clean = username.strip().lower()

        try:
            # Buscar por username (CUI/DPI) O por email (correo)
            user = UserModel.objects.filter(
                Q(username__iexact=username_clean) | Q(email__iexact=username_clean)
            ).first()

            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user
        except Exception:
            return None
        return None
