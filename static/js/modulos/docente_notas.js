// logica de navegacion rapida y calculo reactivo de calificaciones por fila
function limpiarSeccionYCurso() {
    const s = document.getElementById('seccionSelect');
    const c = document.getElementById('cursoSelect');
    if (s) s.removeAttribute('name');
    if (c) c.removeAttribute('name');
}

function limpiarCurso() {
    const c = document.getElementById('cursoSelect');
    if (c) c.removeAttribute('name');
}

document.addEventListener('DOMContentLoaded', function () {
    const rows = document.querySelectorAll('.nota-row');
    const inputs = document.querySelectorAll('.input-nota');

    function actualizarFila(row) {
        const inputZona = row.querySelector('.input-zona');
        const inputExamen = row.querySelector('.input-examen');
        const cellTotal = row.querySelector('.cell-total');
        const cellEstado = row.querySelector('.cell-estado');

        let zona = parseFloat(inputZona.value) || 0;
        let examen = parseFloat(inputExamen.value) || 0;

        // limitar dentro de rangos
        if (zona < 0) zona = 0;
        if (zona > 60) zona = 60;
        if (examen < 0) examen = 0;
        if (examen > 40) examen = 40;

        const total = Math.round((zona + examen) * 100) / 100;
        const esAprobado = total >= 60;

        // actualizar celda total
        cellTotal.innerHTML = `
            <span class="badge-total px-2.5 py-1 rounded-lg ${esAprobado ? 'text-emerald-700 bg-emerald-50 border border-emerald-200' : 'text-rose-700 bg-rose-50 border border-rose-200'}">
                ${total.toFixed(2)} pts
            </span>
        `;

        // actualizar celda estado
        cellEstado.innerHTML = esAprobado
            ? `<span class="badge-estado inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black bg-emerald-100 text-emerald-800 border border-emerald-200">
                <svg class="w-3 h-3 lucide lucide-check" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg> Aprobado
               </span>`
            : `<span class="badge-estado inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black bg-rose-100 text-rose-800 border border-rose-200">
                <svg class="w-3 h-3 lucide lucide-x" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg> Reprobado
               </span>`;

        actualizarResumenGlobal();
    }

    function actualizarResumenGlobal() {
        let countAprobados = 0;
        let countReprobados = 0;
        let sumaTotales = 0;
        let totalFilas = rows.length;

        rows.forEach(r => {
            const z = parseFloat(r.querySelector('.input-zona').value) || 0;
            const e = parseFloat(r.querySelector('.input-examen').value) || 0;
            const t = z + e;
            sumaTotales += t;
            if (t >= 60) {
                countAprobados++;
            } else {
                countReprobados++;
            }
        });

        const statAprobados = document.getElementById('statAprobados');
        const statReprobados = document.getElementById('statReprobados');
        const statPromedio = document.getElementById('statPromedio');

        if (statAprobados) statAprobados.textContent = countAprobados;
        if (statReprobados) statReprobados.textContent = countReprobados;
        if (statPromedio && totalFilas > 0) {
            statPromedio.textContent = (sumaTotales / totalFilas).toFixed(2) + ' pts';
        }
    }

    // eventos en inputs de notas
    inputs.forEach(input => {
        input.addEventListener('input', function () {
            const row = this.closest('.nota-row');
            if (row) actualizarFila(row);
        });

        // navegacion rapida con teclado: flechas arriba y abajo y enter
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
            }

            const isDown = e.key === 'ArrowDown' || e.key === 'Enter';
            const isUp = e.key === 'ArrowUp';

            if (isDown || isUp) {
                const currentRow = this.closest('.nota-row');
                const colType = this.getAttribute('data-col');
                let targetRow = isDown ? currentRow.nextElementSibling : currentRow.previousElementSibling;

                while (targetRow && !targetRow.classList.contains('nota-row')) {
                    targetRow = isDown ? targetRow.nextElementSibling : targetRow.previousElementSibling;
                }

                if (targetRow) {
                    const targetInput = targetRow.querySelector(`[data-col="${colType}"]`);
                    if (targetInput) {
                        targetInput.focus();
                        targetInput.select();
                    }
                }
            }
        });
    });
});
