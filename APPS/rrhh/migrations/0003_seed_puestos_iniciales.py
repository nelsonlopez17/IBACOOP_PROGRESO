from django.db import migrations

def crear_puestos_iniciales(apps, schema_editor):
    Puesto = apps.get_model('rrhh', 'Puesto')
    puestos_default = [
        ('Director General', 'Dirección general, administrativa y académica del instituto.'),
        ('Docente / Catedrático', 'Personal docente encargados de impartir asignaturas del CNB Nivel Medio.'),
        ('Secretaria de Dirección', 'Gestión de expedientes de alumnos, papelería oficial y archivo.'),
        ('Contador General', 'Administración de finanzas, cobro de colegiaturas y planillas.'),
        ('Coordinador Académico', 'Supervisión docente, horarios y planificación escolar.'),
        ('Auxiliar Administrativo', 'Apoyo operativo a secretaría y contabilidad.'),
        ('Personal de Servicios / Conserjería', 'Mantenimiento, instalaciones y servicios generales.'),
    ]
    for nombre, desc in puestos_default:
        Puesto.objects.get_or_create(
            nombre_puesto=nombre,
            defaults={'descripcion': desc}
        )

def revertir_puestos_iniciales(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('rrhh', '0002_personal_contacto_emergencia_nombre_and_more'),
    ]

    operations = [
        migrations.RunPython(crear_puestos_iniciales, reverse_code=revertir_puestos_iniciales),
    ]
