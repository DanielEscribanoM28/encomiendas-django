from datetime import timedelta
from decimal import Decimal
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from config.choices import EstadoEnvio, EstadoGeneral
from .querysets import EncomiendaQuerySet
from .validators import validar_codigo_encomienda, validar_peso_positivo


class Empleado(models.Model):
    codigo = models.CharField(max_length=10, unique=True, verbose_name='Codigo')
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    cargo = models.CharField(max_length=80, verbose_name='Cargo')
    email = models.EmailField(unique=True, verbose_name='Correo Electronico')
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name='Telefono')
    estado = models.IntegerField(
        choices=EstadoGeneral.choices,
        default=EstadoGeneral.ACTIVO,
        verbose_name='Estado',
    )
    fecha_ingreso = models.DateField(verbose_name='Fecha de Ingreso')
    rutas_asignadas = models.ManyToManyField('rutas.Ruta', blank=True, verbose_name='Rutas Asignadas')

    class Meta:
        db_table = 'empleados'
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['apellidos']

    def __str__(self):
        return f'{self.codigo} - {self.apellidos}, {self.nombres}'


class Encomienda(models.Model):
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Codigo',
        validators=[validar_codigo_encomienda],
    )
    descripcion = models.TextField(verbose_name='Descripcion')
    peso_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Peso (kg)',
        validators=[validar_peso_positivo],
    )
    volumen_cm3 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Volumen (cm3)',
    )
    remitente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        related_name='envios_como_remitente',
        verbose_name='Remitente',
    )
    destinatario = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        related_name='envios_como_destinatario',
        verbose_name='Destinatario',
    )
    ruta = models.ForeignKey(
        'rutas.Ruta',
        on_delete=models.PROTECT,
        related_name='encomiendas',
        verbose_name='Ruta',
    )
    empleado_registro = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name='encomiendas_registradas',
        verbose_name='Empleado que Registra',
    )
    estado = models.CharField(
        max_length=2,
        choices=EstadoEnvio.choices,
        default=EstadoEnvio.PENDIENTE,
        verbose_name='Estado',
    )
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Costo de Envio')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')
    fecha_entrega_est = models.DateField(null=True, blank=True, verbose_name='Fecha de Entrega Estimada')
    fecha_entrega_real = models.DateField(null=True, blank=True, verbose_name='Fecha de Entrega Real')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')

    objects = EncomiendaQuerySet.as_manager()

    class Meta:
        db_table = 'encomiendas'
        verbose_name = 'Encomienda'
        verbose_name_plural = 'Encomiendas'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f'{self.codigo} [{self.get_estado_display()}]'

    def clean(self):
        errors = {}

        if self.remitente_id and self.destinatario_id and self.remitente_id == self.destinatario_id:
            errors['destinatario'] = 'El destinatario no puede ser el mismo que el remitente.'

        hoy = timezone.now().date()
        if self.fecha_entrega_est and self.fecha_entrega_est < hoy:
            errors['fecha_entrega_est'] = 'La fecha de entrega estimada no puede ser en el pasado.'

        if self.fecha_entrega_real and self.fecha_entrega_est and self.fecha_entrega_real < self.fecha_entrega_est:
            errors['fecha_entrega_real'] = 'La fecha de entrega real no puede ser antes de la fecha estimada.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def esta_entregada(self):
        return self.estado == EstadoEnvio.ENTREGADO

    @property
    def esta_en_transito(self):
        return self.estado == EstadoEnvio.EN_TRANSITO

    @property
    def dias_en_transito(self):
        if not self.fecha_registro:
            return 0
        return (timezone.now().date() - self.fecha_registro.date()).days

    @property
    def tiene_retraso(self):
        if not self.fecha_entrega_est or self.esta_entregada:
            return False
        return timezone.now().date() > self.fecha_entrega_est

    @property
    def descripcion_corta(self):
        return self.descripcion[:50] + '...' if len(self.descripcion) > 50 else self.descripcion

    def cambiar_estado(self, nuevo_estado, empleado, observacion=''):
        if nuevo_estado == self.estado:
            raise ValueError(
                f'La encomienda ya se encuentra en estado {self.get_estado_display()}'
            )

        estado_anterior = self.estado
        self.estado = nuevo_estado

        if nuevo_estado == EstadoEnvio.ENTREGADO:
            self.fecha_entrega_real = timezone.now().date()

        self.save()

        HistorialEstado.objects.create(
            encomienda=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            observacion=observacion,
            empleado=empleado,
        )
        self._notificar_cambio_estado(estado_anterior, nuevo_estado, empleado)
        return self

    def _stats_dashboard(self):
        hoy = timezone.now().date()
        return {
            'total_activas': Encomienda.objects.activas().count(),
            'en_transito': Encomienda.objects.en_transito().count(),
            'con_retraso': Encomienda.objects.con_retraso().count(),
            'entregadas_hoy': Encomienda.objects.filter(
                estado=EstadoEnvio.ENTREGADO,
                fecha_entrega_real=hoy,
            ).count(),
        }

    def _notificar_cambio_estado(self, estado_anterior, estado_nuevo, empleado):
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        mensaje = {
            'encomienda_id': self.pk,
            'codigo': self.codigo,
            'estado_anterior': estado_anterior,
            'estado_nuevo': estado_nuevo,
            'empleado': str(empleado),
            'timestamp': timezone.now().isoformat(),
        }

        stats = self._stats_dashboard()

        async_to_sync(channel_layer.group_send)(
            'encomiendas_global',
            {'type': 'encomienda_estado_cambio', **mensaje},
        )
        async_to_sync(channel_layer.group_send)(
            f'encomienda_{self.pk}',
            {'type': 'encomienda_estado_cambio', **mensaje},
        )
        async_to_sync(channel_layer.group_send)(
            'dashboard',
            {'type': 'dashboard_actualizar', 'stats': stats},
        )
        async_to_sync(channel_layer.group_send)(
            'dashboard',
            {'type': 'encomienda_estado_cambio', **mensaje, 'stats': stats},
        )

    def calcular_costo(self):
        precio_por_kg_extra = Decimal('2.50')
        peso_base = Decimal('5.00')

        costo = self.ruta.precio_base
        if self.peso_kg > peso_base:
            costo += (self.peso_kg - peso_base) * precio_por_kg_extra
        return round(costo, 2)

    @classmethod
    def crear_con_costo_calculado(
        cls,
        remitente,
        destinatario,
        ruta,
        empleado,
        descripcion,
        peso_kg,
        **kwargs,
    ):
        codigo = f'ENC-{timezone.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}'
        fecha_est = timezone.now().date() + timedelta(days=ruta.dias_entrega)

        encomienda = cls(
            codigo=codigo,
            descripcion=descripcion,
            peso_kg=peso_kg,
            remitente=remitente,
            destinatario=destinatario,
            ruta=ruta,
            empleado_registro=empleado,
            fecha_entrega_est=fecha_est,
            **kwargs,
        )
        encomienda.costo_envio = encomienda.calcular_costo()
        encomienda.save()
        return encomienda


class HistorialEstado(models.Model):
    encomienda = models.ForeignKey(
        Encomienda,
        on_delete=models.CASCADE,
        related_name='historial',
        verbose_name='Encomienda',
    )
    estado_anterior = models.CharField(
        max_length=2,
        choices=EstadoEnvio.choices,
        verbose_name='Estado Anterior',
    )
    estado_nuevo = models.CharField(
        max_length=2,
        choices=EstadoEnvio.choices,
        verbose_name='Estado Nuevo',
    )
    observacion = models.TextField(blank=True, null=True, verbose_name='Observacion')
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name='cambios_estado',
        verbose_name='Empleado que registra',
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Cambio')

    class Meta:
        db_table = 'historial_estados'
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f'{self.encomienda.codigo}: {self.estado_anterior}->{self.estado_nuevo}'
