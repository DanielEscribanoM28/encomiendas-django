from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Limitar intentos de login: 5 por minuto."""

    scope = 'login_attempt'


class BurstRateThrottle(AnonRateThrottle):
    """Limite corto para endpoints publicos o anonimos."""

    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """Limite sostenido para usuarios autenticados."""

    scope = 'sustained'


class EmpleadoRateThrottle(UserRateThrottle):
    """Empleados: 100 peticiones por minuto."""

    scope = 'empleado'


class CambioEstadoThrottle(UserRateThrottle):
    """Limitar cambios de estado: 30 por hora."""

    scope = 'cambio_estado'
