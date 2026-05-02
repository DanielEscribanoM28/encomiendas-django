from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from config.choices import EstadoEnvio

from .forms import EncomiendaForm
from .models import Empleado, Encomienda


def _obtener_empleado_actual(user):
    """Obtiene el empleado asociado al usuario autenticado por correo."""
    if not user.is_authenticated:
        return None
    return Empleado.objects.filter(email=user.email).first()


@login_required
def dashboard(request):
    """Vista principal del sistema con estadisticas."""
    hoy = timezone.now().date()
    context = {
        'total_activas': Encomienda.objects.activas().count(),
        'en_transito': Encomienda.objects.en_transito().count(),
        'con_retraso': Encomienda.objects.con_retraso().count(),
        'entregadas_hoy': Encomienda.objects.filter(
            estado=EstadoEnvio.ENTREGADO,
            fecha_entrega_real=hoy,
        ).count(),
        'ultimas': Encomienda.objects.con_relaciones()[:5],
    }
    return render(request, 'envios/dashboard.html', context)


@require_GET
@login_required
def encomienda_lista(request):
    """Listado con filtros GET y paginacion de 15 registros."""
    qs = Encomienda.objects.con_relaciones()

    # Leer parametros enviados en la URL
    estado = request.GET.get('estado', '')
    q = request.GET.get('q', '')

    # Filtro opcional por estado
    if estado:
        qs = qs.filter(estado=estado)

    # Busqueda por codigo o cliente
    if q:
        qs = qs.filter(
            Q(codigo__icontains=q)
            | Q(remitente__apellidos__icontains=q)
            | Q(remitente__nombres__icontains=q)
            | Q(destinatario__apellidos__icontains=q)
            | Q(destinatario__nombres__icontains=q)
        )

    # Paginacion del QuerySet
    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page', 1)
    encomiendas = paginator.get_page(page_number)

    return render(
        request,
        'envios/lista.html',
        {
            'encomiendas': encomiendas,
            'estados': EstadoEnvio.choices,
            'estado_activo': estado,
            'q': q,
        },
    )


@login_required
def encomienda_detalle(request, pk):
    """Detalle de una encomienda con su historial de estados."""
    encomienda = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)
    historial = encomienda.historial.select_related('empleado')
    return render(
        request,
        'envios/detalle.html',
        {
            'encomienda': encomienda,
            'historial': historial,
            'estados': EstadoEnvio.choices,
        },
    )


@login_required
def encomienda_crear(request):
    """
    GET  -> muestra el formulario vacio
    POST -> valida, guarda y redirige al detalle
    """
    if request.method == 'POST':
        form = EncomiendaForm(request.POST)
        if form.is_valid():
            # form.save(commit=False) crea la instancia sin guardarla aun
            enc = form.save(commit=False)
            empleado = _obtener_empleado_actual(request.user)
            if empleado is None:
                messages.error(
                    request,
                    'Tu usuario no tiene un empleado asociado por correo electronico.',
                )
                return render(
                    request,
                    'envios/form.html',
                    {'form': form, 'titulo': 'Nueva Encomienda'},
                )

            # Asignar el empleado que registra antes de guardar
            enc.empleado_registro = empleado
            enc.save()
            messages.success(
                request,
                f'Encomienda {enc.codigo} registrada correctamente.',
            )
            # Patron Post/Redirect/Get: evitar reenvio al recargar
            return redirect('encomienda_detalle', pk=enc.pk)
        messages.error(request, 'Corrige los errores del formulario.')
    else:
        # GET: formulario vacio
        form = EncomiendaForm()

    return render(request, 'envios/form.html', {'form': form, 'titulo': 'Nueva Encomienda'})


@require_POST
@login_required
def encomienda_cambiar_estado(request, pk):
    """Procesa el cambio de estado desde request.POST."""
    encomienda = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)
    nuevo_estado = request.POST.get('estado')
    observacion = request.POST.get('observacion', '')
    empleado = _obtener_empleado_actual(request.user)

    if empleado is None:
        messages.error(request, 'Tu usuario no tiene un empleado asociado para registrar cambios.')
        return redirect('encomienda_detalle', pk=pk)

    try:
        encomienda.cambiar_estado(nuevo_estado, empleado, observacion)
        messages.success(
            request,
            f'Estado actualizado a: {encomienda.get_estado_display()}',
        )
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect('encomienda_detalle', pk=pk)
