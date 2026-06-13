import asyncio

from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from config.choices import EstadoEnvio

from .models import Encomienda


async def dashboard_stats_async(request):
    """
    Endpoint async que calcula las estadisticas del dashboard.
    Las 4 consultas corren en paralelo con asyncio.gather().
    """
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    hoy = timezone.now().date()
    total_activas, en_transito, con_retraso, entregadas_hoy = await asyncio.gather(
        Encomienda.objects.activas().acount(),
        Encomienda.objects.en_transito().acount(),
        Encomienda.objects.con_retraso().acount(),
        Encomienda.objects.filter(
            estado=EstadoEnvio.ENTREGADO,
            fecha_entrega_real=hoy,
        ).acount(),
    )

    return JsonResponse({
        'total_activas': total_activas,
        'en_transito': en_transito,
        'con_retraso': con_retraso,
        'entregadas_hoy': entregadas_hoy,
    })
