from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from clientes.models import Cliente
from config.choices import EstadoEnvio, EstadoGeneral, TipoDocumento
from envios.models import Empleado, Encomienda
from rutas.models import Ruta


class ModeloEncomiendasTestCase(TestCase):
    def setUp(self):
        self.remitente = Cliente.objects.create(
            tipo_doc=TipoDocumento.DNI,
            nro_doc='12345678',
            nombres='Carlos',
            apellidos='Ramirez',
            telefono='999111222',
            email='carlos@example.com',
            direccion='Lima',
            estado=EstadoGeneral.ACTIVO,
        )
        self.destinatario = Cliente.objects.create(
            tipo_doc=TipoDocumento.DNI,
            nro_doc='87654321',
            nombres='Ana',
            apellidos='Torres',
            telefono='999333444',
            email='ana@example.com',
            direccion='Trujillo',
            estado=EstadoGeneral.ACTIVO,
        )
        self.ruta = Ruta.objects.create(
            codigo='LIM-TRU',
            origen='Lima',
            destino='Trujillo',
            descripcion='Ruta principal',
            precio_base=Decimal('25.00'),
            dias_entrega=2,
            estado=EstadoGeneral.ACTIVO,
        )
        self.empleado = Empleado.objects.create(
            codigo='EMP001',
            nombres='Luis',
            apellidos='Perez',
            cargo='Supervisor',
            email='luis@example.com',
            telefono='999555666',
            estado=EstadoGeneral.ACTIVO,
            fecha_ingreso=timezone.now().date(),
        )

    def crear_encomienda(self, **overrides):
        data = {
            'codigo': 'ENC-20260425-AAAAAA',
            'descripcion': 'Documentos legales importantes',
            'peso_kg': Decimal('4.00'),
            'remitente': self.remitente,
            'destinatario': self.destinatario,
            'ruta': self.ruta,
            'empleado_registro': self.empleado,
            'estado': EstadoEnvio.PENDIENTE,
            'costo_envio': Decimal('25.00'),
            'fecha_entrega_est': timezone.now().date() + timedelta(days=2),
        }
        data.update(overrides)
        return Encomienda(**data)

    def test_clean_lanza_validation_error_con_datos_invalidos(self):
        encomienda = self.crear_encomienda(
            peso_kg=Decimal('-1.00'),
            remitente=self.remitente,
            destinatario=self.remitente,
            fecha_entrega_est=timezone.now().date() - timedelta(days=1),
        )

        with self.assertRaises(ValidationError) as error:
            encomienda.full_clean()

        self.assertIn('peso_kg', error.exception.message_dict)
        self.assertIn('destinatario', error.exception.message_dict)
        self.assertIn('fecha_entrega_est', error.exception.message_dict)

    def test_save_llama_full_clean(self):
        encomienda = self.crear_encomienda(destinatario=self.remitente)

        with self.assertRaises(ValidationError):
            encomienda.save()

    def test_propiedades_de_cliente(self):
        self.crear_encomienda().save()

        self.assertEqual(self.remitente.nombre_completo, 'Ramirez, Carlos')
        self.assertTrue(self.remitente.esta_activo)
        self.assertEqual(self.remitente.total_encomiendas_enviadas, 1)

    def test_propiedades_de_encomienda(self):
        encomienda = self.crear_encomienda(
            descripcion='x' * 60,
            estado=EstadoEnvio.EN_TRANSITO,
        )
        encomienda.save()
        Encomienda.objects.filter(pk=encomienda.pk).update(
            fecha_entrega_est=timezone.now().date() - timedelta(days=1)
        )
        encomienda.refresh_from_db()

        self.assertFalse(encomienda.esta_entregada)
        self.assertTrue(encomienda.esta_en_transito)
        self.assertTrue(encomienda.tiene_retraso)
        self.assertTrue(encomienda.descripcion_corta.endswith('...'))
        self.assertGreaterEqual(encomienda.dias_en_transito, 0)

    def test_cambiar_estado_actualiza_y_crea_historial(self):
        encomienda = self.crear_encomienda()
        encomienda.save()

        encomienda.cambiar_estado(
            nuevo_estado=EstadoEnvio.EN_TRANSITO,
            empleado=self.empleado,
            observacion='Salida de agencia',
        )

        encomienda.refresh_from_db()
        self.assertEqual(encomienda.estado, EstadoEnvio.EN_TRANSITO)
        self.assertEqual(encomienda.historial.count(), 1)
        self.assertEqual(encomienda.historial.first().estado_nuevo, EstadoEnvio.EN_TRANSITO)

    def test_crear_con_costo_calculado(self):
        encomienda = Encomienda.crear_con_costo_calculado(
            remitente=self.remitente,
            destinatario=self.destinatario,
            ruta=self.ruta,
            empleado=self.empleado,
            descripcion='Paquete de ropa',
            peso_kg=Decimal('7.00'),
            observaciones='Fragil',
        )

        self.assertTrue(encomienda.codigo.startswith('ENC-'))
        self.assertEqual(encomienda.costo_envio, Decimal('30.00'))
        self.assertEqual(
            encomienda.fecha_entrega_est,
            timezone.now().date() + timedelta(days=self.ruta.dias_entrega),
        )

    def test_managers_y_encadenamiento(self):
        Encomienda.crear_con_costo_calculado(
            remitente=self.remitente,
            destinatario=self.destinatario,
            ruta=self.ruta,
            empleado=self.empleado,
            descripcion='Paquete 1',
            peso_kg=Decimal('3.00'),
        )
        encomienda_2 = Encomienda.crear_con_costo_calculado(
            remitente=self.remitente,
            destinatario=self.destinatario,
            ruta=self.ruta,
            empleado=self.empleado,
            descripcion='Paquete 2',
            peso_kg=Decimal('6.00'),
        )
        encomienda_2.cambiar_estado(EstadoEnvio.EN_TRANSITO, self.empleado)

        self.assertEqual(Cliente.objects.activos().count(), 2)
        self.assertEqual(Cliente.objects.buscar('Ramir').count(), 1)
        self.assertEqual(Ruta.objects.activas().por_origen('Lima').count(), 1)
        self.assertEqual(Encomienda.objects.pendientes().count(), 1)
        self.assertEqual(Encomienda.objects.activas().por_ruta(self.ruta).count(), 2)
        self.assertEqual(Encomienda.objects.en_transito_por_ruta(self.ruta).count(), 1)
