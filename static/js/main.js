document.addEventListener('DOMContentLoaded', function () {
    // Inicializar tooltips de Bootstrap
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(function (el) {
        new bootstrap.Tooltip(el);
    });

    // Auto-cerrar alertas flash despues de 5 segundos
    setTimeout(function () {
        document.querySelectorAll('.alert').forEach(function (alert) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        });
    }, 5000);

    // Confirmacion reutilizable para acciones sensibles
    window.confirmar = function (mensaje) {
        return confirm(mensaje || 'Estas seguro?');
    };

    // Navegacion al detalle al hacer click en la fila
    document.querySelectorAll('.fila-link').forEach(function (fila) {
        fila.addEventListener('click', function (event) {
            if (event.target.closest('a, button, input, select, textarea, form')) {
                return;
            }
            window.location = this.dataset.href;
        });
    });
});
