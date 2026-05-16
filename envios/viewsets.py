from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from api.exceptions import EncomiendaYaEntregadaError, EstadoInvalidoError
from api.filters import EncomiendaFilter
from api.pagination import EncomiendaPagination, HistorialPagination
from api.permissions import EsEmpleadoActivo, EsPropietarioOAdmin
from api.throttles import CambioEstadoThrottle, EmpleadoRateThrottle
from config.choices import EstadoEnvio
from config.settings import CACHE_TTL
from rutas.models import Ruta

from .models import Empleado, Encomienda
from .serializers import (
    EncomiendaDetailSerializer,
    EncomiendaListSerializer,
    EncomiendaSerializer,
    EncomiendaV2Serializer,
    HistorialEstadoSerializer,
    RutaSerializer,
)


def _obtener_empleado_actual(user):
    return Empleado.objects.filter(email=user.email).first()


@extend_schema_view(
    list=extend_schema(
        summary='Listar encomiendas',
        description='Lista encomiendas con paginacion, filtros, busqueda y ordenamiento.',
        tags=['Encomiendas'],
        parameters=[
            OpenApiParameter('estado', OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter('ruta', OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter('remitente', OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter('desde', OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter('hasta', OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter('con_retraso', OpenApiTypes.BOOL, OpenApiParameter.QUERY),
            OpenApiParameter('search', OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter('ordering', OpenApiTypes.STR, OpenApiParameter.QUERY),
        ],
    ),
    create=extend_schema(
        summary='Crear encomienda',
        description='Crea una nueva encomienda y asigna el empleado segun el JWT.',
        tags=['Encomiendas'],
    ),
    retrieve=extend_schema(
        summary='Detalle de encomienda',
        description='Obtiene una encomienda con clientes, ruta, empleado e historial.',
        tags=['Encomiendas'],
    ),
    update=extend_schema(summary='Actualizar encomienda', tags=['Encomiendas']),
    partial_update=extend_schema(summary='Actualizar parcial', tags=['Encomiendas']),
    destroy=extend_schema(summary='Eliminar encomienda', tags=['Encomiendas']),
)
class EncomiendaViewSet(viewsets.ModelViewSet):
    queryset = Encomienda.objects.con_relaciones()
    permission_classes = [EsEmpleadoActivo]
    pagination_class = EncomiendaPagination
    throttle_classes = [EmpleadoRateThrottle]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EncomiendaFilter
    search_fields = [
        'codigo',
        'remitente__apellidos',
        'destinatario__apellidos',
        'descripcion',
    ]
    ordering_fields = ['fecha_registro', 'peso_kg', 'costo_envio']
    ordering = ['-fecha_registro']

    def get_serializer_class(self):
        version = getattr(self.request, 'version', 'v1')

        if version == 'v2':
            return EncomiendaV2Serializer

        if self.action == 'list':
            return EncomiendaListSerializer
        if self.action == 'retrieve':
            return EncomiendaDetailSerializer
        return EncomiendaSerializer

    def get_queryset(self):
        qs = Encomienda.objects.con_relaciones()
        version = getattr(self.request, 'version', 'v1')

        if self.action == 'list' and version == 'v1':
            qs = qs.only(
                'id',
                'codigo',
                'estado',
                'peso_kg',
                'costo_envio',
                'fecha_registro',
                'fecha_entrega_est',
                'remitente__nombres',
                'remitente__apellidos',
                'destinatario__nombres',
                'destinatario__apellidos',
                'ruta__destino',
                'empleado_registro__id',
                'empleado_registro__codigo',
                'empleado_registro__nombres',
                'empleado_registro__apellidos',
                'empleado_registro__cargo',
                'empleado_registro__email',
            )

        return qs

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [EsEmpleadoActivo(), EsPropietarioOAdmin()]
        return [EsEmpleadoActivo()]

    def get_throttles(self):
        if self.action == 'cambiar_estado':
            return [CambioEstadoThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer):
        empleado = _obtener_empleado_actual(self.request.user)
        serializer.save(empleado_registro=empleado)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache.delete(f'estadisticas_empleado_{self.request.user.id}')

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response['X-API-Version'] = getattr(request, 'version', 'v1')
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response['X-API-Version'] = getattr(request, 'version', 'v1')
        return response

    @extend_schema(
        summary='Cambiar estado de encomienda',
        description='Cambia el estado de una encomienda y registra el historial.',
        tags=['Encomiendas'],
        examples=[
            OpenApiExample(
                'Cambio a transito',
                value={'estado': 'TR', 'observacion': 'Recogido en agencia Lima'},
                request_only=True,
            )
        ],
        responses={
            200: EncomiendaSerializer,
            400: OpenApiResponse(description='Estado invalido'),
            409: OpenApiResponse(description='La encomienda ya fue entregada'),
        },
    )
    @action(detail=True, methods=['post'], url_path='cambiar_estado')
    def cambiar_estado(self, request, pk=None, *args, **kwargs):
        enc = self.get_object()
        nuevo_estado = request.data.get('estado')
        observacion = request.data.get('observacion', '')

        if not nuevo_estado:
            return Response(
                {'error': 'El campo estado es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if nuevo_estado not in EstadoEnvio.values:
            return Response(
                {'error': 'El estado enviado no es valido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if enc.esta_entregada:
            raise EncomiendaYaEntregadaError()

        empleado = _obtener_empleado_actual(request.user)
        if empleado is None:
            return Response(
                {'error': 'El usuario no tiene empleado asociado por email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            enc.cambiar_estado(nuevo_estado, empleado, observacion)
            cache.delete_many(
                [
                    f'estadisticas_empleado_{request.user.id}',
                    f'encomienda_detalle_{pk}',
                ]
            )
            return Response(EncomiendaSerializer(enc).data)
        except ValueError as exc:
            raise EstadoInvalidoError(detail=str(exc))

    @extend_schema(
        summary='Encomiendas con retraso',
        description='Lista encomiendas activas cuya fecha estimada ya vencio.',
        tags=['Encomiendas'],
    )
    @action(detail=False, methods=['get'], url_path='con_retraso')
    def con_retraso(self, request, *args, **kwargs):
        qs = Encomienda.objects.con_retraso().con_relaciones()
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(
        summary='Encomiendas pendientes',
        description='Lista encomiendas en estado pendiente.',
        tags=['Encomiendas'],
    )
    @action(detail=False, methods=['get'])
    def pendientes(self, request, *args, **kwargs):
        qs = Encomienda.objects.pendientes().con_relaciones()
        return Response(self.get_serializer(qs, many=True).data)

    @extend_schema(
        summary='Historial de estados',
        description='Lista el historial de cambios de estado de una encomienda.',
        tags=['Encomiendas'],
    )
    @action(detail=True, methods=['get'], url_path='historial')
    def historial(self, request, pk=None, *args, **kwargs):
        enc = self.get_object()
        qs = enc.historial.select_related('empleado').order_by('-fecha_cambio')

        paginator = HistorialPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = HistorialEstadoSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = HistorialEstadoSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Estadisticas globales',
        description='Devuelve contadores principales de encomiendas. Usa cache por usuario.',
        tags=['Encomiendas'],
    )
    @action(detail=False, methods=['get'])
    def estadisticas(self, request, *args, **kwargs):
        from django.utils import timezone

        cache_key = f'estadisticas_empleado_{request.user.id}'
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        hoy = timezone.now().date()
        data = {
            'total_activas': Encomienda.objects.activas().count(),
            'en_transito': Encomienda.objects.en_transito().count(),
            'con_retraso': Encomienda.objects.con_retraso().count(),
            'entregadas_hoy': Encomienda.objects.entregadas().filter(
                fecha_entrega_real=hoy,
            ).count(),
            'entregadas_mes': Encomienda.objects.entregadas().filter(
                fecha_entrega_real__month=hoy.month,
            ).count(),
        }
        cache.set(cache_key, data, CACHE_TTL)
        return Response(data)

    @extend_schema(
        summary='Crear multiples encomiendas',
        description='Crea varias encomiendas en una sola peticion. Body: lista de objetos.',
        tags=['Encomiendas'],
    )
    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        empleado = _obtener_empleado_actual(request.user)
        if empleado is None:
            return Response(
                {'error': 'El usuario no tiene un empleado asociado.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        encomiendas = serializer.save(empleado_registro=empleado)
        cache.delete(f'estadisticas_empleado_{request.user.id}')
        return Response(
            self.get_serializer(encomiendas, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary='Cambiar estado a multiples encomiendas',
        description='Cambia el estado de varias encomiendas y reporta errores por item.',
        tags=['Encomiendas'],
    )
    @action(detail=False, methods=['patch'], url_path='bulk_estado')
    def bulk_estado(self, request, *args, **kwargs):
        ids = request.data.get('ids', [])
        nuevo_estado = request.data.get('estado')
        observacion = request.data.get('observacion', '')

        if not ids:
            return Response(
                {'error': 'El campo ids es requerido y no puede estar vacio.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not nuevo_estado:
            return Response(
                {'error': 'El campo estado es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        empleado = _obtener_empleado_actual(request.user)
        if empleado is None:
            return Response(
                {'error': 'El usuario no tiene un empleado asociado.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        encomiendas = Encomienda.objects.filter(id__in=ids)
        actualizadas = []
        errores = []

        for enc in encomiendas:
            try:
                enc.cambiar_estado(nuevo_estado, empleado, observacion)
                actualizadas.append(enc.id)
            except ValueError as exc:
                errores.append({'id': enc.id, 'error': str(exc)})

        ids_procesados = list(encomiendas.values_list('id', flat=True))
        no_encontrados = [i for i in ids if i not in ids_procesados]

        cache.delete(f'estadisticas_empleado_{request.user.id}')
        return Response(
            {
                'actualizadas': actualizadas,
                'errores': errores,
                'no_encontrados': no_encontrados,
                'total': len(actualizadas),
            }
        )


class RutaViewSet(viewsets.ReadOnlyModelViewSet):
    """Las rutas cambian poco: cachear el listado 15 minutos."""

    queryset = Ruta.objects.activas()
    serializer_class = RutaSerializer
    permission_classes = [EsEmpleadoActivo]

    @method_decorator(cache_page(CACHE_TTL))
    @method_decorator(vary_on_headers('Authorization'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
