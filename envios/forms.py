from django import forms

from clientes.models import Cliente
from config.choices import EstadoGeneral
from rutas.models import Ruta

from .models import Encomienda


class EncomiendaForm(forms.ModelForm):
    """Formulario para registrar una nueva encomienda."""

    class Meta:
        model = Encomienda
        fields = [
            'codigo',
            'descripcion',
            'peso_kg',
            'volumen_cm3',
            'remitente',
            'destinatario',
            'ruta',
            'costo_envio',
            'fecha_entrega_est',
            'observaciones',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'peso_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'volumen_cm3': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'remitente': forms.Select(attrs={'class': 'form-select'}),
            'destinatario': forms.Select(attrs={'class': 'form-select'}),
            'ruta': forms.Select(attrs={'class': 'form-select'}),
            'costo_envio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fecha_entrega_est': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'codigo': 'Codigo de encomienda',
            'peso_kg': 'Peso (kg)',
            'volumen_cm3': 'Volumen (cm3)',
            'fecha_entrega_est': 'Fecha estimada de entrega',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar solo clientes activos
        self.fields['remitente'].queryset = Cliente.objects.filter(estado=EstadoGeneral.ACTIVO)
        self.fields['destinatario'].queryset = Cliente.objects.filter(estado=EstadoGeneral.ACTIVO)
        # Mostrar solo rutas activas
        self.fields['ruta'].queryset = Ruta.objects.filter(estado=EstadoGeneral.ACTIVO)

    def clean(self):
        """Validaciones adicionales a nivel de formulario."""
        cleaned = super().clean()
        remitente = cleaned.get('remitente')
        destinatario = cleaned.get('destinatario')

        if remitente and destinatario and remitente == destinatario:
            raise forms.ValidationError(
                'El remitente y el destinatario no pueden ser la misma persona.'
            )

        return cleaned
