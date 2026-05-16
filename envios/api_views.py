from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.pagination import ClientePagination
from clientes.models import Cliente
from rutas.models import Ruta
from .models import Empleado, Encomienda
from .serializers import (
    ClienteSerializer,
    EncomiendaDetailSerializer,
    EncomiendaSerializer,
    RutaSerializer,
)


def _obtener_empleado_actual(user):
    return Empleado.objects.filter(email=user.email).first()


@extend_schema(exclude=True)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def encomienda_list(request):
    if request.method == 'GET':
        qs = Encomienda.objects.con_relaciones()
        serializer = EncomiendaSerializer(
            qs,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)

    serializer = EncomiendaSerializer(
        data=request.data,
        context={'request': request},
    )
    if serializer.is_valid():
        empleado = _obtener_empleado_actual(request.user)
        if empleado is None:
            return Response(
                {'error': 'El usuario no tiene empleado asociado por email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save(empleado_registro=empleado)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(exclude=True)
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def encomienda_detail(request, pk):
    enc = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)

    if request.method == 'GET':
        return Response(EncomiendaDetailSerializer(enc).data)

    if request.method in ['PUT', 'PATCH']:
        serializer = EncomiendaSerializer(
            enc,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    enc.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(exclude=True),
    post=extend_schema(exclude=True),
)
class EncomiendaListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Encomienda.objects.con_relaciones()
        serializer = EncomiendaSerializer(
            qs,
            many=True,
            context={'request': request},
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = EncomiendaSerializer(
            data=request.data,
            context={'request': request},
        )
        if serializer.is_valid():
            empleado = _obtener_empleado_actual(request.user)
            if empleado is None:
                return Response(
                    {'error': 'El usuario no tiene empleado asociado por email.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.save(empleado_registro=empleado)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(exclude=True),
    put=extend_schema(exclude=True),
    patch=extend_schema(exclude=True),
    delete=extend_schema(exclude=True),
)
class EncomiendaDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)

    def get(self, request, pk):
        enc = self.get_object(pk)
        return Response(EncomiendaDetailSerializer(enc).data)

    def put(self, request, pk):
        enc = self.get_object(pk)
        serializer = EncomiendaSerializer(
            enc,
            data=request.data,
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        enc = self.get_object(pk)
        serializer = EncomiendaSerializer(
            enc,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        enc = self.get_object(pk)
        enc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(exclude=True),
    post=extend_schema(exclude=True),
)
class EncomiendaMixinListCreateView(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    generics.GenericAPIView,
):
    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        empleado = _obtener_empleado_actual(self.request.user)
        serializer.save(empleado_registro=empleado)


@extend_schema_view(
    get=extend_schema(exclude=True),
    put=extend_schema(exclude=True),
    patch=extend_schema(exclude=True),
    delete=extend_schema(exclude=True),
)
class EncomiendaMixinDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class EncomiendaListCreateView(generics.ListCreateAPIView):
    queryset = Encomienda.objects.con_relaciones()
    serializer_class = EncomiendaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        empleado = _obtener_empleado_actual(self.request.user)
        serializer.save(empleado_registro=empleado)


class EncomiendaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Encomienda.objects.con_relaciones()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EncomiendaDetailSerializer
        return EncomiendaSerializer


@extend_schema(
    summary='Listar clientes activos',
    description='Devuelve clientes activos para seleccionar remitente y destinatario.',
    tags=['Clientes'],
)
class ClienteListView(generics.ListAPIView):
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ClientePagination

    def get_queryset(self):
        return Cliente.objects.activos()


@extend_schema(
    summary='Listar rutas activas',
    description='Devuelve las rutas disponibles para registrar encomiendas.',
    tags=['Rutas'],
)
class RutaListView(generics.ListAPIView):
    serializer_class = RutaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Ruta.objects.activas()
