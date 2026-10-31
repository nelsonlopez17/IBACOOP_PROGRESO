/**
 * ibacoop el progreso - logica de interfaz y componentes
 */

// inicializacion de iconos lucide
function initLucideIcons() {
    if (window.lucide && typeof lucide.createIcons === 'function') {
        try {
            lucide.createIcons();
        } catch (e) {
            console.error('error al inicializar iconos lucide:', e);
        }
    }
}

// inicializacion de notificaciones emergentes (notyf)
function initNotyfToasts() {
    const toastItems = document.querySelectorAll('#django-toast-messages .django-toast-item');
    if (toastItems.length > 0 && typeof Notyf !== 'undefined') {
        const notyf = new Notyf({
            duration: 5000,
            position: { x: 'right', y: 'top' },
            dismissible: true,
            ripple: false,
            types: [
                {
                    type: 'success',
                    background: '#1E6532',
                    className: 'notyf__toast--success',
                    duration: 5000,
                    icon: { className: 'notyf__icon--success', tagName: 'i' }
                },
                {
                    type: 'error',
                    background: '#7A1C21',
                    className: 'notyf__toast--error',
                    duration: 6500,
                    icon: { className: 'notyf__icon--error', tagName: 'i' }
                },
                {
                    type: 'warning',
                    background: '#D97706',
                    className: 'notyf__toast--warning',
                    duration: 6000,
                    icon: false
                },
                {
                    type: 'info',
                    background: '#3C7DA8',
                    className: 'notyf__toast--info',
                    duration: 5000,
                    icon: false
                }
            ]
        });

        toastItems.forEach(function (item) {
            const rawTag = (item.getAttribute('data-tag') || item.getAttribute('data-tags') || 'info').toLowerCase();
            const text = item.textContent.trim();
            if (!text) return;

            let type = 'info';
            if (rawTag.includes('error') || rawTag.includes('danger')) {
                type = 'error';
            } else if (rawTag.includes('warning')) {
                type = 'warning';
            } else if (rawTag.includes('success')) {
                type = 'success';
            }
            notyf.open({ type: type, message: text });
        });
    }
}

// control de barra lateral movil en erp
function initMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    const closeBtn = document.getElementById('sidebar-close-btn');

    function openSidebar() {
        if (sidebar) sidebar.classList.remove('-translate-x-full');
        if (overlay) overlay.classList.remove('hidden');
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.add('-translate-x-full');
        if (overlay) overlay.classList.add('hidden');
    }

    if (toggleBtn) toggleBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);
}

// control de navegacion movil en portal web
function initMobilePortalMenu() {
    const menuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');

    if (menuBtn && mobileMenu) {
        menuBtn.addEventListener('click', function () {
            mobileMenu.classList.toggle('hidden');
        });
    }
}

// enfoque automatico en el primer campo con error de validacion
function focusFirstInvalidField() {
    const firstInvalidField = document.querySelector('[aria-invalid="true"]');
    if (firstInvalidField) {
        firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(function () {
            firstInvalidField.focus({ preventScroll: true });
        }, 300);
    }
}

// inicializacion de selectores con busqueda predictiva
function initSearchableSelects() {
    if (typeof TomSelect === 'undefined') return;
    document.querySelectorAll('select.searchable-select, select[data-searchable="true"]').forEach(function (el) {
        if (!el.tomselect) {
            new TomSelect(el, {
                create: false,
                maxOptions: 500,
                placeholder: el.getAttribute('data-placeholder') || el.getAttribute('placeholder') || 'Escriba para buscar por nombre, CUI/DPI o codigo...',
                allowEmptyOption: true,
                render: {
                    no_results: function (data, escape) {
                        return '<div class="no-results p-3 text-sm text-slate-500 text-center">No se encontraron resultados para "' + escape(data.input) + '"</div>';
                    }
                }
            });
        }
    });
}

// ejecucion al cargar el dom y tras peticiones htmx
function initComponentes() {
    initLucideIcons();
    initNotyfToasts();
    initMobileSidebar();
    initMobilePortalMenu();
    focusFirstInvalidField();
    initSearchableSelects();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initComponentes);
} else {
    initComponentes();
}

// respaldo inmediato y al cargar la ventana
initLucideIcons();
window.addEventListener('load', initLucideIcons);

if (document.body) {
    document.body.addEventListener('htmx:afterSwap', function () {
        initLucideIcons();
        initSearchableSelects();
    });
}
