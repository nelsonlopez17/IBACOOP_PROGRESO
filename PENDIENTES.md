# 📌 Lista de Pendientes y Funcionalidades Futuras — ERP IBACOOP EL PROGRESO

Este documento registra los requerimientos, flujos y funcionalidades pendientes por implementar en los distintos módulos del ERP.

---

## 🎓 Módulo Académico (Pendiente de Desarrollo)

### 1. Promoción de Grado y Reinscripción Automática al Siguiente Ciclo Lectivo
*   **Lógica de Promoción de Grado (Cierre Anual):**
    *   Proceso automatizado al finalizar el ciclo escolar activo que evalúa los promedios finales y recuperaciones (`NotaFinalCurso`).
    *   Etiquetado de estudiantes como `PROMOVIDO` (si aprobó el pensum $\ge 60$ pts) o `RETENIDO` (si reprobó materias).
*   **Proceso de Reinscripción Rápida (Nuevo Ciclo):**
    *   Interfaz de asignación masiva/individual para inscribir alumnos existentes en el nuevo ciclo escolar activo.
    *   El sistema sugerirá automáticamente el grado superior para alumnos `PROMOVIDOS` (ej. de 1ro Básico A a 2do Básico) y el mismo grado para alumnos `RETENIDOS`.
    *   Evita duplicar o reingresar datos personales del estudiante.

---

## 💰 Módulo Financiero / Cuentas por Cobrar (Pendiente de Integración)

### 1. Vinculación del Registro de Alumno con la Solvencia de Cuota de Inscripción
*   Generación automática de la `CuentaPorCobrar` por el concepto "Inscripción" al registrar a un alumno en el padrón.
*   Indicador de estado financiero en la Ficha del Alumno (`SOLVENTE` vs `PENDIENTE DE PAGO DE INSCRIPCIÓN`).
