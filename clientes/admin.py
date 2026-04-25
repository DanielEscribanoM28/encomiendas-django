from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nro_doc', 'nombres', 'apellidos', 'email', 'telefono', 'estado')
    search_fields = ('nro_doc', 'nombres', 'apellidos', 'email')
    list_filter = ('estado', 'tipo_doc')
