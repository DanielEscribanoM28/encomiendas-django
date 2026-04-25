from django.db import models

from config.choices import EstadoGeneral, TipoDocumento
from envios.querysets import ClienteQuerySet


class Cliente(models.Model):
    tipo_doc = models.CharField(
        max_length=3,
        choices=TipoDocumento.choices,
        default=TipoDocumento.DNI,
        verbose_name='Tipo de Documento',
    )
    nro_doc = models.CharField(max_length=15, unique=True, verbose_name='Numero de Documento')
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name='Telefono')
    email = models.EmailField(blank=True, null=True, verbose_name='Correo Electronico')
    direccion = models.TextField(blank=True, null=True, verbose_name='Direccion')
    estado = models.IntegerField(
        choices=EstadoGeneral.choices,
        default=EstadoGeneral.ACTIVO,
        verbose_name='Estado',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')

    objects = ClienteQuerySet.as_manager()

    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f'{self.nro_doc} - {self.apellidos}, {self.nombres}'

    @property
    def nombre_completo(self):
        return f'{self.apellidos}, {self.nombres}'

    @property
    def esta_activo(self):
        return self.estado == EstadoGeneral.ACTIVO

    @property
    def total_encomiendas_enviadas(self):
        return self.envios_como_remitente.count()
