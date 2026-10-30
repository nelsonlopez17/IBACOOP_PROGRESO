from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.db.models.deletion import RestrictedError
from django.test import TestCase
from django.urls import reverse

from APPS.academico.models import (
    AsignacionDocente,
    AsignacionEstudiante,
    BloqueAcademico,
    CicloEscolar,
    Curso,
    Grado,
    NotaBloque,
    NotaFinalCurso,
    Seccion,
)
from APPS.core.models import ContactoPersona, DocumentoExpediente, Persona
from APPS.estudiantes.models import Encargado, Estudiante, EstudianteEncargado
from APPS.financiero.models import Abono, ConceptoPago, CuentaPorCobrar, EstadoPagoChoices
from APPS.rrhh.models import Personal, Planilla, Puesto
from APPS.usuarios.models import RolChoices, Usuario


class SoftDeleteRestrictedErrorTestCase(TestCase):
    def test_soft_delete_raises_restricted_error_when_active_children_exist(self):
        # creacion de grado y seccion con restriccion de eliminacion
        grado = Grado.objects.create(nombre="Primero Básico Test", orden=1)
        seccion = Seccion.objects.create(grado=grado, letra="A", cupo_maximo=30)

        # verificacion de restriccion al eliminar registro padre con hijos activos
        with self.assertRaises(RestrictedError):
            grado.delete()

        # eliminacion logica previa de la seccion
        seccion.delete()

        # confirmacion de eliminacion del registro principal
        grado.delete()
        self.assertTrue(grado.esta_eliminado)


class Normalizacion4FNTestCase(TestCase):
    """Verifica el cumplimiento de 3FN, FNBC y 4FN y la retrocompatibilidad de propiedades y anotaciones SQL."""

    def test_4fn_documentos_y_contactos_estudiante_y_personal(self):
        usuario = Usuario.objects.create_user(username="3001112220101", password="Password123!", rol=RolChoices.ESTUDIANTE)
        persona = Persona.objects.create(
            usuario=usuario,
            cui="3001112220101",
            nombres="María Fernanda",
            apellidos="López García",
            correo="mflopez@ibacoop.edu.gt",
        )
        # verificacion de sincronizacion entre persona y usuario
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, "María Fernanda")
        self.assertEqual(usuario.last_name, "López García")

        persona_enc = Persona.objects.create(cui="2001112220101", nombres="Carlos", apellidos="López")
        encargado = Encargado.objects.create(persona=persona_enc, lugar_de_trabajo="Cooperativa")

        est, _ = Estudiante.objects.update_or_create(
            persona=persona,
            defaults={
                "codigo_mineduc": "MIN-4FN-01",
                "encargado": encargado,
                "nombre_padre": "Carlos López",
                "telefono_padre": "55551111",
                "nombre_madre": "Ana García",
                "telefono_madre": "55552222",
                "doc_cert_nacimiento_renap": True,
                "doc_dpi_encargado": True,
                "doc_certificado_grado_anterior": False,
            },
        )
        est.refresh_from_db()
        self.assertEqual(est.nombre_padre, "Carlos López")
        self.assertEqual(est.telefono_padre, "55551111")
        self.assertEqual(est.nombre_madre, "Ana García")
        self.assertTrue(est.doc_cert_nacimiento_renap)
        self.assertFalse(est.doc_certificado_grado_anterior)
        self.assertTrue(est.estado_activo)

        # verificacion de tablas normalizadas
        self.assertEqual(ContactoPersona.objects.filter(persona=persona).count(), 2)
        self.assertEqual(DocumentoExpediente.objects.filter(persona=persona, entregado=True).count(), 2)
        self.assertTrue(EstudianteEncargado.objects.filter(estudiante=est, encargado=encargado, es_contacto_principal=True).exists())

        # verificacion de filtrado sobre propiedades anotadas
        incompletos = Estudiante.objects.filter(Q(doc_certificado_grado_anterior=False))
        self.assertIn(est, incompletos)

    def test_3fn_y_fnbc_academico_y_financiero(self):
        ciclo = CicloEscolar.objects.create(anio=2026, estado_activo=True)
        g1 = Grado.objects.create(nombre="Primero Básico", orden=1)
        g2 = Grado.objects.create(nombre="Segundo Básico", orden=2)
        sec1 = Seccion.objects.create(grado=g1, letra="A")
        curso_g2 = Curso.objects.create(grado=g2, nombre_curso="Ciencias II", codigo_curso="CIE-2")

        p_doc = Persona.objects.create(cui="1999888770101", nombres="Pedro", apellidos="Méndez")
        puesto = Puesto.objects.create(nombre_puesto="Docente")
        docente = Personal.objects.create(
            persona=p_doc,
            puesto=puesto,
            fecha_contratacion=date(2025, 1, 10),
            salario_base_asignado=Decimal("4000.00"),
            contacto_emergencia_nombre="Lucía Méndez",
            contacto_emergencia_telefono="44443333",
            doc_dpi_personal=True,
        )
        docente.refresh_from_db()
        self.assertEqual(docente.contacto_emergencia_nombre, "Lucía Méndez")
        self.assertTrue(docente.doc_dpi_personal)

        # validacion para evitar asignacion de curso en seccion no correspondiente
        asig_invalida = AsignacionDocente(personal=docente, curso=curso_g2, seccion=sec1, ciclo_escolar=ciclo)
        with self.assertRaises(ValidationError):
            asig_invalida.full_clean()

        # calculo de total a pagar en planilla y filtrado
        pl = Planilla.objects.create(
            personal=docente,
            ciclo_escolar=ciclo,
            mes_pagado=1,
            bonificaciones=Decimal("250.00"),
            descuentos=Decimal("150.00"),
        )
        self.assertEqual(pl.total_pagar, Decimal("4100.00"))
        agg_pl = Planilla.objects.filter(pk=pl.pk).aggregate(s=Sum("total_pagar"))
        self.assertEqual(agg_pl["s"], Decimal("4100.00"))


class ValidacionFormulariosGuatemalaTestCase(TestCase):
    """
    Verifica las reglas de longitud y formato para datos de Guatemala
    tanto en el Backend (forms/validators), Base de Datos (models) como Frontend (widget.attrs HTML5).
    """

    def test_persona_form_validaciones_guatemala_y_atributos_html5(self):
        from APPS.core.forms import PersonaForm
        from APPS.usuarios.forms import MiPerfilContactoForm

        form = PersonaForm()
        self.assertEqual(form.fields['cui'].widget.attrs.get('minlength'), '13')
        self.assertEqual(form.fields['cui'].widget.attrs.get('maxlength'), '13')
        self.assertEqual(form.fields['nombres'].widget.attrs.get('minlength'), '2')
        self.assertEqual(form.fields['nombres'].widget.attrs.get('maxlength'), '100')
        self.assertEqual(form.fields['direccion'].widget.attrs.get('maxlength'), '300')
        self.assertEqual(form.fields['telefono_principal'].widget.attrs.get('minlength'), '8')
        self.assertEqual(form.fields['telefono_principal'].widget.attrs.get('maxlength'), '8')
        self.assertEqual(form.fields['telefono_secundario'].widget.attrs.get('minlength'), '8')
        self.assertEqual(form.fields['telefono_secundario'].widget.attrs.get('maxlength'), '8')

        # validacion de longitud en telefono y formato de identificador
        form_invalido = PersonaForm(data={
            'cui': '12345',
            'nombres': 'A',
            'apellidos': '12345',
            'telefono_principal': '555512349',
            'telefono_secundario': '1234',
        })
        self.assertFalse(form_invalido.is_valid())
        self.assertIn('cui', form_invalido.errors)
        self.assertIn('nombres', form_invalido.errors)
        self.assertIn('apellidos', form_invalido.errors)
        self.assertIn('telefono_principal', form_invalido.errors)
        self.assertIn('telefono_secundario', form_invalido.errors)

        # verificacion con datos validos de guatemala
        form_valido = PersonaForm(data={
            'cui': '2580123450101',
            'nombres': 'Juan Carlos',
            'apellidos': 'Pérez Morales',
            'telefono_principal': '55551234',
            'telefono_secundario': '44445678',
            'direccion': 'Barrio El Centro, San Agustín Acasaguastlán, El Progreso',
        })
        self.assertTrue(form_valido.is_valid(), form_valido.errors)
        self.assertEqual(form_valido.cleaned_data['telefono_principal'], '55551234')
        self.assertEqual(form_valido.cleaned_data['telefono_secundario'], '44445678')

        # formulario de autoservicio rechaza longitudes invalidas
        p_est = Persona.objects.create(cui='2580999990101', nombres='Isabella', apellidos='López')
        perfil_inv = MiPerfilContactoForm(
            data={
                'telefono_principal': '5555123456',
                'telefono_secundario': '444456789',
                'correo': 'isabella@ibacoop.edu.gt',
                'direccion': 'El Progreso',
            },
            instance=p_est,
        )
        self.assertFalse(perfil_inv.is_valid())
        self.assertIn('telefono_principal', perfil_inv.errors)
        self.assertIn('telefono_secundario', perfil_inv.errors)

    def test_rrhh_nit_sat_y_contacto_emergencia(self):
        from APPS.rrhh.forms import PersonalForm

        puesto = Puesto.objects.create(nombre_puesto='Secretaria General')
        # validacion de formato tributario y telefono
        form_inv = PersonalForm(data={
            'puesto': puesto.pk,
            'nit': 'NIT-INVALIDO-999',
            'fecha_contratacion': '2026-01-15',
            'estado_laboral': 'ACTIVO',
            'salario_base_asignado': '0.00',
            'contacto_emergencia_telefono': '999',
        })
        self.assertFalse(form_inv.is_valid())
        self.assertIn('nit', form_inv.errors)
        self.assertIn('salario_base_asignado', form_inv.errors)
        self.assertIn('contacto_emergencia_telefono', form_inv.errors)

        # verificacion con identificadores tributarios validos
        form_val = PersonalForm(data={
            'puesto': puesto.pk,
            'nit': '1234567-k',
            'fecha_contratacion': '2026-01-15',
            'estado_laboral': 'ACTIVO',
            'salario_base_asignado': '3800.00',
            'contacto_emergencia_nombre': 'Rosa Morales',
            'contacto_emergencia_telefono': '55112233',
        })
        self.assertTrue(form_val.is_valid(), form_val.errors)
        self.assertEqual(form_val.cleaned_data['nit'], '1234567-K')
        self.assertEqual(form_val.cleaned_data['contacto_emergencia_telefono'], '55112233')

    def test_financiero_beca_descuento_y_validaciones(self):
        from APPS.financiero.forms import BecaDescuentoForm
        from APPS.financiero.models import BecaDescuento

        p_enc = Persona.objects.create(cui='2111222330101', nombres='Mario', apellidos='Gómez')
        enc = Encargado.objects.create(persona=p_enc)
        p_est = Persona.objects.create(cui='3111222330101', nombres='Luis', apellidos='Gómez')
        est = Estudiante.objects.create(persona=p_est, codigo_mineduc='E999XYZ', encargado=enc)

        # validacion de datos minimos en registro de beca
        form_inv = BecaDescuentoForm(data={
            'estudiante': est.pk,
            'porcentaje_descuento': '0',
            'monto_descuento_fijo': '0',
            'motivo_convenio': 'Beca Cooperativa',
            'esta_activo': True,
        })
        self.assertFalse(form_inv.is_valid())

        # calculo correcto de porcentaje de descuento en beca
        beca = BecaDescuento.objects.create(
            estudiante=est,
            porcentaje_descuento=Decimal('20.00'),
            monto_descuento_fijo=Decimal('0.00'),
            motivo_convenio='Hijo de Cooperativista',
        )
        self.assertEqual(beca.calcular_monto_con_descuento(Decimal('150.00')), Decimal('120.00'))
        self.assertEqual(beca.motivo, 'Hijo de Cooperativista')


class ManejadorError403TestCase(TestCase):
    """
    pruebas del manejador personalizado de error 403 para redireccion
    al dashboard o al portal del visitante.
    """

    def setUp(self):
        self.usuario_sin_permiso = Usuario.objects.create_user(
            username='estudiante_403',
            email='est403@ibacoop.edu.gt',
            password='Password123!',
            rol=RolChoices.ESTUDIANTE,
            debe_cambiar_password=False,
        )

    def test_visitante_no_autenticado_es_redirigido_al_portal(self):
        # solicitud a modulo protegido sin haber iniciado sesion
        res = self.client.get(reverse('estudiantes:estudiante_list'))
        self.assertRedirects(res, reverse('portal:index'))

    def test_usuario_autenticado_sin_permiso_es_redirigido_al_dashboard(self):
        # usuario autenticado pero sin permisos del modulo rrhh o usuarios
        self.client.force_login(self.usuario_sin_permiso)
        res = self.client.get(reverse('rrhh:personal_list'))
        self.assertRedirects(res, reverse('core:home'))

    def test_solicitud_ajax_sin_permiso_retorna_403_json(self):
        # peticion asincrona denegada debe retornar 403 json
        self.client.force_login(self.usuario_sin_permiso)
        res = self.client.get(reverse('rrhh:personal_list'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res.status_code, 403)
        self.assertIn('error', res.json())

