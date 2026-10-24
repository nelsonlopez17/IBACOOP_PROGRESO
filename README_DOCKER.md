# Guía de Despliegue con Docker — IBACOOP El Progreso

Esta guía detalla los pasos para levantar y ejecutar el proyecto ERP Escolar IBACOOP El Progreso en cualquier máquina utilizando **Docker** y **Docker Compose**.

---

## 1. Prerrequisitos

* Tener instalado **Docker Desktop** (en Windows/macOS) o el motor de **Docker** y **Docker Compose** (en Linux).
* Verificar que el servicio de Docker esté iniciado ejecutando en su terminal:
  ```bash
  docker --version
  docker compose version
  ```

---

## 2. Servicios Incluidos en el Contenedor

El archivo `docker-compose.yml` orquesta los servicios interconectados en una red interna aislada:

1. **`db`** (PostgreSQL 16 Alpine): Base de datos relacional (puerto externo `5433`, interno `5432`).
2. **`web`** (Django 5 + Python 3.12 + Gunicorn): Servidor web principal (puerto `8000`), con procesamiento nativo de tareas en segundo plano.

---

## 3. Puesta en Marcha (Paso a Paso)

### Paso 1: Configurar variables de entorno (Opcional)
El proyecto incluye un archivo `.env.example`. Puede crear su propio archivo `.env` o utilizar los valores por defecto ya configurados en `docker-compose.yml`:
```bash
cp .env.example .env
```

### Paso 2: Construir las imágenes y levantar los contenedores
Ejecute en la raíz del proyecto:
```bash
docker compose up -d --build
```
> El script `entrypoint.sh` esperará automáticamente a que PostgreSQL esté listo, aplicará todas las migraciones (`migrate`) y compilará los archivos estáticos (`collectstatic`).

### Paso 3: Poblar datos de prueba del instituto (Recomendado)
Para cargar datos de prueba completos de Guatemala (estudiantes, encargados, docentes, ciclos, calificaciones, cuotas y planillas):
```bash
docker compose exec web python manage.py poblar_datos_prueba
```

## 4. Credenciales de Prueba Preconfiguradas

El sistema genera y configura automáticamente un superusuario administrador para pruebas al levantar los contenedores:

* **Usuario**: `admin`
* **Contraseña**: `admin`
* **Rol**: `ADMINISTRADOR` (Superusuario con privilegios globales)

---

## 5. Acceso a la Plataforma

* **Portal Institucional y ERP**: [http://localhost:8000](http://localhost:8000)
* **Inicio de Sesión ERP**: [http://localhost:8000/usuarios/login/](http://localhost:8000/usuarios/login/)
* **Panel de Administración**: [http://localhost:8000/admin/](http://localhost:8000/admin/)

---

## 6. Comandos Útiles de Mantenimiento

* **Ver los registros (logs) en tiempo real**:
  ```bash
  docker compose logs -f
  ```
* **Ver logs únicamente de la aplicación web**:
  ```bash
  docker compose logs -f web
  ```
* **Acceder a la terminal dentro del contenedor web**:
  ```bash
  docker compose exec web bash
  ```
* **Ejecutar pruebas automatizadas**:
  ```bash
  docker compose exec web python manage.py test APPS
  ```
* **Detener los contenedores**:
  ```bash
  docker compose stop
  ```
* **Detener y remover los contenedores (conservando la base de datos)**:
  ```bash
  docker compose down
  ```
* **Reiniciar desde cero eliminando volúmenes de datos**:
  ```bash
  docker compose down -v
  ```
