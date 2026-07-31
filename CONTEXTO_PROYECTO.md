# Contexto Técnico y Arquitectura del Proyecto
## Sistema de Gestión Escolar — Instituto "El Progreso" (ERP Educativo)

> **Centro Educativo:** Instituto de Educación Básica "El Progreso" (Guatemala)  
> **Nivel Educativo:** Nivel de Educación Media — Ciclo de Educación Básica (1ro, 2do y 3ro Básico)  
> **Stack Tecnológico:** Python 3.12, Django 6.0.7, PostgreSQL, Django Templates, Tailwind CSS v4, DaisyUI, `django-simple-history`  
> **Paleta Institucional:** Rojo Institucional (`#7A1C21`), Verde Oscuro (`#1E6532`), Azul Océano (`#3C7DA8`), Azul Cielo (`#5D9CEC`), Verde Claro (`#42A855`).

---

## 📋 Índice

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Principios de Arquitectura y Reglas de Negocio](#2-principios-de-arquitectura-y-reglas-de-negocio)
3. [Estrategia de Autenticación y Autorización](#3-estrategia-de-autenticación-y-autorización)
4. [Estructura del Proyecto y Aplicaciones](#4-estructura-del-proyecto-y-aplicaciones)
5. [Diccionario de Datos y Modelos](#5-diccionario-de-datos-y-modelos)
6. [Configuración General (`settings.py`) y Sistema de Estilos](#6-configuración-general-settingspy-y-sistema-de-estilos)
7. [Vistas y Seguridad en Backend (CBV)](#7-vistas-y-seguridad-en-backend-cbv)
8. [Comandos de Administración y Ejecución](#8-comandos-de-administración-y-ejecución)
9. [Estado Actual del Desarrollo y Hitos Implementados](#9-estado-actual-del-desarrollo-y-hitos-implementados)

---

## 1. Resumen Ejecutivo

El **Sistema de Gestión Escolar del Instituto "El Progreso"** es una plataforma ERP integral desarrollada para automatizar la gestión académica, administrativa, financiera, de recursos humanos, control de inventarios y presencia web institucional de un centro de Educación Básica en Guatemala.

El sistema está diseñado siguiendo las normativas del **Ministerio de Educación de Guatemala (MINEDUC)** para el Nivel Básico, garantizando la trazabilidad total de notas, cobros e inventarios mediante auditoría de cambios y borrado lógico (*Soft Delete*).

---

## 2. Principios de Arquitectura y Reglas de Negocio

### 2.1 Eliminación Lógica (Soft Delete) e Integridad Referencial
**Regla:** Ningún registro de la base de datos se elimina físicamente.

- **`ModeloAuditable` (`APPS/core/models.py`)**: Modelo abstracto base del que heredan todos los modelos del sistema (excepto `Usuario` que extiende `AbstractUser`).
- **`ActivosManager`**: Manager por defecto (`objects`) que aplica automáticamente el filtro `esta_eliminado=False` a todos los QuerySets.
- **Manager `todos`**: Manager secundario (`todos`) que permite consultar la totalidad de registros (activos y eliminados lógicamente) para fines de auditoría.
- **Método `delete(usuario=None)`**: Valida mediante introspección `_meta.related_objects` que no existan objetos relacionados activos con `on_delete=models.RESTRICT`. Si los hay, eleva `RestrictedError`. Si no hay dependencias activas, marca `esta_eliminado=True`, registra `eliminado_en = timezone.now()` y actualiza `usuario_modificacion`.
- **Método `restaurar(usuario=None)`**: Revierte el estado de eliminación lógica del registro.

### 2.2 Auditoría de Cambios (`django-simple-history`)
Se integra la librería `django-simple-history` para mantener un historial completo e inmutable de modificaciones (versionado de registros) en los modelos críticos:
1. **`NotaBloque`** (`academico`): Audita cambios de zona y examen, identificando qué usuario modificó la nota y en qué fecha/hora.
2. **`PagoColegiatura`** (`financiero`): Audita modificaciones a los registros de pagos, abonos y números de boleta.
3. **`ArticuloInventario`** (`inventario`): Audita alteraciones en el stock actual de suministros y bienes institucionales.

### 2.3 Integridad Referencial Estricta en Soft Delete (`on_delete=models.RESTRICT`)
Para prevenir eliminaciones descontroladas que corrompan la consistencia de los datos del colegio, se aplica `on_delete=models.RESTRICT` en todas las llaves foráneas clave. En borrados lógicos, `ModeloAuditable.delete()` intercepta la llamada y eleva `RestrictedError` si existen hijos no eliminados.
- *Ejemplo:* No se puede desactivar o borrar un `Grado` si posee `Secciones` o `Cursos` activos asociados; ni eliminar un `Personal` si tiene `AsignacionesDocentes` o registros de `Planilla`.

### 2.4 Sistema Educativo Guatemalteco (Nivel Básico)
- **Estructura Académica:** Solo existen **Grados** (1ro, 2do y 3ro Básico) y **Secciones** (A, B, C, etc.). **NO existen carreras** (las carreras pertenecen al Nivel Diversificado).
- **Evaluación MINEDUC:**
  - **Nota de Zona:** Máximo **60 puntos** (actividades, tareas, ejercicios, parciales).
  - **Nota de Examen:** Máximo **40 puntos** (evaluación sumativa de fin de bloque).
  - **Nota Total:** `nota_zona + nota_examen` (máximo **100 puntos**).
  - **Aprobación:** Requiere un mínimo de **60 puntos**.
- **Bloques Académicos:** Evaluaciones divididas en bimestres o trimestres supeditadas a un **Ciclo Escolar** (año lectivo).

---

## 3. Estrategia de Autenticación y Autorización

### 3.1 Modelo de Usuario Personalizado (`Usuario`)
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

### 3.2 Separación Estricta entre UI y Seguridad Backend
> [!IMPORTANT]
> - **Campo `rol`:** Se utiliza **únicamente para la lógica visual en los templates** (ej. personalizar menú lateral, mostrar tarjetas contextuales o badges en la interfaz).
> - **Seguridad del Backend:** Se gestiona **exclusivamente mediante los `Groups` y `Permissions` nativos de Django**. Las vistas validan permisos mediante `PermissionRequiredMixin` (ej. `permission_required = 'usuarios.view_usuario'`, `permission_required = 'academico.change_notabloque'`).

---

## 4. Estructura del Proyecto y Aplicaciones

```
IBACOOP_PROGRESO/
├── APPS/
│   ├── core/           # Módulo base: ModeloAuditable, ActivosManager, HomeView (Dashboard), urls, views
│   ├── usuarios/       # Usuario personalizado, CustomUserForms, TailwindFormMixin, CBVs (List, Create, Update) y URLs de Login/Logout
│   ├── estudiantes/    # Estudiantes, Encargados y relaciones de parentesco
│   ├── rrhh/           # Personal, Puestos, Asistencia de Empleados y Planilla
│   ├── academico/      # Ciclos, Grados, Secciones, Cursos, Notas (History), Asistencia
│   ├── financiero/     # MensualidadCobro, PagoColegiatura (History)
│   ├── inventario/     # ArticuloInventario (History), MovimientoInventario
│   └── portal/         # ContenidoWeb (Portal institucional público)
├── IBACOOP_PROGRESO/   # Configuración global del proyecto
│   ├── settings.py     # Ajustes de Django, PostgreSQL, simple_history, URLs de auth
│   ├── urls.py         # URLconf principal con ruteo de apps (core, usuarios, etc.)
│   ├── wsgi.py
│   └── asgi.py
├── templates/          # Plantillas HTML globales del sistema
│   ├── base.html       # Layout principal (Navbar, Sidebar dinámico, Alertas Django)
│   ├── core/           # Vista Dashboard (home.html con KPIs y accesos rápidos)
│   └── usuarios/       # Templates de Usuarios (login.html, usuario_list.html, usuario_form.html)
├── theme/              # App de Tailwind CSS v4 (django-tailwind) + DaisyUI
│   └── static_src/src/styles.css # Definición de la paleta de colores institucional (@theme)
├── CONTEXTO_PROYECTO.md # Documento de contexto del sistema
├── manage.py
└── venv/               # Entorno virtual Python
```

---

## 5. Diccionario de Datos y Modelos

### 5.1 App `core` (`APPS/core/models.py`)
- **`ModeloAuditable` (Abstract Base Model)**
  - `creado_en` (`DateTimeField`): Fecha y hora de creación automática (`auto_now_add=True`).
  - `actualizado_en` (`DateTimeField`): Fecha y hora de última modificación (`auto_now=True`).
  - `eliminado_en` (`DateTimeField`, `null=True`): Timestamp de eliminación lógica.
  - `esta_eliminado` (`BooleanField`, `default=False`): Bandera de soft delete.
  - `usuario_creacion` (`FK(Usuario, SET_NULL)`): Usuario creador.
  - `usuario_modificacion` (`FK(Usuario, SET_NULL)`): Último usuario modificador.

### 5.2 App `usuarios` (`APPS/usuarios/models.py`)
- **`Usuario` (`AbstractUser`)**
  - Inherita todos los campos nativos de Django (`username`, `password`, `email`, `first_name`, `last_name`, `is_staff`, `is_superuser`, `groups`, `user_permissions`).
  - `rol` (`CharField`, `choices=RolChoices`): Administrador, Director, Contador, Docente, Estudiante, Encargado.

### 5.3 App `estudiantes` (`APPS/estudiantes/models.py`)
- **`Estudiante` (`ModeloAuditable`)**
  - `usuario` (`OneToOneField(Usuario, RESTRICT)`): Cuenta de acceso.
  - `codigo_mineduc` (`CharField`, `unique=True`): Código oficial del MINEDUC.
  - `nombres`, `apellidos`, `fecha_nacimiento`, `genero`, `direccion`.
  - `estado_activo` (`BooleanField`, `default=True`).
- **`Encargado` (`ModeloAuditable`)**
  - `usuario` (`OneToOneField(Usuario, RESTRICT, null=True)`): Cuenta opcional.
  - `nombres`, `apellidos`, `dpi` (`unique=True`), `telefono_contacto`, `telefono_secundario`, `correo`, `ocupacion`.
- **`EstudianteEncargado` (`ModeloAuditable`)**
  - `estudiante` (`FK(Estudiante, RESTRICT)`), `encargado` (`FK(Encargado, RESTRICT)`).
  - `parentesco` (`CharField`): Padre, Madre, Abuelo/a, Tío/a, Hermano/a, Tutor, Otro.
  - `es_contacto_principal` (`BooleanField`).

### 5.4 App `rrhh` (`APPS/rrhh/models.py`)
- **`Puesto` (`ModeloAuditable`)**: `nombre_puesto` (`unique=True`), `descripcion`.
- **`Personal` (`ModeloAuditable`)**:
  - `usuario` (`OneToOneField(Usuario, RESTRICT)`), `puesto` (`FK(Puesto, RESTRICT)`).
  - `nombres`, `apellidos`, `dpi` (`unique=True`), `nit`, `fecha_contratacion`, `estado_laboral`, `salario_base_asignado`.
- **`AsistenciaPersonal` (`ModeloAuditable`)**: `personal` (`FK(Personal, RESTRICT)`), `fecha`, `hora_entrada`, `hora_salida`, `estado_asistencia`.
- **`Planilla` (`ModeloAuditable`)**: `personal` (`FK(Personal, RESTRICT)`), `mes_pagado`, `ciclo_escolar` (`FK(CicloEscolar, RESTRICT)`), `bonificaciones`, `descuentos`, `total_pagar`, `comprobante_pdf`, `pagado`.

### 5.5 App `academico` (`APPS/academico/models.py`)
- **`CicloEscolar` (`ModeloAuditable`)**: `anio` (`unique=True`), `estado_activo` (`BooleanField`).
- **`BloqueAcademico` (`ModeloAuditable`)**: `ciclo_escolar` (`FK(CicloEscolar, RESTRICT)`), `nombre_bloque`, `orden`.
- **`Grado` (`ModeloAuditable`)**: `nombre` (`unique=True`, ej. "Primero Básico"), `orden`.
- **`Seccion` (`ModeloAuditable`)**: `grado` (`FK(Grado, RESTRICT)`), `letra`, `cupo_maximo`.
- **`Curso` (`ModeloAuditable`)**: `grado` (`FK(Grado, RESTRICT)`), `nombre_curso`, `codigo_curso` (`unique=True`).
- **`AsignacionEstudiante` (`ModeloAuditable`)**: Inscripción de estudiante en una Sección y Ciclo Escolar.
- **`AsignacionDocente` (`ModeloAuditable`)**: Cátedra asignada a un docente (Personal + Curso + Seccion + CicloEscolar).
- **`NotaBloque` (`ModeloAuditable` + `HistoricalRecords`)**:
  - `asignacion_estudiante` (`FK(AsignacionEstudiante, RESTRICT)`).
  - `curso` (`FK(Curso, RESTRICT)`), `bloque_academico` (`FK(BloqueAcademico, RESTRICT)`).
  - `nota_zona` (`DecimalField`, 0 a 60 pts).
  - `nota_examen` (`DecimalField`, 0 a 40 pts).
  - `@property nota_total`: Retorna `nota_zona + nota_examen`.
  - `history = HistoricalRecords()`: Registra cada cambio con trazabilidad de usuario y timestamp.
- **`NotaFinalCurso` (`ModeloAuditable`)**:
  - `asignacion_estudiante` (`FK(AsignacionEstudiante, RESTRICT)`), `curso` (`FK(Curso, RESTRICT)`).
  - `nota_promedio` (`DecimalField`): Promedio acumulado de bloques evaluados.
  - `esta_promocionado` (`BooleanField`): Dictamina la promoción si `nota_promedio >= 60`.
- **`AsistenciaEstudiantil` (`ModeloAuditable`)**: `asignacion_estudiante`, `curso`, `fecha`, `presente`, `justificado`.

### 5.6 App `financiero` (`APPS/financiero/models.py`)
- **`MensualidadCobro` (`ModeloAuditable`)**: `estudiante` (`FK(Estudiante, RESTRICT)`), `ciclo_escolar` (`FK(CicloEscolar, RESTRICT)`), `mes_cobro`, `monto_esperado`, `estado_pagado`.
- **`PagoColegiatura` (`ModeloAuditable` + `HistoricalRecords`)**: `mensualidad` (`FK(MensualidadCobro, RESTRICT)`), `monto_pagado`, `fecha_pago`, `numero_boleta` (`unique=True`), `recibo_generado`, `recibo_pdf`.

### 5.7 App `inventario` (`APPS/inventario/models.py`)
- **`ArticuloInventario` (`ModeloAuditable` + `HistoricalRecords`)**: `codigo_unico` (`unique=True`), `nombre`, `categoria`, `stock_actual`, `stock_minimo_alerta`, `@property alerta_stock_bajo`.
- **`MovimientoInventario` (`ModeloAuditable`)**: `articulo` (`FK(ArticuloInventario, RESTRICT)`), `personal_responsable` (`FK(Personal, RESTRICT)`), `tipo_movimiento` (Entrada, Salida, Asignación, etc.), `cantidad`, `fecha`, `motivo`.

### 5.8 App `portal` (`APPS/portal/models.py`)
- **`ContenidoWeb` (`ModeloAuditable`)**: `seccion` (Noticias, Historia, Galería, Oferta, etc.), `titulo`, `cuerpo`, `imagen_url`, `imagen_archivo`, `fecha_publicacion`, `publicado`, `autor` (`FK(Usuario, SET_NULL)`).

---

## 6. Configuración General (`settings.py`) y Sistema de Estilos

### 6.1 Ajustes de Django
- **Modelo de Usuario Custom:** `AUTH_USER_MODEL = 'usuarios.Usuario'`
- **Base de Datos:** PostgreSQL local (`ENGINE: django.db.backends.postgresql`, `NAME: IBACOOP_PROGRESO`).
- **Aplicaciones:** Todas las 8 apps del ERP registradas junto a `tailwind`, `theme` y `simple_history`.
- **Middleware:** `simple_history.middleware.HistoryRequestMiddleware` incluido.
- **Idioma y Zona Horaria:** `LANGUAGE_CODE = 'es-gt'`, `TIME_ZONE = 'America/Guatemala'`.
- **Redirección de Autenticación:**
  ```python
  LOGIN_URL = 'usuarios:login'
  LOGIN_REDIRECT_URL = 'core:home'
  LOGOUT_REDIRECT_URL = 'usuarios:login'
  ```

### 6.2 Paleta de Colores y Tailwind CSS v4
Ubicación del archivo de estilos: `theme/static_src/src/styles.css`

```css
@import "tailwindcss";
@plugin "daisyui";

@theme {
  --color-brand-red: #7A1C21;
  --color-brand-darkgreen: #1E6532;
  --color-brand-ocean: #3C7DA8;
  --color-brand-sky: #5D9CEC;
  --color-brand-lightgreen: #42A855;
  --color-brand-bg: #FFFFFF;
}

@source "../../../**/*.{html,py,js}";
```

---

## 7. Vistas y Seguridad en Backend (CBV)

### 7.1 Dashboard Principal (`HomeView`)
Ubicación: [views.py](file:///c:/Users/Nelson/Desktop/Proyectos/IBACOOP_PROGRESO/APPS/core/views.py#L11)
- Protected con `LoginRequiredMixin`.
- Calcula KPIs en tiempo real (`total_usuarios`, `usuarios_activos`, conteo por rol `ADMINISTRADOR`, `DOCENTE`, `ESTUDIANTE`).

### 7.2 Gestión de Usuarios (CRUD)
Ubicación: [views.py](file:///c:/Users/Nelson/Desktop/Proyectos/IBACOOP_PROGRESO/APPS/usuarios/views.py#L18)
- **`UsuarioListView`**: Muestra la lista paginada (10 por página) con `prefetch_related('groups')` para prevenir consultas N+1. Valida el permiso `usuarios.view_usuario` con `raise_exception = True` (HTTP 403).
- **`UsuarioCreateView`**: Permite registrar nuevos usuarios asociando datos personales, rol visual e integración de grupos de permisos. Valida `usuarios.add_usuario`.
- **`UsuarioUpdateView`**: Permite modificar información de usuarios existentes. Valida `usuarios.change_usuario`.

### 7.3 Mixin de Formularios Tailwind (`TailwindFormMixin`)
Ubicación: [forms.py](file:///c:/Users/Nelson/Desktop/Proyectos/IBACOOP_PROGRESO/APPS/usuarios/forms.py#L12)
Formularios como `CustomUserCreationForm` y `CustomUserChangeForm` heredan de `TailwindFormMixin` para inyectar automáticamente bordes, rings de enfoque y colores corporativos (`#1E6532`) en los widgets HTML (`TextInput`, `Select`, `CheckboxInput`, etc.).

### 7.4 Ejemplo de Seguridad Backend: `IngresoNotasUpdateView`
Ubicación: [views.py](file:///c:/Users/Nelson/Desktop/Proyectos/IBACOOP_PROGRESO/APPS/academico/views.py#L25)

```python
class IngresoNotasUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Permite al docente ingresar/modificar las notas de sus estudiantes.
    Aplica 3 capas de seguridad:
      1. LoginRequiredMixin: Exige sesión activa.
      2. PermissionRequiredMixin: Exige el permiso 'academico.change_notabloque'.
      3. get_queryset(): Filtra el QuerySet únicamente a las notas de cursos
         y secciones que el docente imparte en el ciclo escolar activo.
    """
    model = NotaBloque
    form_class = NotaBloqueForm
    template_name = 'academico/ingreso_notas.html'
    permission_required = 'academico.change_notabloque'
    raise_exception = True  # Retorna HTTP 403 en lugar de redirigir

    def get_queryset(self):
        usuario = self.request.user
        try:
            ciclo_activo = CicloEscolar.objects.get(estado_activo=True)
        except (CicloEscolar.DoesNotExist, CicloEscolar.MultipleObjectsReturned):
            return NotaBloque.objects.none()

        asignaciones_docente = AsignacionDocente.objects.filter(
            personal__usuario=usuario,
            ciclo_escolar=ciclo_activo,
        )

        curso_ids = list(asignaciones_docente.values_list('curso_id', flat=True))
        seccion_ids = list(asignaciones_docente.values_list('seccion_id', flat=True))

        return NotaBloque.objects.filter(
            curso_id__in=curso_ids,
            asignacion_estudiante__ciclo_escolar=ciclo_activo,
            asignacion_estudiante__seccion_id__in=seccion_ids,
        )

    def form_valid(self, form):
        nota = form.save(commit=False)
        nota.usuario_modificacion = self.request.user
        nota.save()
        return super().form_valid(form)
```

---

## 8. Comandos de Administración y Ejecución

### 8.1 Levantar el Entorno Virtual
```powershell
.\venv\Scripts\activate
```

### 8.2 Migraciones de Base de Datos
```powershell
python manage.py makemigrations
python manage.py migrate
```

### 8.3 Compilar/Monitorear Tailwind CSS
```powershell
python manage.py tailwind start
```

### 8.4 Iniciar Servidor de Desarrollo
```powershell
python manage.py runserver
```

---

## 9. Estado Actual del Desarrollo y Hitos Implementados

### 🟢 Hitos Completados
- [x] **Arquitectura Base & Soft Delete**: Implementación del modelo abstracto `ModeloAuditable` y manager `ActivosManager` en `APPS/core`.
- [x] **Modelos de Datos Integrales**: Definición completa de entidades para las 8 aplicaciones (`core`, `usuarios`, `estudiantes`, `rrhh`, `academico`, `financiero`, `inventario`, `portal`).
- [x] **Auditoría e Historial**: Configuración de `django-simple-history` en `NotaBloque`, `PagoColegiatura` y `ArticuloInventario`.
- [x] **Diseño Visual & UI**: Integración de Tailwind CSS v4, DaisyUI y personalización con la paleta de colores institucional.
- [x] **Plantilla Base Reutilizable (`base.html`)**: Navbar con información del usuario, Sidebar dinámico con accesos por rol y contenedor de mensajes de feedback.
- [x] **Dashboard Principal (`HomeView`)**: Tarjetas de métricas (KPIs) en tiempo real para administración y accesos a módulos.
- [x] **Módulo de Autenticación Nactiva**: Vistas y plantillas de inicio y cierre de sesión (`LoginView`, `LogoutView`, `login.html`).
- [x] **Módulo de Gestión de Usuarios (CRUD)**:
  - `UsuarioListView` con paginación, filtros de permisos y optimización N+1 (`prefetch_related`).
  - `UsuarioCreateView` y `UsuarioUpdateView` asociadas a `CustomUserCreationForm` y `CustomUserChangeForm`.
  - Mixin `TailwindFormMixin` para estilar automáticamente los inputs y selects.

### 🟡 Hitos Pendientes / Próximos Pasos
- [ ] **Módulo Académico**: Vistas y plantillas para inscripción de estudiantes, asignación docente y registro de notas/asistencia.
- [ ] **Módulo Estudiantes & Encargados**: Vistas CRUD de expediente estudiantil y asignación de parentescos.
- [ ] **Módulo RRHH**: Control de asistencia del personal y gestión de planillas.
- [ ] **Módulo Financiero**: Generación de estado de cuenta de mensualidades y registro de pagos con emisión de recibos.
- [ ] **Módulo Inventario**: Registro de artículos, alertas de stock bajo y control de movimientos.
- [ ] **Módulo Portal Público**: Gestión de publicaciones web e historia institucional.

---
*Documento actualizado para el proyecto ERP Escolar Instituto "El Progreso".*
