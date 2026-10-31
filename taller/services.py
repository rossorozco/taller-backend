
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    Notificacion,
    OrdenServicio,
    ProximoServicio,
    Vehiculo,
)


# ---------- Estimacion ----------

def calcular_proximo(vehiculo, tipo, fecha, km):
    """Calcula el proximo servicio por tiempo y kilometraje."""
    km_por_dia = vehiculo.km_por_dia
    if km_por_dia <= 0:
        raise ValidationError("El kilometraje diario debe ser mayor que cero.")

    dias_por_km = tipo.intervalo_km / km_por_dia
    dias = max(1, int(min(tipo.intervalo_dias, dias_por_km)))

    return fecha + timedelta(days=dias), km + tipo.intervalo_km


def reajustar_pendientes(vehiculo):
    """Recalcula la fecha de los servicios pendientes con el uso real.

    Se llama cuando el vehiculo vuelve al taller y se actualiza su
    kilometraje. Cada pendiente conserva su punto de partida (fecha y
    km de la orden que lo origino) y solo cambia la velocidad estimada.
    """
    pendientes = vehiculo.proximos.filter(
        estado="PENDIENTE", detalle_origen__isnull=False
    ).select_related("tipo_servicio", "detalle_origen__orden")

    for proximo in pendientes:
        origen = proximo.detalle_origen.orden
        fecha, _ = calcular_proximo(
            vehiculo,
            proximo.tipo_servicio,
            origen.fecha_ingreso,
            origen.km_ingreso,
        )
        if fecha != proximo.fecha_estimada:
            proximo.fecha_estimada = fecha
            proximo.save(update_fields=["fecha_estimada"])


# ---------- Ordenes ----------

@transaction.atomic
def avanzar_orden(orden, observaciones_cierre=""):
    """Avanza una orden al siguiente estado permitido.

    Al pasar a *Terminado* se puede registrar la información de cierre
    (trabajo realizado, repuestos, recomendaciones).
    """
    orden = (
        OrdenServicio.objects.select_for_update()
        .select_related("vehiculo")
        .get(pk=orden.pk)
    )

    siguiente = OrdenServicio.SIGUIENTE.get(orden.estado)
    if not siguiente:
        raise ValidationError(
            "La orden ya fue entregada y es de solo lectura."
        )

    if siguiente == "TERMINADO":
        detalles = list(
            orden.detalles.select_related("tipo_servicio")
        )
        if not detalles:
            raise ValidationError(
                "Agregue al menos un servicio antes de terminar la orden."
            )

        orden.fecha_cierre = date.today()
        if observaciones_cierre and observaciones_cierre.strip():
            orden.observaciones_cierre = observaciones_cierre.strip()

        for detalle in detalles:
            if detalle.tipo_servicio.es_preventivo:
                _crear_proximo(orden, detalle)

    orden.estado = siguiente
    orden.save()
    return orden


def _crear_proximo(orden, detalle):
    """Programa el siguiente mantenimiento preventivo."""
    vehiculo = orden.vehiculo
    tipo = detalle.tipo_servicio

    ProximoServicio.objects.filter(
        vehiculo=vehiculo,
        tipo_servicio=tipo,
        estado="PENDIENTE",
    ).update(estado="CUMPLIDO")

    fecha, km = calcular_proximo(
        vehiculo,
        tipo,
        orden.fecha_ingreso,
        orden.km_ingreso,
    )

    return ProximoServicio.objects.create(
        vehiculo=vehiculo,
        tipo_servicio=tipo,
        detalle_origen=detalle,
        fecha_estimada=fecha,
        km_estimado=km,
    )


# ---------- Alertas y resumen ----------

def _pendientes():
    return (
        ProximoServicio.objects.filter(estado="PENDIENTE")
        .select_related("vehiculo__propietario", "tipo_servicio")
        .prefetch_related("notificaciones")
        .order_by("fecha_estimada")
    )


def alertas():
    hoy = date.today()
    pendientes = _pendientes()

    return {
        "vencidos": pendientes.filter(fecha_estimada__lt=hoy),
        "proximos7": pendientes.filter(
            fecha_estimada__gte=hoy,
            fecha_estimada__lte=hoy + timedelta(days=7),
        ),
        "proximos30": pendientes.filter(
            fecha_estimada__gt=hoy + timedelta(days=7),
            fecha_estimada__lte=hoy + timedelta(days=30),
        ),
    }


PERIODOS = [
    (7, "7 días"),
    (30, "30 días"),
    (90, "90 días"),
    (365, "1 año"),
]
PERIODO_POR_DEFECTO = 30


def periodo_valido(valor):
    """Devuelve un período permitido (en días); si no es válido, 30."""
    try:
        dias = int(valor)
    except (TypeError, ValueError):
        return PERIODO_POR_DEFECTO
    return dias if dias in dict(PERIODOS) else PERIODO_POR_DEFECTO


def resumen(dias=PERIODO_POR_DEFECTO):
    """Datos del panel principal. `dias` es el período de los vehículos atendidos."""
    hoy = date.today()
    dias = periodo_valido(dias)
    etiqueta = dict(PERIODOS)[dias]
    avisos = alertas()

    atendidos = (
        OrdenServicio.objects.filter(
            fecha_ingreso__gte=hoy - timedelta(days=dias)
        )
        .values("vehiculo")
        .distinct()
        .count()
    )

    tarjetas = [
        ("Vehículos registrados", Vehiculo.objects.count(), "primary"),
        ("Servicios próximos (7 días)", avisos["proximos7"].count(), "warning"),
        ("Servicios vencidos", avisos["vencidos"].count(), "danger"),
        (f"Vehículos atendidos ({etiqueta})", atendidos, "success"),
        (
            "Órdenes en proceso",
            OrdenServicio.objects.filter(estado="EN_PROCESO").count(),
            "secondary",
        ),
    ]

    lista = _pendientes().filter(
        fecha_estimada__lte=hoy + timedelta(days=30)
    )

    return {
        "tarjetas": tarjetas,
        "lista": lista,
        "dias": dias,
        "periodos": PERIODOS,
    }


# ---------- Recordatorios ----------

def _mensaje(proximo, tipo):
    vehiculo = proximo.vehiculo
    servicio = proximo.tipo_servicio.nombre.lower()

    texto = (
        f"Estimado cliente {vehiculo.propietario.nombre}: "
        f"le recordamos que su vehículo {vehiculo.marca} "
        f"{vehiculo.modelo} (placa {vehiculo.placa}) "
    )

    if tipo == "VENCIDO":
        texto += (
            f"tenía programado su servicio de {servicio} "
            f"para el {proximo.fecha_estimada:%d/%m/%Y} "
            "y ya está vencido. "
        )
    else:
        texto += (
            f"tiene próximo su servicio de {servicio} "
            f"(fecha estimada: {proximo.fecha_estimada:%d/%m/%Y}). "
        )

    return texto + "Comuníquese con el taller para programar su cita."


def actualizar_mensajes():
    """Reescribe el texto de los recordatorios ya generados (sin duplicar)."""
    cambiados = 0
    for n in Notificacion.objects.select_related(
        "proximo__vehiculo__propietario", "proximo__tipo_servicio"
    ):
        nuevo = _mensaje(n.proximo, n.tipo)
        if n.mensaje != nuevo:
            n.mensaje = nuevo
            n.save(update_fields=["mensaje"])
            cambiados += 1
    return cambiados


@transaction.atomic
def generar_recordatorios():
    """Crea recordatorios pendientes sin duplicar sus tipos."""
    hoy = date.today()
    nuevas = 0

    pendientes = _pendientes().filter(
        fecha_estimada__lte=hoy + timedelta(days=7)
    )

    for proximo in pendientes:
        dias = (proximo.fecha_estimada - hoy).days

        if dias < 0:
            tipos = ["VENCIDO"]
        elif dias == 0:
            tipos = ["UN_DIA"]
        elif dias == 1:
            tipos = ["UN_DIA"]
        elif dias <= 7:
            tipos = ["SIETE_DIAS"]
        else:
            continue

        for tipo in tipos:
            _, creada = Notificacion.objects.get_or_create(
                proximo=proximo,
                tipo=tipo,
                defaults={"mensaje": _mensaje(proximo, tipo)},
            )
            if creada:
                nuevas += 1

    return nuevas
