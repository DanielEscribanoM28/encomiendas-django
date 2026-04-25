from django.contrib import admin
from .models import Empleado, Encomienda, HistorialEstado

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombres', 'apellidos', 'cargo', 'estado')
    search_fields = ('codigo', 'nombres', 'apellidos')
    list_filter = ('estado', 'cargo')
    filter_horizontal = ('rutas_asignadas',)

@admin.register(Encomienda)
class EncomiendaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'remitente', 'destinatario', 'ruta', 'estado', 'fecha_registro')
    search_fields = ('codigo', 'descripcion', 'remitente__nombres', 'destinatario__nombres')
    list_filter = ('estado', 'ruta')
    readonly_fields = ('fecha_entrega_real',)

@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ('encomienda', 'estado_anterior', 'estado_nuevo', 'fecha_cambio', 'empleado')
    list_filter = ('estado_nuevo', 'fecha_cambio')
    search_fields = ('encomienda__codigo',)
