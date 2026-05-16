from rest_framework.permissions import BasePermission

from config.choices import EstadoGeneral
from envios.models import Empleado


class EsEmpleadoActivo(BasePermission):
    """Solo empleados activos del sistema pueden acceder."""

    message = 'Solo empleados activos tienen acceso a esta API.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return Empleado.objects.filter(
            email=request.user.email,
            estado=EstadoGeneral.ACTIVO,
        ).exists()


class EsPropietarioOAdmin(BasePermission):
    """Permite modificar solo encomiendas propias, salvo usuarios admin."""

    message = 'Solo puedes modificar encomiendas registradas por tu usuario.'

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True

        return obj.empleado_registro.email == request.user.email
