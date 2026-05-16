import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def encomiendas_exception_handler(exc, context):
    """
    Handler global de errores para la API de encomiendas.
    Devuelve siempre el mismo formato:
    {
        'error': True,
        'code': 'VALIDATION_ERROR',
        'message': 'Descripcion legible del error',
        'detail': {...errores por campo...}
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_code = 'API_ERROR'
        message = 'Ha ocurrido un error procesando la solicitud.'

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_code = 'VALIDATION_ERROR'
            message = 'Los datos enviados contienen errores de validacion.'
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = 'AUTHENTICATION_REQUIRED'
            message = 'Se requiere autenticacion para acceder a este recurso.'
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            error_code = 'PERMISSION_DENIED'
            message = 'No tienes permiso para realizar esta accion.'
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            error_code = 'NOT_FOUND'
            message = 'El recurso solicitado no existe.'
        elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_code = 'RATE_LIMIT_EXCEEDED'
            message = 'Se excedio el limite de solicitudes. Intenta mas tarde.'

        response.data = {
            'error': True,
            'code': error_code,
            'message': message,
            'detail': response.data,
        }
        return response

    view_name = context.get('view').__class__.__name__ if context.get('view') else 'unknown'
    logger.error(
        f'Error no controlado en {view_name}: {exc}',
        exc_info=True,
    )
    return Response(
        {
            'error': True,
            'code': 'INTERNAL_ERROR',
            'message': 'Error interno del servidor.',
            'detail': None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class EstadoInvalidoError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = 'ESTADO_INVALIDO'
    default_detail = 'La transicion de estado no esta permitida.'


class EncomiendaYaEntregadaError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = 'YA_ENTREGADA'
    default_detail = 'La encomienda ya fue entregada y no puede modificarse.'
