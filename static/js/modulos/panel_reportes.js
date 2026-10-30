// configuracion y logica para la emision parametrica de reportes y proceso en segundo plano
let reporteActual = null;

const CONFIG_REPORTES = {
    'boleta_individual': {
        titulo: 'Boleta Oficial de Calificaciones',
        subtitulo: 'Seleccione grado, seccion y estudiante para generar la boleta.',
        campos: ['ciclo', 'grado_seccion', 'estudiante'],
        permitePDF: true,
        permiteExcel: false
    },
    'cuadro_calificaciones': {
        titulo: 'Cuadro General de Calificaciones por Seccion',
        subtitulo: 'Matriz consolidada de cursos y calificaciones acumuladas.',
        campos: ['ciclo', 'grado_seccion'],
        permitePDF: true,
        permiteExcel: true
    },
    'listado_estudiantes': {
        titulo: 'Listado Oficial de Estudiantes Inscritos',
        subtitulo: 'Padron escolar de la seccion con datos de contacto y encargado.',
        campos: ['ciclo', 'grado_seccion'],
        permitePDF: true,
        permiteExcel: true
    },
    'cuadro_honor': {
        titulo: 'Cuadro de Honor y Excelencia Academica',
        subtitulo: 'Ranking de los mejores promedios acumulados de la seccion.',
        campos: ['ciclo', 'grado_seccion'],
        permitePDF: true,
        permiteExcel: true
    },
    'constancia_inscripcion': {
        titulo: 'Constancia Oficial de Inscripcion Escolar',
        subtitulo: 'Seleccione el estudiante para extender la constancia oficial.',
        campos: ['ciclo', 'grado_seccion', 'estudiante'],
        permitePDF: true,
        permiteExcel: false
    },
    'antiguedad_saldos': {
        titulo: 'Antiguedad de Saldos y Morosidad',
        subtitulo: 'Corte de cartera estratificado en quetzales.',
        campos: ['ciclo'],
        permitePDF: true,
        permiteExcel: true
    },
    'cuadre_caja': {
        titulo: 'Arqueo y Cuadre Diario de Caja',
        subtitulo: 'Consolidado de cobros y recibos por rango de fechas.',
        campos: ['fechas'],
        permitePDF: true,
        permiteExcel: true
    },
    'estado_cuenta': {
        titulo: 'Estado de Cuenta y Solvencia',
        subtitulo: 'Registro de cuotas y abonos del estudiante.',
        campos: ['ciclo', 'grado_seccion', 'estudiante'],
        permitePDF: true,
        permiteExcel: false
    },
    'consolidado_planilla': {
        titulo: 'Consolidado Mensual de Planilla',
        subtitulo: 'Planilla general de sueldos, decreto 37-2001 e igss.',
        campos: ['ciclo', 'mes'],
        permitePDF: true,
        permiteExcel: true
    },
    'boleta_pago_individual': {
        titulo: 'Boleta Oficial de Pago de Salario',
        subtitulo: 'Comprobante individual para firma del colaborador.',
        campos: ['planilla_individual'],
        permitePDF: true,
        permiteExcel: false
    },
    'disciplina_historial': {
        titulo: 'Historial de Disciplina y Convivencia',
        subtitulo: 'Faltas tipificadas y medidas formativas aplicadas.',
        campos: ['ciclo', 'grado_seccion'],
        permitePDF: true,
        permiteExcel: true
    },
    'directorio_personal': {
        titulo: 'Directorio Oficial de Personal',
        subtitulo: 'Directorio oficial del personal docente y operativo configurable por estado.',
        campos: ['estado_laboral'],
        permitePDF: true,
        permiteExcel: true
    }
};

function abrirModalReporte(tipoReporte) {
    reporteActual = tipoReporte;
    const conf = CONFIG_REPORTES[tipoReporte];
    if (!conf) return;

    document.getElementById('modal-titulo').innerText = conf.titulo;
    document.getElementById('modal-subtitulo').innerText = conf.subtitulo;
    document.getElementById('modal-error').classList.add('hidden');

    // mostrar u ocultar campos segun corresponda
    document.getElementById('campo-ciclo').style.display = conf.campos.includes('ciclo') ? 'block' : 'none';
    document.getElementById('campo-grado-seccion').style.display = conf.campos.includes('grado_seccion') ? 'grid' : 'none';
    document.getElementById('campo-estudiante').style.display = conf.campos.includes('estudiante') ? 'block' : 'none';
    document.getElementById('campo-fechas').style.display = conf.campos.includes('fechas') ? 'grid' : 'none';
    document.getElementById('campo-mes').style.display = conf.campos.includes('mes') ? 'block' : 'none';
    document.getElementById('campo-planilla-individual').style.display = conf.campos.includes('planilla_individual') ? 'block' : 'none';
    document.getElementById('campo-estado-laboral').style.display = conf.campos.includes('estado_laboral') ? 'block' : 'none';

    // botones de salida
    document.getElementById('modal-btn-pdf').style.display = conf.permitePDF ? 'inline-flex' : 'none';
    document.getElementById('modal-btn-excel').style.display = conf.permiteExcel ? 'inline-flex' : 'none';

    // resetear selectores dependientes
    document.getElementById('modal-select-grado').selectedIndex = 0;
    document.getElementById('modal-select-seccion').innerHTML = '<option value="">-- Primero elija el Grado --</option>';
    document.getElementById('modal-select-estudiante').innerHTML = '<option value="">-- Seleccione una seccion primero --</option>';

    document.getElementById('modal-reporte').classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function cerrarModalReporte() {
    document.getElementById('modal-reporte').classList.add('hidden');
    reporteActual = null;
}

// carga dinamica de secciones segun el grado elegido
function cargarSeccionesPorGrado(gradoId) {
    const selectSec = document.getElementById('modal-select-seccion');
    selectSec.innerHTML = '<option value="">Cargando secciones...</option>';
    document.getElementById('modal-select-estudiante').innerHTML = '<option value="">-- Seleccione una seccion primero --</option>';

    if (!gradoId) {
        selectSec.innerHTML = '<option value="">-- Primero elija el Grado --</option>';
        return;
    }

    fetch(`/reportes/api/secciones-por-grado/${gradoId}/`)
        .then(r => r.json())
        .then(data => {
            selectSec.innerHTML = '<option value="">-- Seleccionar Seccion --</option>';
            if (data.secciones && data.secciones.length > 0) {
                data.secciones.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    opt.textContent = s.nombre;
                    selectSec.appendChild(opt);
                });
            } else {
                selectSec.innerHTML = '<option value="">No hay secciones en este grado</option>';
            }
        })
        .catch(err => {
            selectSec.innerHTML = '<option value="">Error al cargar secciones</option>';
            console.error(err);
        });
}

// carga dinamica de estudiantes segun la seccion y ciclo escolar elegidos
function onSeccionCambiada(seccionId) {
    const conf = CONFIG_REPORTES[reporteActual];
    if (!conf || !conf.campos.includes('estudiante')) return;

    const selectEst = document.getElementById('modal-select-estudiante');
    const cicloId = document.getElementById('modal-select-ciclo').value;

    if (!seccionId) {
        selectEst.innerHTML = '<option value="">-- Seleccione una seccion primero --</option>';
        return;
    }

    selectEst.innerHTML = '<option value="">Cargando estudiantes...</option>';
    fetch(`/reportes/api/estudiantes-por-seccion/${seccionId}/${cicloId}/`)
        .then(r => r.json())
        .then(data => {
            selectEst.innerHTML = '<option value="">-- Seleccionar Estudiante --</option>';
            if (data.estudiantes && data.estudiantes.length > 0) {
                data.estudiantes.forEach(e => {
                    const opt = document.createElement('option');
                    opt.value = e.id;
                    opt.textContent = `${e.nombre_completo} | CUI: ${e.cui}`;
                    selectEst.appendChild(opt);
                });
            } else {
                selectEst.innerHTML = '<option value="">No hay estudiantes inscritos en esta seccion</option>';
            }
        })
        .catch(err => {
            selectEst.innerHTML = '<option value="">Error al cargar estudiantes</option>';
            console.error(err);
        });
}

// ejecucion de la emision parametrica del reporte
function ejecutarEmision(formato) {
    const conf = CONFIG_REPORTES[reporteActual];
    if (!conf) return;

    const cicloId = document.getElementById('modal-select-ciclo').value;
    const seccionId = document.getElementById('modal-select-seccion').value;
    const estudianteId = document.getElementById('modal-select-estudiante').value;
    const fechaIni = document.getElementById('modal-fecha-ini').value;
    const fechaFin = document.getElementById('modal-fecha-fin').value;
    const mes = document.getElementById('modal-select-mes').value;
    const planillaId = document.getElementById('modal-select-planilla-id').value;
    const errBox = document.getElementById('modal-error');
    const errText = document.getElementById('modal-error-text');

    errBox.classList.add('hidden');

    // validaciones segun el reporte
    if (conf.campos.includes('grado_seccion') && !seccionId && reporteActual !== 'disciplina_historial') {
        errText.innerText = 'Debe seleccionar el grado y la seccion.';
        errBox.classList.remove('hidden');
        return;
    }

    if (conf.campos.includes('estudiante') && !estudianteId) {
        errText.innerText = 'Debe seleccionar un estudiante.';
        errBox.classList.remove('hidden');
        return;
    }

    if (conf.campos.includes('planilla_individual') && !planillaId) {
        errText.innerText = 'Debe seleccionar una boleta de planilla valida.';
        errBox.classList.remove('hidden');
        return;
    }

    let url = '';
    if (reporteActual === 'boleta_individual') {
        url = `/reportes/academico/boleta/${estudianteId}/${cicloId}/`;
    } else if (reporteActual === 'cuadro_calificaciones') {
        url = `/reportes/academico/cuadro-calificaciones/?seccion_id=${seccionId}&ciclo_id=${cicloId}&formato=${formato}`;
    } else if (reporteActual === 'listado_estudiantes') {
        url = `/reportes/academico/listado-estudiantes/?seccion_id=${seccionId}&ciclo_id=${cicloId}&formato=${formato}`;
    } else if (reporteActual === 'cuadro_honor') {
        url = `/reportes/academico/cuadro-honor/?seccion_id=${seccionId}&ciclo_id=${cicloId}&formato=${formato}`;
    } else if (reporteActual === 'constancia_inscripcion') {
        url = `/reportes/academico/constancia-inscripcion/${estudianteId}/${cicloId}/`;
    } else if (reporteActual === 'antiguedad_saldos') {
        url = `/reportes/financiero/antiguedad-saldos/?ciclo_id=${cicloId}&formato=${formato}`;
    } else if (reporteActual === 'cuadre_caja') {
        url = `/reportes/financiero/cuadre-caja/?fecha_inicio=${fechaIni}&fecha_fin=${fechaFin}&formato=${formato}`;
    } else if (reporteActual === 'estado_cuenta') {
        url = `/reportes/financiero/estado-cuenta/${estudianteId}/${cicloId}/`;
    } else if (reporteActual === 'consolidado_planilla') {
        url = `/reportes/rrhh/consolidado-planillas/?ciclo_id=${cicloId}&mes=${mes}&formato=${formato}`;
    } else if (reporteActual === 'boleta_pago_individual') {
        url = `/reportes/rrhh/boleta-pago/${planillaId}/`;
    } else if (reporteActual === 'disciplina_historial') {
        const secParam = seccionId ? `&seccion_id=${seccionId}` : '';
        url = `/reportes/disciplina/historial/?ciclo_id=${cicloId}${secParam}&formato=${formato}`;
    } else if (reporteActual === 'directorio_personal') {
        const estado = document.getElementById('modal-select-estado-laboral').value;
        const estadoParam = estado ? `&estado=${encodeURIComponent(estado)}` : '';
        url = `/reportes/rrhh/directorio/?formato=${formato}${estadoParam}`;
    }

    if (url) {
        if (formato === 'pdf') {
            window.open(url, '_blank');
        } else {
            window.location.href = url;
        }
        cerrarModalReporte();
    }
}

// buscador interactivo en vivo y filtro por categorias
document.addEventListener('DOMContentLoaded', function () {
    const buscador = document.getElementById('buscador-reportes');
    if (!buscador) return;

    const tarjetas = Array.from(document.querySelectorAll('.tarjeta-reporte'));
    const tabBtns = Array.from(document.querySelectorAll('.btn-tab-categoria'));
    let categoriaActiva = 'todos';

    function filtrarCatalogo() {
        const query = buscador.value.trim().toLowerCase();

        tarjetas.forEach(t => {
            const cat = t.getAttribute('data-categoria') || '';
            const tit = t.getAttribute('data-titulo') || '';
            const desc = t.getAttribute('data-desc') || '';

            const coincideCat = (categoriaActiva === 'todos' || cat === categoriaActiva);
            const coincideTexto = !query || tit.includes(query) || desc.includes(query);

            if (coincideCat && coincideTexto) {
                t.style.display = 'flex';
            } else {
                t.style.display = 'none';
            }
        });
    }

    buscador.addEventListener('input', filtrarCatalogo);

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            tabBtns.forEach(b => {
                b.className = 'btn-tab-categoria px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-white text-slate-600 hover:bg-slate-100 border border-slate-200 cursor-pointer';
            });
            this.className = 'btn-tab-categoria px-3 py-1.5 rounded-xl text-xs font-bold transition-all bg-[#1E6532] text-white shadow-xs cursor-pointer';
            categoriaActiva = this.getAttribute('data-categoria') || 'todos';
            filtrarCatalogo();
        });
    });
});

// control del procesamiento asincrono en segundo plano
let celeryPollInterval = null;

function iniciarGeneracionZip() {
    const secId = document.getElementById('select-seccion-zip').value;
    const cicloId = document.getElementById('select-ciclo-zip').value;
    const btn = document.getElementById('btn-iniciar-zip');
    const panel = document.getElementById('celery-progress-panel');
    const bar = document.getElementById('celery-progress-bar');
    const percentTxt = document.getElementById('celery-progress-percent');
    const statusTxt = document.getElementById('celery-status-text');
    const estDetail = document.getElementById('celery-estudiante-detail');
    const countDetail = document.getElementById('celery-count-detail');
    const downloadBtn = document.getElementById('celery-download-btn');
    const errorAlert = document.getElementById('celery-error-alert');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '';

    if (!secId || !cicloId) {
        alert('Por favor seleccione la seccion y el ciclo escolar.');
        return;
    }

    if (celeryPollInterval) clearInterval(celeryPollInterval);
    btn.disabled = true;
    btn.classList.add('opacity-50', 'cursor-not-allowed');
    panel.classList.remove('hidden');
    bar.style.width = '0%';
    percentTxt.innerText = '0%';
    statusTxt.innerText = 'Iniciando proceso en segundo plano...';
    estDetail.innerText = 'En cola de procesamiento...';
    countDetail.innerText = '';
    downloadBtn.classList.add('hidden');
    errorAlert.classList.add('hidden');

    const formData = new FormData();
    formData.append('seccion_id', secId);
    formData.append('ciclo_id', cicloId);

    const endpointUrl = btn.getAttribute('data-url-iniciar') || '/reportes/asincrono/boletas-zip/iniciar/';

    fetch(endpointUrl, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': csrfToken }
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            throw new Error(data.error || 'No se pudo iniciar la tarea asincrona.');
        }
        const taskId = data.task_id;
        statusTxt.innerText = 'Tarea en ejecucion, procesando boletas...';

        celeryPollInterval = setInterval(() => {
            fetch(`/reportes/asincrono/tarea/${taskId}/estado/`)
            .then(r => r.json())
            .then(taskData => {
                if (taskData.state === 'PROGRESS') {
                    const pct = taskData.percent || 0;
                    bar.style.width = pct + '%';
                    percentTxt.innerText = pct + '%';
                    statusTxt.innerText = 'Generando boletas oficiales en pdf...';
                    estDetail.innerText = taskData.estudiante_actual ? `Estudiante: ${taskData.estudiante_actual}` : '';
                    countDetail.innerText = `${taskData.current || 0} de ${taskData.total || 0}`;
                } else if (taskData.state === 'SUCCESS') {
                    clearInterval(celeryPollInterval);
                    bar.style.width = '100%';
                    percentTxt.innerText = '100%';
                    statusTxt.innerText = '¡Proceso completado!';
                    estDetail.innerText = taskData.mensaje || `Se generaron ${taskData.total || 0} boletas.`;
                    countDetail.innerText = `${taskData.total || 0} de ${taskData.total || 0}`;

                    if (taskData.archivo_url) {
                        downloadBtn.href = taskData.archivo_url;
                        document.getElementById('celery-download-label').innerText = `Descargar ${taskData.filename}`;
                        downloadBtn.classList.remove('hidden');
                        if (window.lucide) lucide.createIcons();
                    }

                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                } else if (taskData.state === 'FAILURE' || taskData.status === 'ERROR') {
                    clearInterval(celeryPollInterval);
                    errorAlert.classList.remove('hidden');
                    document.getElementById('celery-error-text').innerText = taskData.error || taskData.mensaje || 'Error al generar el lote.';
                    statusTxt.innerText = 'Error en el proceso';
                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            })
            .catch(err => {
                console.error('Error al sondear estado de tarea:', err);
            });
        }, 1200);
    })
    .catch(err => {
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
        errorAlert.classList.remove('hidden');
        document.getElementById('celery-error-text').innerText = err.message || 'Error al conectar con el servidor.';
    });
}
