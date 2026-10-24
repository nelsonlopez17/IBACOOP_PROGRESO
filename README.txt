================================================================================
GUIA SIMPLE DE INSTALACION CON DOCKER - IBACOOP EL PROGRESO
================================================================================

1. REQUISITOS PREVIOS:
   - Tener instalado Docker Desktop (Windows / macOS) o Docker Engine (Linux).
   - Asegurarse de que Docker se encuentre en ejecucion.

2. PASOS PARA INSTALAR Y LEVANTAR EL PROYECTO:

   Paso 1: Descomprimir el archivo ZIP en una carpeta.
   
   Paso 2: Abrir una terminal en dicha carpeta (donde esta docker-compose.yml).
   
   Paso 3: Ejecutar el siguiente comando para construir y levantar los contenedores:
   
           docker compose up -d --build

           (El contenedor esperara a que PostgreSQL este listo, aplicara las
           migraciones de base de datos y dejara listo el sistema de forma
           totalmente automatica).

   Paso 4 (Opcional pero recomendado):
           Para poblar la base de datos con informacion y registros de prueba
           (estudiantes, encargados, docentes, cursos, notas, cuotas y planillas):
           
           docker compose exec web python manage.py poblar_datos_prueba

3. CREDENCIALES DEL USUARIO ADMINISTRADOR (SUPERUSER):
   
   - Usuario:    admin
   - Contrasena: admin
   - Rol:        ADMINISTRADOR (Superusuario con acceso total al ERP y a /admin/)

4. ENLACES DE ACCESO EN EL NAVEGADOR WEB:

   - Plataforma ERP / Portal Web: http://localhost:8000
   - Inicio de Sesion:            http://localhost:8000/usuarios/login/
   - Panel de Administracion:     http://localhost:8000/admin/

5. COMANDOS UTILES:

   - Ver registros / logs en tiempo real:
     docker compose logs -f

   - Detener los contenedores:
     docker compose stop

   - Detener y remover contenedores conservando la base de datos:
     docker compose down

   - Reiniciar desde cero (borrando volumenes de datos):
     docker compose down -v
================================================================================
