# Contexto Técnico y Arquitectura del Proyecto
## Sistema de Gestión Escolar — Instituto "El Progreso" (ERP Educativo)

> **Centro Educativo:** Instituto de Educación Básica "El Progreso" (Guatemala)  
> **Nivel Educativo:** Nivel de Educación Media — Ciclo de Educación Básica (1ro, 2do y 3ro Básico)  
> **Stack Tecnológico:** Python 3.12, Django 6.0, PostgreSQL 16, Gunicorn 23.0, WhiteNoise 6.9, Django Templates, Tailwind CSS v4, DaisyUI, HTMX 1.9, ReportLab 4.4, `django-simple-history`  
> **Paleta Institucional:** Rojo Institucional (`#7A1C21`), Verde Oscuro (`#1E6532`), Azul Océano (`#3C7DA8`), Azul Cielo (`#5D9CEC`), Verde Claro (`#42A855`).  
> **Despliegue y Orquestación:** Docker, Docker Compose (`ibacoop_web` + `ibacoop_db`).

---

## 📋 Índice

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Principios de Arquitectura y Reglas de Negocio](#2-principios-de-arquitectura-y-reglas-de-negocio)
3. [Patrón Supertipo / Subtipo (Herencia Persona)](#3-patrón-supertipo--subtipo-herencia-persona)
4. [Estrategia de Autenticación, Usuarios y Login Multicriterio](#4-estrategia-de-autenticación-usuarios-y-login-multicriterio)
5. [Estructura del Proyecto y Aplicaciones](#5-estructura-del-proyecto-y-aplicaciones)
6. [Diccionario de Datos y Modelos Refactorizados](#6-diccionario-de-datos-y-modelos-refactorizados)
7. [Subsistemas Específicos (Registro de Alumnos, Académico, Financiero, Inventarios)](#7-subsistemas-específicos-registro-de-alumnos-académico-financiero-inventarios)
8. [Vistas Basadas en Clases (CBV), Formularios, Validaciones y PDF](#8-vistas-basadas-en-clases-cbv-formularios-validaciones-y-pdf)
9. [Diseño Visual, Plantillas HTML y Menú Principal](#9-diseño-visual-plantillas-html-y-menú-principal)
10. [Arquitectura Docker y Comandos de Administración](#10-arquitectura-docker-y-comandos-de-administración)

---

## 1. Resumen Ejecutivo

El **Sistema de Gestión Escolar del Instituto "El Progreso"** es una plataforma ERP integral desarrollada para automatizar la gestión académica, administrativa, financiera, de recursos humanos, control de inventarios y presencia web institucional de un centro de Educación Básica en Guatemala.

El sistema está diseñado siguiendo las normativas del **Ministerio de Educación de Guatemala (MINEDUC)** para el Nivel Básico, garantizando la trazabilidad total de expedientes, notas, cobros e inventarios mediante auditoría de cambios (`django-simple-history`) y borrado lógico (*Soft Delete*).

---

## 2. Principios de Arquitectura y Reglas de Negocio

### 2.1 Eliminación Lógica (*Soft Delete*) e Integridad Referencial
**Regla:** Ningún registro de la base de datos se elimina físicamente.

- **`ModeloAuditable` (`APPS/core/models.py`)**: Modelo abstracto base del que heredan todos los modelos operativos del sistema (excepto `Usuario` que extiende `AbstractUser`).
  - `creado_en` (`DateTimeField`, `auto_now_add=True`)
  - `actualizado_en` (`DateTimeField`, `auto_now=True`)
  - `esta_eliminado` (`BooleanField`, `default=False`)
- **`ActivosManager`**: Manager por defecto (`objects`) que aplica automáticamente el filtro `esta_eliminado=False` a todos los QuerySets.
- **Manager `todos`**: Manager secundario (`todos`) que permite consultar la totalidad de registros (activos y eliminados lógicamente) para fines de auditoría.
- **Método `delete()` con Integridad `RESTRICT`**: Valida mediante introspección `_meta.related_objects` que no existan objetos relacionados activos configurados con `on_delete=models.RESTRICT`. Si los hay, eleva `models.deletion.RestrictedError`. Si no hay dependencias activas, marca `esta_eliminado=True` y actualiza `actualizado_en`.

### 2.2 Auditoría de Cambios Inmutable (`django-simple-history`)
Se integra la librería `django-simple-history` para mantener un historial completo e inmutable de modificaciones (versionado de registros) en los modelos críticos:
1. **`NotaBloque`** (`academico`): Audita cambios de zona y examen, identificando qué usuario modificó la nota y en qué fecha/hora.
2. **`Abono`** (`financiero`): Audita modificaciones a los registros de abonos, pagos parciales y números de boleta bancaria.
3. **`ArticuloInventario`** (`inventario`): Audita alteraciones en el stock actual de suministros y bienes institucionales.

### 2.3 Integridad Referencial Estricta (`on_delete=models.RESTRICT`)
Para prevenir eliminaciones descontroladas que corrompan la consistencia de los datos del colegio, se aplica `on_delete=models.RESTRICT` en **todas las llaves foráneas (`ForeignKey` y `OneToOneField`)** del sistema.

---

## 3. Patrón Supertipo / Subtipo (Herencia Persona)

El sistema centraliza los datos personales comunes de todos los individuos en la entidad **`Persona`**:

- **Modelo `Persona` (`APPS/core/models.py`)**:
  - `usuario` (`OneToOneField` a `Usuario`, opcional, `on_delete=models.RESTRICT`).
  - `cui` (`CharField`, Unique, 13 dígitos DPI o CUI RENAP).
  - `nombres`, `apellidos`, `fecha_nacimiento`, `genero` (`M`/`F`, opcional), `direccion`.
  - `telefono_principal`, `telefono_secundario`.
  - `correo` (email de contacto personal/familiar, único en el sistema).

- **Modelos Subtipo**:
  - **`Estudiante` (`APPS/estudiantes/models.py`)**: `persona = OneToOneField(Persona, primary_key=True, on_delete=models.RESTRICT)`, `codigo_mineduc`, `estado_estudiante` (`ACTIVO`, `RETIRADO`, `GRADUADO`, `SUSPENDIDO`), `encargado` (FK a `Encargado`), `nombre_padre`, `telefono_padre`, `nombre_madre`, `telefono_madre`, checklist de 5 documentos MINEDUC, `historial_medico`, `@property expediente_completo`.
  - **`Encargado` (`APPS/estudiantes/models.py`)**: `persona = OneToOneField(Persona, primary_key=True, on_delete=models.RESTRICT)`, `lugar_de_trabajo`.
  - **`Personal` (`APPS/rrhh/models.py`)**: `persona = OneToOneField(Persona, primary_key=True, on_delete=models.RESTRICT)`, `puesto` (FK a `Puesto`), `nit`, `fecha_contratacion`, `estado_laboral`, `salario_base_asignado`.

---

## 4. Estrategia de Autenticación, Usuarios y Login Multicriterio

### 4.1 Modelo de Usuario Personalizado (`Usuario`)
El modelo `Usuario` (`APPS/usuarios/models.py`) hereda de `AbstractUser` e incluye el campo:

```python
class RolChoices(models.TextChoices):
    ADMINISTRADOR = 'ADMINISTRADOR', 'Administrador'
    DIRECTOR      = 'DIRECTOR',      'Director'
    SECRETARIA    = 'SECRETARIA',    'Secretaría'
    CONTADOR      = 'CONTADOR',      'Contador'
    DOCENTE       = 'DOCENTE',       'Docente'
    ESTUDIANTE    = 'ESTUDIANTE',    'Estudiante'
    ENCARGADO     = 'ENCARGADO',     'Encargado'
```

- **Identificador de Usuario Universal:** En Estudiantes y Encargados, `username = CUI` (13 dígitos de RENAP).
- **Control de Primer Ingreso:** La propiedad `debe_cambiar_password = True` (default `True`) es interceptada por `EnforcePasswordChangeMiddleware` exigiendo cambio de clave obligatorio al autenticarse por primera vez.

### 4.2 Login Multicriterio (`CUIOrEmailModelBackend`)
El backend personalizado de autenticación (`APPS/usuarios/backends.py`) permite a cualquier usuario iniciar sesión indistintamente con:
1. Su **CUI / DPI de 13 dígitos** (username).
2. Su **Correo Electrónico**.

---

## 5. Estructura del Proyecto y Aplicaciones

```
IBACOOP_PROGRESO/
├── APPS/
│   ├── core/           # Módulo base: ModeloAuditable, Persona, PersonaForm, ActivosManager, TailwindFormMixin, Dashboard, admin
│   ├── usuarios/       # Usuario personalizado, backends.py (Login Multicriterio), EnforcePasswordChangeMiddleware, CBVs Usuarios
│   ├── estudiantes/    # Subtipos Estudiante, Encargado, EstudianteForm, EncargadoForm, reports.py (ReportLab PDF), CBVs transaccionales
│   ├── rrhh/           # Subtipo Personal, Puesto, PersonalForm, AsistenciaPersonal, Planilla, CBV PersonalCreateView
│   ├── academico/      # CicloEscolar, BloqueAcademico, Grado, Seccion, Curso, Asignaciones, NotaBloque (History), NotaFinalCurso, AsistenciaEstudiantil
│   ├── financiero/     # Sistema de Cuenta Corriente: ConceptoPago, CuentaPorCobrar, Abono (History)
│   ├── inventario/     # ArticuloInventario (History), MovimientoInventario
│   └── portal/         # ContenidoWeb (Portal institucional público)
├── IBACOOP_PROGRESO/   # Configuración global de Django (settings.py, urls.py, wsgi.py)
├── templates/          # Plantillas HTML globales del sistema (Tailwind v4 + DaisyUI)
│   ├── base.html       # Layout maestro con navegación lateral y barra superior
│   ├── estudiantes/    # estudiante_form.html, encargado_form.html, estudiante_list.html, estudiante_detail.html
│   └── usuarios/       # login.html, usuario_list.html, usuario_form.html
├── PENDIENTES.md       # Hoja de ruta de funcionalidades futuras (Módulo Académico)
├── LOGICA_DEL_NEGOCIO_Y_BASE_DE_DATOS.md # Documento de BD y Reglas de Negocio
└── CONTEXTO_PROYECTO.md # Documento de contexto del sistema
```

---

## 6. Diccionario de Datos y Modelos Refactorizados

- **`ModeloAuditable` (Abstract Base Model)**: `creado_en`, `actualizado_en`, `esta_eliminado`. Managers: `objects` (ActivosManager) y `todos`.
- **`Persona`**: `usuario` (O2O a Usuario opcional), `cui` (UK 13 dgs), `nombres`, `apellidos`, `fecha_nacimiento`, `genero`, `direccion`, `telefono_principal`, `telefono_secundario`, `correo` (UK).

### 6.2 App `estudiantes` (`APPS/estudiantes/models.py`)
- **`Estudiante`**: `persona` (O2O Persona, PK), `codigo_mineduc` (UK), `estado_estudiante` (`ACTIVO`, `RETIRADO`, `GRADUADO`, `SUSPENDIDO`), `encargado` (FK Encargado), `nombre_padre`, `telefono_padre`, `nombre_madre`, `telefono_madre`, `historial_medico`, `doc_cert_nacimiento_renap`, `doc_dpi_encargado`, `doc_certificado_grado_anterior`, `doc_diploma_primaria`, `doc_codigo_mineduc`, `@property expediente_completo`, `@property documentos_entregados_count`.
- **`Encargado`**: `persona` (O2O Persona, PK), `lugar_de_trabajo`.

---

## 7. Subsistemas Específicos

### 7.1 Módulo "Registro de Alumnos" (Expediente Digital 360°)
- **Papelería Obligatoria MINEDUC:** Verificación de 5 documentos requeridos para Ciclo Básico Nivel Medio.
- **Generador de Reportes PDF (`APPS/estudiantes/reports.py`):**
  1. `generar_pdf_expediente_estudiante`: Ficha única para el expediente físico en Secretaría.
  2. `generar_pdf_credenciales_acceso`: Comprobante de credenciales de acceso para Estudiante y Tutor Legal con claves temporales.

---

## 8. Vistas Basadas en Clases (CBV), Formularios, Validaciones y PDF

### 8.1 Validaciones de Negocio en Formularios (`PersonaForm` y `EstudianteForm`)
- **CUI / DPI:** Exige exactamente 13 dígitos numéricos + comprobación de unicidad.
- **Correo:** `clean_correo()` valida que el email no esté registrado previamente para otra persona.
- **Rango de Edad Alumno:** $10 \le \text{Edad} < 18$ años (Ciclo Básico diurno regular).
- **Teléfono Guatemala:** Exige exactamente 8 dígitos numéricos.
- **Encargado Obligatorio:** Todo alumno debe tener asignado un Tutor Legal principal.

---

## 9. Arquitectura Docker y Comandos de Administración

```powershell
# Iniciar y orquestar el sistema completo en Docker
docker compose up -d --build

# Reiniciar servicios de aplicación web
docker compose restart web

# Ejecutar comandos de verificación de Django dentro del contenedor
docker compose exec web python manage.py check
```
