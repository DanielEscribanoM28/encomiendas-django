import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from config.choices import EstadoEnvio


class EncomiendaConsumer(AsyncWebsocketConsumer):
    """Consumer global para notificaciones de encomiendas."""

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = 'encomiendas_global'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        stats = await self.get_estadisticas()
        await self.send(text_data=json.dumps({
            'tipo': 'conectado',
            'usuario': user.username,
            'stats': stats,
        }))

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'tipo': 'error',
                'mensaje': 'JSON invalido',
            }))
            return

        tipo = data.get('tipo')
        if tipo == 'ping':
            await self.send(text_data=json.dumps({'tipo': 'pong'}))
        elif tipo == 'solicitar_stats':
            stats = await self.get_estadisticas()
            await self.send(text_data=json.dumps({'tipo': 'stats', 'stats': stats}))
        elif tipo == 'suscribir_encomienda':
            enc_id = data.get('encomienda_id')
            if enc_id:
                await self.channel_layer.group_add(f'encomienda_{enc_id}', self.channel_name)
                await self.send(text_data=json.dumps({
                    'tipo': 'suscrito',
                    'encomienda_id': enc_id,
                }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def encomienda_estado_cambio(self, event):
        await self.send(text_data=json.dumps({
            'tipo': 'estado_cambio',
            'encomienda_id': event['encomienda_id'],
            'codigo': event['codigo'],
            'estado_anterior': event['estado_anterior'],
            'estado_nuevo': event['estado_nuevo'],
            'empleado': event['empleado'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def get_estadisticas(self):
        from .models import Encomienda

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


class EncomiendaDetalleConsumer(AsyncWebsocketConsumer):
    """Consumer para una encomienda especifica."""

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close(code=4001)
            return

        self.enc_pk = self.scope['url_route']['kwargs']['pk']
        self.group_name = f'encomienda_{self.enc_pk}'

        existe = await self.enc_existe(self.enc_pk)
        if not existe:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        enc_data = await self.get_encomienda(self.enc_pk)
        await self.send(text_data=json.dumps({
            'tipo': 'estado_actual',
            'encomienda': enc_data,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        return

    async def encomienda_estado_cambio(self, event):
        await self.send(text_data=json.dumps({
            'tipo': 'estado_cambio',
            'estado_anterior': event['estado_anterior'],
            'estado_nuevo': event['estado_nuevo'],
            'empleado': event['empleado'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def enc_existe(self, pk):
        from .models import Encomienda

        return Encomienda.objects.filter(pk=pk).exists()

    @database_sync_to_async
    def get_encomienda(self, pk):
        from .models import Encomienda

        enc = Encomienda.objects.con_relaciones().get(pk=pk)
        return {
            'id': enc.pk,
            'codigo': enc.codigo,
            'estado': enc.estado,
            'estado_display': enc.get_estado_display(),
            'remitente': enc.remitente.nombre_completo,
            'destinatario': enc.destinatario.nombre_completo,
            'ruta': str(enc.ruta),
        }


class DashboardConsumer(AsyncWebsocketConsumer):
    """Consumer del dashboard en tiempo real."""

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = 'dashboard'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        stats = await self.get_stats()
        await self.send(text_data=json.dumps({
            'tipo': 'stats_iniciales',
            'stats': stats,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def dashboard_actualizar(self, event):
        await self.send(text_data=json.dumps({
            'tipo': 'stats_actualizado',
            'stats': event['stats'],
        }))

    async def encomienda_estado_cambio(self, event):
        await self.send(text_data=json.dumps({
            'tipo': 'estado_cambio',
            'encomienda_id': event['encomienda_id'],
            'codigo': event['codigo'],
            'estado_anterior': event['estado_anterior'],
            'estado_nuevo': event['estado_nuevo'],
            'empleado': event['empleado'],
            'timestamp': event['timestamp'],
            'stats': event.get('stats'),
        }))

    @database_sync_to_async
    def get_stats(self):
        from .models import Encomienda

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
