
from django.contrib import admin

from .models import (
    Propietario,
    Vehiculo,
    TipoServicio,
    OrdenServicio,
    DetalleServicio,
    ProximoServicio,
    Notificacion,
)


@admin.register(Propietario)
class PropietarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "documento", "telefono", "correo", "activo")
    search_fields = ("nombre", "documento", "telefono", "correo")
    list_filter = ("activo",)


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = (
        "placa",
        "marca",
        "modelo",
        "anio",
        "propietario",
        "km_actual",
        "estado",
    )
    search_fields = ("placa", "marca", "modelo", "propietario__nombre")
    list_filter = ("tipo", "estado", "nivel_uso")


@admin.register(TipoServicio)
class TipoServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "intervalo_km", "intervalo_dias", "es_preventivo", "activo")
    search_fields = ("nombre",)
    list_filter = ("es_preventivo", "activo")


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vehiculo",
        "fecha_ingreso",
        "km_ingreso",
        "estado",
        "fecha_cierre",
    )
    search_fields = ("vehiculo__placa", "motivo")
    list_filter = ("estado", "fecha_ingreso")
    date_hierarchy = "fecha_ingreso"


@admin.register(DetalleServicio)
class DetalleServicioAdmin(admin.ModelAdmin):
    list_display = ("orden", "tipo_servicio", "descripcion")
    search_fields = ("orden__vehiculo__placa", "tipo_servicio__nombre", "descripcion")


@admin.register(ProximoServicio)
class ProximoServicioAdmin(admin.ModelAdmin):
    list_display = (
        "vehiculo",
        "tipo_servicio",
        "fecha_estimada",
        "km_estimado",
        "estado",
        "dias_restantes",
    )
    search_fields = ("vehiculo__placa", "tipo_servicio__nombre")
    list_filter = ("estado", "fecha_estimada")


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("proximo", "tipo", "fecha_generada", "canal", "estado")
    search_fields = ("mensaje", "proximo__vehiculo__placa")
    list_filter = ("tipo", "canal", "estado")
    date_hierarchy = "fecha_generada"
