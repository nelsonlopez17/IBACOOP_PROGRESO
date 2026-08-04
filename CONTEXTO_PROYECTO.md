# Contexto Técnico y Arquitectura del Proyecto
## Sistema de Gestión Escolar — Instituto "El Progreso" (ERP Educativo)

> **Centro Educativo:** Instituto de Educación Básica "El Progreso" (Guatemala)  
> **Nivel Educativo:** Nivel de Educación Media — Ciclo de Educación Básica (1ro, 2do y 3ro Básico)  
> **Stack Tecnológico:** Python 3.12, Django 6.0, PostgreSQL 16, Gunicorn 23.0, WhiteNoise 6.9, Django Templates, Tailwind CSS v4, DaisyUI, HTMX 1.9, `django-simple-history`  
> **Paleta Institucional:** Rojo Institucional (`#7A1C21`), Verde Oscuro (`#1E6532`), Azul Océano (`#3C7DA8`), Azul Cielo (`#5D9CEC`), Verde Claro (`#42A855`).  
> **Despliegue y Orquestación:** Docker, Docker Compose (`ibacoop_web` + `ibacoop_db`).

---

## 📋 Índice

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Principios de Arquitectura y Reglas de Negocio](#2-principios-de-arquitectura-y-reglas-de-negocio)
3. [Patrón Supertipo / Subtipo (Herencia Persona)](#3-patrón-supertipo--subtipo-herencia-persona)
4. [Estrategia de Autenticación y Autorización](#4-estrategia-de-autenticación-y-autorización)
5. [Estructura del Proyecto y Aplicaciones](#5-estructura-del-proyecto-y-aplicaciones)
6. [Diccionario de Datos y Modelos Refactorizados](#6-diccionario-de-datos-y-modelos-refactorizados)
7. [Subsistemas Específicos (Académico, Financiero, Inventarios)](#7-subsistemas-específicos-académico-financiero-inventarios)
8. [Vistas Basadas en Clases (CBV), Formularios y Transacciones Atómicas](#8-vistas-basadas-en-clases-cbv-formularios-y-transacciones-atómicas)
9. [Diseño Visual, Plantillas HTML y Menú Principal](#9-diseño-visual-plantillas-html-y-menú-principal)
10. [Arquitectura Docker y Comandos de Administración](#10-arquitectura-docker-y-comandos-de-administración)

---

## 1. Resumen Ejecutivo

El **Sistema de Gestión Escolar del Instituto "El Progreso"** es una plataforma ERP integral desarrollada para automatizar la gestión académica, administrativa, financiera, de recursos humanos, control de inventarios y presencia web institucional de un centro de Educación Básica en Guatemala.

El sistema está diseñado siguiendo las normativas del **Ministerio de Educación de Guatemala (MINEDUC)** para el Nivel Básico, garantizando la trazabilidad total de notas, cobros e inventarios mediante auditoría de cambios (`django-simple-history`) y borrado lógico (*Soft Delete*).

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
  - `cui` (`CharField`, Unique, 13 dígitos DPI o CUI MINEDUC).
  - `nombres`, `apellidos`, `fecha_nacimiento`, `genero` (`M`/`F`, opcional), `direccion`.
  - `telefono_principal`, `telefono_secundario`.
  - `correo` (email comercial/contacto, independiente de las credenciales de acceso).

- **Modelos Subtipo**:
  - **`Estudiante` (`APPS/estudiantes/models.py`)**: `persona = OneToOneField(Persona, primary_key=True, on_delete=models.RESTRICT)`, `codigo_mineduc`, `historial_medico`, `estado_activo`.
  - **`Encargado` (`APPS/estudiantes/models.py`)**: `persona = OneToOneField(Persona, primary_key=True, on_delete=models.RESTRICT)`, `lugar_de_trabajo`.
  - **`Personal` (`APPS/rrhh/models.py`)**: `persona = OneToOneField(Persona, primary_key=True, on_delete=models.RESTRICT)`, `puesto` (FK a `Puesto`), `nit`, `fecha_contratacion`, `estado_laboral`, `salario_base_asignado`.

---

## 4. Estrategia de Autenticación y Autorización

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

### 4.2 Separación Estricta entre UI y Seguridad Backend
> [!IMPORTANT]
> - **Campo `rol`:** Se utiliza **únicamente para la lógica visual en los templates** (ej. personalizar menú lateral o tarjetas contextuales).
> - **Seguridad del Backend:** Se gestiona **exclusivamente mediante los `Groups` y `Permissions` nativos de Django**. Las vistas validan permisos mediante `PermissionRequiredMixin` (ej. `permission_required = 'estudiantes.add_estudiante'`).

---

## 5. Estructura del Proyecto y Aplicaciones

```
IBACOOP_PROGRESO/
├── APPS/
│   ├── core/           # Módulo base: ModeloAuditable, Persona, PersonaForm, ActivosManager, TailwindFormMixin, Dashboard, admin
│   ├── usuarios/       # Usuario personalizado, CustomUserForms, CBVs de Usuarios y Login/Logout
│   ├── estudiantes/    # Subtipos Estudiante, Encargado, EstudianteEncargado, EstudianteForm, EncargadoForm, CBVs transaccionales
│   ├── rrhh/           # Subtipo Personal, Puesto, PersonalForm, AsistenciaPersonal, Planilla, CBV PersonalCreateView
│   ├── academico/      # CicloEscolar, BloqueAcademico, Grado, Seccion, Curso, Asignaciones, NotaBloque (History), NotaFinalCurso (Recuperación), AsistenciaEstudiantil
│   ├── financiero/     # Sistema de Cuenta Corriente: ConceptoPago, CuentaPorCobrar, Abono (History)
│   ├── inventario/     # ArticuloInventario (History), MovimientoInventario
│   └── portal/         # ContenidoWeb (Portal institucional público)
├── IBACOOP_PROGRESO/   # Configuración global de Django (settings.py, urls.py, wsgi.py, asgi.py)
├── templates/          # Plantillas HTML globales del sistema
│   ├── base.html       # Layout maestro con navegación lateral y barra superior
│   ├── core/           # home.html (Dashboard activo)
│   ├── estudiantes/    # estudiante_form.html, encargado_form.html, estudiante_list.html
│   ├── rrhh/           # personal_form.html, personal_list.html
│   └── usuarios/       # login.html, usuario_list.html, usuario_form.html
├── theme/              # App de Tailwind CSS v4 + DaisyUI
├── LOGICA_DEL_NEGOCIO_Y_BASE_DE_DATOS.md # Documento detallado de BD y Lógica del Negocio
└── CONTEXTO_PROYECTO.md # Documento de contexto del sistema
```

---

## 6. Diccionario de Datos y Modelos Refactorizados

- **`ModeloAuditable` (Abstract Base Model)**: `creado_en`, `actualizado_en`, `esta_eliminado`. Managers: `objects` (ActivosManager) y `todos`.
- **`Persona`**: `usuario` (O2O a Usuario opcional), `cui` (UK 13 dgs), `nombres`, `apellidos`, `fecha_nacimiento`, `genero` (`M`/`F` opcional), `direccion`, `telefono_principal`, `telefono_secundario`, `correo`.

### 6.2 App `estudiantes` (`APPS/estudiantes/models.py`)
- **`Estudiante`**: `persona` (O2O Persona, PK), `codigo_mineduc` (UK), `historial_medico`, `estado_activo`.
- **`Encargado`**: `persona` (O2O Persona, PK), `lugar_de_trabajo`.
- **`EstudianteEncargado`**: `estudiante` (FK Estudiante), `encargado` (FK Encargado), `parentesco` (`ParentescoChoices`), `es_contacto_principal`. Restricción: `unique_together = [['estudiante', 'encargado']]`.

### 6.3 App `rrhh` (`APPS/rrhh/models.py`)
- **`Puesto`**: `nombre_puesto` (UK), `descripcion`.
- **`Personal`**: `persona` (O2O Persona, PK), `puesto` (FK Puesto), `nit`, `fecha_contratacion`, `estado_laboral` (`EstadoLaboralChoices`), `salario_base_asignado`.

### 7.1 Subsistema Académico y Recuperaciones (`APPS/academico/models.py`)
- **`CicloEscolar`**: `anio` (UK), `estado_activo` (único activo), `fecha_inicio`, `fecha_fin`.
- **`BloqueAcademico`**: `ciclo_escolar` (FK), `nombre_bloque`, `orden`.
- **`Grado`**: `nombre` (UK), `orden`.
- **`Seccion`**: `grado` (FK), `letra`, `cupo_maximo`.
- **`Curso`**: `grado` (FK), `nombre_curso`, `codigo_curso` (UK).
- **`AsignacionEstudiante`**: `estudiante` (FK), `seccion` (FK), `ciclo_escolar` (FK). Unicidad: `[estudiante, ciclo_escolar]`.
- **`AsignacionDocente`**: `personal` (FK), `curso` (FK), `seccion` (FK), `ciclo_escolar` (FK).
- **`NotaBloque` (`HistoricalRecords`)**: `asignacion_estudiante` (FK), `curso` (FK), `bloque_academico` (FK), `nota_zona` (0-60), `nota_examen` (0-40). `@property nota_total`.
- **`NotaFinalCurso`**: Promedio ordinario y recuperaciones:
  - `nota_promedio`: Promedio ordinario acumulado.
  - `aplica_recuperacion`: `True` si `nota_promedio < 60.00`.
  - `nota_recuperacion_1`, `nota_recuperacion_2`: Calificaciones de pruebas extraordinarias.
  - `nota_definitiva`: Máximo punteo alcanzado.
  - `esta_promocionado`: `True` si `nota_definitiva >= 60.00`.
  - Método `calcular_nota_final()`.

### 7.2 Subsistema Financiero — Cuenta Corriente (`APPS/financiero/models.py`)
- **`ConceptoPago`**: `nombre` (UK), `monto_estandar`.
- **`CuentaPorCobrar`**: `estudiante` (FK), `concepto` (FK), `ciclo_escolar` (FK), `monto_total`, `saldo_pendiente`, `fecha_limite_pago`, `estado_pago` (`EstadoPagoChoices`: `PENDIENTE`, `PARCIAL`, `PAGADO`). Método `actualizar_saldo()`.
- **`Abono` (`HistoricalRecords`)**: `cuenta_por_cobrar` (FK), `monto_pagado`, `fecha_pago`, `numero_boleta` (UK), `recibo_pdf`, `observaciones`.

### 7.3 Subsistema de Inventario (`APPS/inventario/models.py`)
- **`ArticuloInventario` (`HistoricalRecords`)**: `codigo_unico` (UK), `nombre`, `descripcion`, `categoria` (`CategoriaChoices`), `stock_actual`, `stock_minimo_alerta`, `unidad_medida`. `@property alerta_stock_bajo`.
- **`MovimientoInventario`**: `articulo` (FK), `personal_responsable` (FK), `tipo_movimiento` (`TipoMovimientoChoices`), `cantidad`, `fecha`, `motivo`, `documento_referencia`.

---

## 8. Vistas Basadas en Clases (CBV), Formularios y Transacciones Atómicas

### 8.1 Formularios con `TailwindFormMixin`
Todos los formularios del sistema heredan de `TailwindFormMixin` (`APPS/core/forms.py`), aplicando automáticamente los estilos corporativos de Tailwind CSS v4 a los controles de formulario:
- **`PersonaForm` (`APPS/core/forms.py`)**: Formulario para la información de `Persona` (CUI 13 dgs, nombres, apellidos, fecha de nacimiento, dirección, teléfonos, correo).
- **`EstudianteForm` (`APPS/estudiantes/forms.py`)**: Código MINEDUC, género, estado activo.
- **`EncargadoForm` (`APPS/estudiantes/forms.py`)**: Ocupación o profesión del tutor.
- **`PersonalForm` (`APPS/rrhh/forms.py`)**: Puesto, NIT, fecha de contratación, estado laboral y salario base.

### 8.2 Vistas Transaccionales (`transaction.atomic()`) y Creación Automatizada de Cuentas

1. **`EstudianteCreateView` (`APPS/estudiantes/views.py`)**:
   - Procesa `PersonaForm` y `EstudianteForm` en simultáneo.
   - En un bloque `with transaction.atomic()`:
     1. Autogenera la cuenta de `Usuario`: `username` = `codigo_mineduc`, contraseña temporal = `Estudiante.2026!`, `rol` = `RolChoices.ESTUDIANTE`.
     2. Guarda `Persona` vinculada a `Usuario`.
     3. Guarda `Estudiante` vinculado a `Persona`.
   - Requisito de seguridad: `PermissionRequiredMixin` (`estudiantes.add_estudiante`).

2. **`EncargadoCreateView` (`APPS/estudiantes/views.py`)**:
   - Procesa `PersonaForm` y `EncargadoForm` en simultáneo.
   - En un bloque `with transaction.atomic()`:
     1. Autogenera la cuenta de `Usuario`: `username` = `cui` (DPI), contraseña temporal = `Encargado.2026!`, `rol` = `RolChoices.ENCARGADO`.
     2. Guarda `Persona` vinculada a `Usuario`.
     3. Guarda `Encargado` vinculado a `Persona`.
   - Requisito de seguridad: `PermissionRequiredMixin` (`estudiantes.add_encargado`).

3. **`PersonalCreateView` (`APPS/rrhh/views.py`)**:
   - Procesa `PersonaForm` y `PersonalForm` en simultáneo.
   - En un bloque `with transaction.atomic()`:
     1. Genera inteligentemente el `username` del colaborador: 1ra letra del primer nombre + primer apellido (ej. `jgomez`). En caso de colisión, se concatenan los últimos 3 dígitos del DPI/CUI (`jgomez456`).
     2. Mapea dinámicamente el `rol` visual del `Usuario` según la palabra clave del `Puesto` seleccionado (ej. `DIRECTOR`, `SECRETARIA`, `CONTADOR`, `DOCENTE`).
     3. Guarda `Usuario`, `Persona` y `Personal`.
   - Requisito de seguridad: `PermissionRequiredMixin` (`rrhh.add_personal`).

---

## 9. Diseño Visual, Plantillas HTML y Menú Principal

### 9.1 Plantilla Maestra (`base.html`)
- Estructurada con barra lateral fija de navegación, encabezado institucional con logotipo, badges de rol del usuario conectado y botón de cierre de sesión.
- Utiliza **Lucide Icons**, fuente **Inter** y configuración de colores Tailwind CDN (`#7A1C21`, `#1E6532`, `#3C7DA8`, `#5D9CEC`, `#42A855`).
- Define un bloque único `{% block content %}` para la interfaz autenticada y `{% block auth_content %}` para pantallas públicas o login.

### 9.2 Módulos Activos en el Dashboard Principal (`home.html`)
- Muestra tarjetas dinámicas de resumen (KPIs): Total Usuarios, Administradores, Docentes, Estudiantes.
- Accesos directos a los módulos activos del sistema:
  - **Gestión de Usuarios** (`usuarios:usuario_list`)
  - **Estudiantes y Encargados** (`estudiantes:estudiante_list`)
  - **Recursos Humanos** (`rrhh:personal_list`)

---

## 10. Arquitectura Docker y Comandos de Administración

### 10.1 Orquestación con Docker Compose

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: ibacoop_db
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d ibacoop_db"]

  web:
    build: .
    container_name: ibacoop_web
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - DB_PORT=5432
    volumes:
      - .:/app
    depends_on:
      db:
        condition: service_healthy
```

### 10.2 Comandos Principales de Administración

```powershell
# Iniciar y orquestar el sistema completo en Docker
docker compose up -d --build

# Reiniciar servicios de aplicación web
docker compose restart web

# Revisar logs del contenedor web en tiempo real
docker compose logs web --tail 50 -f

# Ejecutar comandos de verificación de Django dentro del contenedor
docker compose exec web python manage.py check
```
