from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from api.throttles import LoginRateThrottle
from envios.models import Empleado


class EncomiendaTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['username'] = user.username
        token['email'] = user.email

        empleado = Empleado.objects.filter(email=user.email).first()
        if empleado is not None:
            token['empleado_id'] = empleado.id
            token['empleado_cod'] = empleado.codigo
            token['cargo'] = empleado.cargo

        return token


class EncomiendaTokenView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]
    serializer_class = EncomiendaTokenSerializer


class LoginCookieView(APIView):
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        request=inline_serializer(
            name='LoginCookieRequest',
            fields={
                'username': serializers.CharField(),
                'password': serializers.CharField(),
            },
        ),
        responses=inline_serializer(
            name='LoginCookieResponse',
            fields={'message': serializers.CharField()},
        ),
        tags=['Auth'],
    )
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if not user:
            return Response({'error': 'Credenciales invalidas.'}, status=401)

        refresh = RefreshToken.for_user(user)
        response = Response({'message': 'Login exitoso.'})
        response.set_cookie(
            key='access_token',
            value=str(refresh.access_token),
            httponly=True,
            secure=True,
            samesite='Lax',
            max_age=3600,
        )
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite='Lax',
            max_age=604800,
        )
        return response


class LogoutCookieView(APIView):
    @extend_schema(
        request=None,
        responses=inline_serializer(
            name='LogoutCookieResponse',
            fields={'message': serializers.CharField()},
        ),
        tags=['Auth'],
    )
    def post(self, request):
        response = Response({'message': 'Logout exitoso.'})
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response
