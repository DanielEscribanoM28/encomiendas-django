import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from config.choices import EstadoGeneral
from envios.models import Empleado


@pytest.fixture
def api_client():
    """Cliente de API sin autenticacion."""

    return APIClient()


@pytest.fixture
def user(db):
    """Usuario de prueba con empleado asociado por email."""

    user = User.objects.create_user(
        username='test_empleado',
        email='empleado@encomiendas.pe',
        password='test1234',
    )
    Empleado.objects.create(
        codigo='EMP-TEST',
        nombres='Empleado',
        apellidos='Prueba',
        cargo='Operador de Envios',
        email=user.email,
        estado=EstadoGeneral.ACTIVO,
        fecha_ingreso='2026-01-01',
    )
    return user


@pytest.fixture
def auth_client(api_client, user):
    """Cliente de API con JWT valido."""

    refresh = RefreshToken.for_user(user)
    api_client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}',
    )
    return api_client
