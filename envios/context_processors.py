from .models import Encomienda


def estadisticas_globales(request):
    if not request.user.is_authenticated:
        return {
            'nav_activas': 0,
            'nav_retraso': 0,
            'nav_pendientes': 0,
        }

    return {
        'nav_activas': Encomienda.objects.activas().count(),
        'nav_retraso': Encomienda.objects.con_retraso().count(),
        'nav_pendientes': Encomienda.objects.pendientes().count(),
    }
