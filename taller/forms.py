
from django import forms

from .models import (
    DetalleServicio,
    OrdenServicio,
    Propietario,
    TipoServicio,
    Vehiculo,
)


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for campo in self.fields.values():
            widget = campo.widget

            if isinstance(widget, forms.CheckboxInput):
                clase = "form-check-input"
            elif isinstance(widget, forms.Select):
                clase = "form-select"
            else:
                clase = "form-control"

            widget.attrs["class"] = clase


class PropietarioForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Propietario
        fields = "__all__"


class VehiculoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = "__all__"
        widgets = {
            "fecha_ingreso": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # El km solo cambia al registrar una orden de servicio
            self.fields["km_actual"].disabled = True
            self.fields["km_actual"].help_text = (
                "Se actualiza al crear una nueva orden de servicio."
            )


class OrdenForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = OrdenServicio
        fields = [
            "vehiculo",
            "fecha_ingreso",
            "km_ingreso",
            "motivo",
            "observaciones",
        ]
        widgets = {
            "fecha_ingreso": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehiculo"].queryset = Vehiculo.objects.filter(
            estado="ACTIVO"
        )


class DetalleForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DetalleServicio
        fields = ["tipo_servicio", "descripcion", "observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_servicio"].queryset = TipoServicio.objects.filter(
            activo=True
        )


class TipoServicioForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = TipoServicio
        fields = [
            "nombre",
            "intervalo_km",
            "intervalo_dias",
            "es_preventivo",
            "activo",
        ]
        help_texts = {
            "es_preventivo": (
                "Si está marcado, al terminar una orden con este servicio "
                "se programa el siguiente mantenimiento."
            ),
            "activo": "Los servicios inactivos no aparecen al crear órdenes.",
        }
