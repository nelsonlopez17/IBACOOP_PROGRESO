---
trigger: always_on
description: Estandarización lingüística y dialectal de Guatemala y nomenclatura en español para IBACOOP EL PROGRESO
---

# Regla Permanente: Estandarización Lingüística de Guatemala (IBACOOP EL PROGRESO)

En todo cambio, creación de archivos `.py` o `.html`, modelos, vistas, formularios y reportes PDF:

1. **Unicidad de Términos (Dialecto y Normativa de Guatemala)**:
   - Usar siempre **Estudiante / Estudiantes** (nunca *Alumno / Alumnos / Educando*).
   - Usar siempre **Padre de Familia o Encargado / Encargado** (nunca *Tutor / Tutor Legal / Apoderado*).
   - Usar siempre **Docente Guía** (nunca *Docente Tutor de Sección*).
   - Usar siempre **Planilla de Sueldos / Planilla** y **Boleta de Pago** (nunca *Nómina* ni *Boleta de Nómina*).
   - Usar siempre **Inscripción / Inscribir / Inscritos** (nunca *Matrícula / Matricular / Matriculados*).
   - Usar siempre **Cuota Mensual / Cuotas Escolares** (nunca *Colegiatura / Arancel / Aranceles*).
   - Usar siempre **Boleta de Calificaciones** (nunca *Boletín*).
   - Usar siempre **Listado de Estudiantes** (nunca *Nómina de Alumnos*).
   - Usar siempre **Incidente Disciplinario / Disciplina y Convivencia** (nunca *Conductual / Conductal*).

2. **Nomenclatura de Archivos y Código**:
   - Nombrar archivos de negocio y plantillas en español estándar de Guatemala (evitar nombres en inglés como `tasks.py`, `dashboard.html`, `reports.py` en nuevos módulos).
   - Mantener coincidencia exacta entre los nombres de modelos Django y el nombre de las tablas en PostgreSQL.
