from django.db import migrations
from django.contrib.auth.hashers import make_password


def crear_admin(apps, schema_editor):
    # creacion de superusuario administrador para pruebas
    Usuario = apps.get_model('usuarios', 'Usuario')
    admin, created = Usuario.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@ibacoop.edu.gt',
            'first_name': 'Administrador',
            'last_name': 'Principal',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'rol': 'ADMINISTRADOR',
            'debe_cambiar_password': False,
            'password': make_password('admin'),
        }
    )
    if not created:
        admin.password = make_password('admin')
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.rol = 'ADMINISTRADOR'
        admin.debe_cambiar_password = False
        admin.save()


def revertir_admin(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_alter_usuario_rol'),
    ]

    operations = [
        migrations.RunPython(crear_admin, revertir_admin),
    ]
