from django.contrib import admin
from django.utils.html import format_html

from config.choices import EstadoEnvio

from .models import Empleado, Encomienda, HistorialEstado


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombres', 'apellidos', 'cargo', 'estado')
    search_fields = ('codigo', 'nombres', 'apellidos')
    list_filter = ('estado', 'cargo')
    filter_horizontal = ('rutas_asignadas',)


@admin.register(Encomienda)
class EncomiendaAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'remitente_nombre',
        'destinatario_nombre',
        'ruta',
        'estado_badge',
        'peso_kg',
        'fecha_registro',
    )
    list_filter = ('estado', 'ruta', 'fecha_registro')
    search_fields = (
        'codigo',
        'remitente__apellidos',
        'destinatario__apellidos',
        'remitente__nro_doc',
    )
    readonly_fields = ('fecha_registro', 'fecha_entrega_real')
    fieldsets = (
        ('Datos principales', {
            'fields': ('codigo', 'descripcion', 'peso_kg', 'volumen_cm3'),
        }),
        ('Participantes y ruta', {
            'fields': ('remitente', 'destinatario', 'ruta', 'empleado_registro'),
        }),
        ('Estado y fechas', {
            'fields': (
                'estado',
                'costo_envio',
                'fecha_registro',
                'fecha_entrega_est',
                'fecha_entrega_real',
            ),
        }),
        ('Notas', {
            'classes': ('collapse',),
            'fields': ('observaciones',),
        }),
    )

    def remitente_nombre(self, obj):
        return obj.remitente.nombre_completo

    remitente_nombre.short_description = 'Remitente'

    def destinatario_nombre(self, obj):
        return obj.destinatario.nombre_completo

    destinatario_nombre.short_description = 'Destinatario'

    def estado_badge(self, obj):
        colores = {
            EstadoEnvio.PENDIENTE: '#6c757d',
            EstadoEnvio.EN_TRANSITO: '#0d6efd',
            EstadoEnvio.EN_DESTINO: '#fd7e14',
            EstadoEnvio.ENTREGADO: '#198754',
            EstadoEnvio.DEVUELTO: '#dc3545',
        }
        color = colores.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background:{}; color:#fff; padding:4px 8px; border-radius:12px;">{}</span>',
            color,
            obj.get_estado_display(),
        )

    estado_badge.short_description = 'Estado'


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ('encomienda', 'estado_anterior', 'estado_nuevo', 'fecha_cambio', 'empleado')
    readonly_fields = ('encomienda', 'estado_anterior', 'estado_nuevo', 'empleado', 'fecha_cambio')
    list_filter = ('estado_nuevo', 'fecha_cambio')
    ordering = ('-fecha_cambio',)
    search_fields = ('encomienda__codigo',)
