from django.core.exceptions import ValidationError
import re

def validar_peso_positivo(value):
    """Verifica que el peso sea mayor estricto que cero."""
    if value <= 0:
        raise ValidationError('El peso debe ser mayor a 0.')

def validar_codigo_encomienda(value):
    """Verifica que el código de encomienda inicie con la estructura ENC-."""
    if not value.startswith('ENC-'):
        raise ValidationError('El código debe iniciar con "ENC-".')

def validar_nro_doc_dni(value):
    """Verifica que el DNI contenga exactamente 8 dígitos numéricos."""
    if not re.match(r'^\d{8}$', value):
        raise ValidationError('El número de documento DNI debe tener exactamente 8 dígitos.')
