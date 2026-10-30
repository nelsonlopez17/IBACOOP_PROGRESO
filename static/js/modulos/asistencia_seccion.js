// logica de marcado rapido y contadores dinamicos de asistencia
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

function marcarTodosPresentes() {
    const radios = document.querySelectorAll('.radio-presente');
    radios.forEach(r => { r.checked = true; });
    actualizarContadoresAsistencia();
}

function actualizarContadoresAsistencia() {
    let presentes = 0;
    let ausentes = 0;
    let justificados = 0;

    document.querySelectorAll('.radio-presente').forEach(r => { if (r.checked) presentes++; });
    document.querySelectorAll('.radio-ausente').forEach(r => { if (r.checked) ausentes++; });
    document.querySelectorAll('.radio-justificado').forEach(r => { if (r.checked) justificados++; });

    const elP = document.getElementById('counterPresentes');
    const elA = document.getElementById('counterAusentes');
    const elJ = document.getElementById('counterJustificados');
    if (elP) elP.textContent = presentes;
    if (elA) elA.textContent = ausentes;
    if (elJ) elJ.textContent = justificados;
}
