from django.urls import path

from . import api

urlpatterns = [
    path("login/", api.login),
    path("resumen/", api.resumen),
    path("alertas/", api.alertas),
    path("notificaciones/", api.notificaciones),
    path("notificaciones/<int:pk>/enviada/", api.notificacion_enviada),
    path("propietarios/", api.propietarios),
    path("propietarios/<int:pk>/", api.propietario),
    path("vehiculos/", api.vehiculos),
    path("vehiculos/<int:pk>/", api.vehiculo),
    path("ordenes/", api.ordenes),
    path("ordenes/<int:pk>/", api.orden),
    path("ordenes/<int:pk>/servicios/", api.orden_servicio),
    path("ordenes/<int:pk>/avanzar/", api.orden_avanzar),
    path("servicios/", api.servicios),
    path("servicios/<int:pk>/", api.servicio),
]
