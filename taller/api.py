"""API JSON del taller. Autenticación por token (Authorization: Bearer <token>)."""
import json
from datetime import date, timedelta
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Max, Q
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from . import services
from .forms import (
    DetalleForm,
    OrdenForm,
    PropietarioForm,
    TipoServicioForm,
    VehiculoForm,
)
from .models import (
    Notificacion,
    OrdenServicio,
    Propietario,
    ProximoServicio,
    TipoServicio,
    Vehiculo,
)

SAL = "taller-api"


# ---------- Utilidades ----------

def _error(mensaje, estado=400, detalle=None):
    cuerpo = {"error": mensaje}
    if detalle:
        cuerpo["campos"] = detalle
    return JsonResponse(cuerpo, status=estado)


def _errores_form(form):
    return {
        campo: [e["message"] for e in lista]
        for campo, lista in form.errors.get_json_data().items()
    }


def _cuerpo(request):
    if not request.body:
        return {}
    try:
        datos = json.loads(request.body)
    except ValueError:
        raise ValueError("El cuerpo debe ser JSON válido.")
    if not isinstance(datos, dict):
        raise ValueError("El cuerpo debe ser un objeto JSON.")
    return datos


def api(*metodos, publica=False):
    """Valida método, token y JSON; convierte errores comunes en respuestas JSON."""

    def decorador(vista):
        @csrf_exempt
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if request.method not in metodos:
                return _error("Método no permitido.", 405)
            if not publica:
                cabecera = request.headers.get("Authorization", "")
                if not cabecera.startswith("Bearer "):
                    return _error("Falta el token de acceso.", 401)
                try:
                    datos = signing.loads(
                        cabecera[7:],
                        salt=SAL,
                        max_age=settings.API_TOKEN_HORAS * 3600,
                    )
                    request.user = get_user_model().objects.get(
                        pk=datos["u"], is_active=True
                    )
                except (signing.BadSignature, get_user_model().DoesNotExist):
                    return _error("Token inválido o vencido.", 401)
            try:
                request.datos = _cuerpo(request) if request.method != "GET" else {}
            except ValueError as e:
                return _error(str(e))
            try:
                return vista(request, *args, **kwargs)
            except ValidationError as e:
                return _error(" ".join(e.messages))

        return envoltura

    return decorador


def _texto(request, nombre):
    return request.GET.get(nombre, "").strip()


def _opcion(request, nombre, opciones):
    valor = _texto(request, nombre)
    return valor if valor in dict(opciones) else ""


def _fecha(request, nombre):
    try:
        return date.fromisoformat(_texto(request, nombre))
    except ValueError:
        return None


def _pagina(request, qs, serializar):
    try:
        tam = min(max(int(request.GET.get("tam", 15)), 1), 100)
        num = max(int(request.GET.get("pagina", 1)), 1)
    except ValueError:
        tam, num = 15, 1
    paginador = Paginator(qs, tam)
    try:
        pagina = paginador.page(num)
    except EmptyPage:
        pagina = paginador.page(paginador.num_pages)
    return JsonResponse({
        "total": paginador.count,
        "pagina": pagina.number,
        "paginas": paginador.num_pages,
        "resultados": [serializar(o) for o in pagina.object_list],
    })


def _guardar(form_clase, datos, instancia=None):
    """Valida con el ModelForm de siempre. En edición, parte de los valores actuales."""
    if instancia is not None:
        base = model_to_dict(instancia)
        base.update(datos)
        datos = base
    form = form_clase(datos, instance=instancia)
    if not form.is_valid():
        return None, _error("Datos no válidos.", 400, _errores_form(form))
    return form.save(), None


# ---------- Serializadores ----------

def s_propietario(p):
    return {
        "id": p.pk, "tipo": p.tipo, "nombre": p.nombre, "documento": p.documento,
        "telefono": p.telefono, "correo": p.correo, "direccion": p.direccion,
        "activo": p.activo, "whatsapp_url": p.whatsapp_url,
        "num_vehiculos": getattr(p, "num_vehiculos", None),
    }


def s_vehiculo(v):
    return {
        "id": v.pk, "propietario": v.propietario_id,
        "propietario_nombre": v.propietario.nombre, "tipo": v.tipo,
        "marca": v.marca, "modelo": v.modelo, "anio": v.anio, "placa": v.placa,
        "km_actual": v.km_actual, "fecha_ingreso": v.fecha_ingreso.isoformat(),
        "estado": v.estado, "nivel_uso": v.nivel_uso, "km_dia_real": v.km_dia_real,
        "observaciones": v.observaciones,
    }


def s_servicio(s):
    return {
        "id": s.pk, "nombre": s.nombre, "intervalo_km": s.intervalo_km,
        "intervalo_dias": s.intervalo_dias, "es_preventivo": s.es_preventivo,
        "activo": s.activo,
    }


def s_orden(o, detalle=False):
    datos = {
        "id": o.pk, "vehiculo": o.vehiculo_id, "placa": o.vehiculo.placa,
        "propietario": o.vehiculo.propietario.nombre,
        "fecha_ingreso": o.fecha_ingreso.isoformat(), "km_ingreso": o.km_ingreso,
        "motivo": o.motivo, "estado": o.estado,
        "estado_display": o.get_estado_display(),
        "siguiente": o.siguiente_display, "acepta_servicios": o.acepta_servicios,
    }
    if detalle:
        datos.update({
            "observaciones": o.observaciones,
            "fecha_cierre": o.fecha_cierre.isoformat() if o.fecha_cierre else None,
            "observaciones_cierre": o.observaciones_cierre,
            "servicios": [
                {"id": d.pk, "tipo_servicio": d.tipo_servicio_id,
                 "nombre": d.tipo_servicio.nombre, "descripcion": d.descripcion,
                 "observaciones": d.observaciones}
                for d in o.detalles.select_related("tipo_servicio")
            ],
        })
    return datos


def s_proximo(p):
    v, o, d = p.vehiculo, p.vehiculo.propietario, p.dias_restantes
    return {
        "id": p.pk,
        "vehiculo": {"id": v.pk, "placa": v.placa, "marca": v.marca, "modelo": v.modelo},
        "propietario": {"id": o.pk, "nombre": o.nombre, "telefono": o.telefono, "correo": o.correo},
        "servicio": p.tipo_servicio.nombre,
        "fecha_estimada": p.fecha_estimada.isoformat(),
        "km_estimado": p.km_estimado,
        "dias_restantes": d,
        "plazo": "vencido" if d < 0 else "proximo" if d <= 7 else "programado",
        "recordatorio": p.estado_recordatorio,
    }


def s_notificacion(n):
    v = n.proximo.vehiculo
    return {
        "id": n.pk, "tipo": n.tipo, "tipo_display": n.get_tipo_display(),
        "estado": n.estado, "estado_display": n.get_estado_display(),
        "mensaje": n.mensaje, "fecha_generada": n.fecha_generada.isoformat(),
        "canal": n.canal, "whatsapp_url": n.whatsapp_url,
        "placa": v.placa, "propietario": v.propietario.nombre,
        "servicio": n.proximo.tipo_servicio.nombre,
    }


# ---------- Acceso ----------

@api("POST", publica=True)
def login(request):
    usuario = authenticate(
        username=str(request.datos.get("username", "")),
        password=str(request.datos.get("password", "")),
    )
    if usuario is None:
        return _error("Usuario o contraseña incorrectos.", 401)
    token = signing.dumps({"u": usuario.pk}, salt=SAL)
    return JsonResponse({"token": token, "usuario": usuario.get_username()})


# ---------- Panel, alertas y notificaciones ----------

@api("GET")
def resumen(request):
    services.generar_recordatorios()
    datos = services.resumen(services.periodo_valido(request.GET.get("dias")))
    return JsonResponse({
        "dias": datos["dias"],
        "periodos": [{"dias": d, "etiqueta": e} for d, e in datos["periodos"]],
        "tarjetas": [{"titulo": t, "valor": v, "color": c} for t, v, c in datos["tarjetas"]],
        "proximos": [s_proximo(p) for p in datos["lista"]],
    })


@api("GET")
def alertas(request):
    services.generar_recordatorios()
    avisos = services.alertas()
    return JsonResponse({
        clave: [s_proximo(p) for p in avisos[clave]]
        for clave in ("vencidos", "proximos7", "proximos30")
    })


@api("GET")
def notificaciones(request):
    qs = Notificacion.objects.select_related(
        "proximo__vehiculo__propietario", "proximo__tipo_servicio"
    )
    q = _texto(request, "q")
    if q:
        qs = qs.filter(
            Q(proximo__vehiculo__placa__icontains=Vehiculo.normalizar(q))
            | Q(proximo__vehiculo__propietario__nombre__icontains=q)
            | Q(proximo__tipo_servicio__nombre__icontains=q)
        )
    estado = _opcion(request, "estado", Notificacion.ESTADOS)
    if estado:
        qs = qs.filter(estado=estado)
    tipo = _opcion(request, "tipo", Notificacion.TIPOS)
    if tipo:
        qs = qs.filter(tipo=tipo)
    return _pagina(request, qs, s_notificacion)


@api("POST")
def notificacion_enviada(request, pk):
    n = get_object_or_404(Notificacion, pk=pk)
    n.estado = "ENVIADA"
    n.save(update_fields=["estado"])
    return JsonResponse(s_notificacion(n))


# ---------- Propietarios ----------

@api("GET", "POST")
def propietarios(request):
    if request.method == "POST":
        datos = {"activo": True, "tipo": "INDIVIDUAL", **request.datos}
        p, err = _guardar(PropietarioForm, datos)
        return err or JsonResponse(s_propietario(p), status=201)

    qs = Propietario.objects.annotate(num_vehiculos=Count("vehiculos"))
    q = _texto(request, "q")
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) | Q(documento__icontains=q)
            | Q(telefono__icontains=q) | Q(correo__icontains=q)
        )
    tipo = _opcion(request, "tipo", Propietario.TIPOS)
    if tipo:
        qs = qs.filter(tipo=tipo)
    estado = _texto(request, "estado")
    if estado in ("activo", "inactivo"):
        qs = qs.filter(activo=(estado == "activo"))
    return _pagina(request, qs.order_by("nombre"), s_propietario)


@api("GET", "PUT")
def propietario(request, pk):
    p = get_object_or_404(Propietario, pk=pk)
    if request.method == "PUT":
        p, err = _guardar(PropietarioForm, request.datos, p)
        if err:
            return err

    vehiculos = p.vehiculos.select_related("propietario").annotate(
        num_ordenes=Count("ordenes"), ultima_visita=Max("ordenes__fecha_ingreso")
    )
    pendientes = ProximoServicio.objects.filter(
        vehiculo__propietario=p, estado="PENDIENTE"
    ).select_related("vehiculo__propietario", "tipo_servicio")
    datos = s_propietario(p)
    datos["vehiculos"] = [
        {**s_vehiculo(v), "num_ordenes": v.num_ordenes,
         "ultima_visita": v.ultima_visita.isoformat() if v.ultima_visita else None}
        for v in vehiculos
    ]
    datos["pendientes"] = [s_proximo(x) for x in pendientes]
    return JsonResponse(datos)


# ---------- Vehículos ----------

@api("GET", "POST")
def vehiculos(request):
    if request.method == "POST":
        v, err = _guardar(VehiculoForm, request.datos)
        return err or JsonResponse(s_vehiculo(v), status=201)

    qs = Vehiculo.objects.select_related("propietario")
    q = _texto(request, "q")
    if q:
        qs = qs.filter(
            Q(placa__icontains=Vehiculo.normalizar(q))
            | Q(propietario__nombre__icontains=q)
            | Q(marca__icontains=q) | Q(modelo__icontains=q)
        )
    tipo = _opcion(request, "tipo", Vehiculo.TIPOS)
    if tipo:
        qs = qs.filter(tipo=tipo)
    estado = _opcion(request, "estado", Vehiculo.ESTADOS)
    if estado:
        qs = qs.filter(estado=estado)
    propietario_id = _texto(request, "propietario")
    if propietario_id.isdigit():
        qs = qs.filter(propietario_id=int(propietario_id))
    return _pagina(request, qs.order_by("placa"), s_vehiculo)


@api("GET", "PUT")
def vehiculo(request, pk):
    v = get_object_or_404(Vehiculo.objects.select_related("propietario"), pk=pk)
    if request.method == "PUT":
        v, err = _guardar(VehiculoForm, request.datos, v)
        if err:
            return err
    datos = s_vehiculo(v)
    datos["historial"] = [s_orden(o) for o in v.ordenes.select_related("vehiculo__propietario")]
    datos["proximos"] = [
        s_proximo(p) for p in v.proximos.filter(estado="PENDIENTE")
        .select_related("vehiculo__propietario", "tipo_servicio")
    ]
    return JsonResponse(datos)


# ---------- Órdenes ----------

@api("GET", "POST")
def ordenes(request):
    if request.method == "POST":
        o, err = _guardar(OrdenForm, request.datos)
        return err or JsonResponse(s_orden(o, detalle=True), status=201)

    qs = OrdenServicio.objects.select_related("vehiculo__propietario")
    q = _texto(request, "q")
    if q.startswith("#") and q[1:].isdigit():
        qs = qs.filter(pk=int(q[1:]))
    elif q:
        filtro = (
            Q(vehiculo__placa__icontains=Vehiculo.normalizar(q))
            | Q(vehiculo__propietario__nombre__icontains=q)
            | Q(motivo__icontains=q)
        )
        if q.isdigit():
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro)
    estado = _opcion(request, "estado", OrdenServicio.ESTADOS)
    if estado:
        qs = qs.filter(estado=estado)
    desde, hasta = _fecha(request, "desde"), _fecha(request, "hasta")
    if desde:
        qs = qs.filter(fecha_ingreso__gte=desde)
    if hasta:
        qs = qs.filter(fecha_ingreso__lte=hasta)
    return _pagina(request, qs.order_by("-fecha_ingreso", "-id"), s_orden)


@api("GET")
def orden(request, pk):
    o = get_object_or_404(OrdenServicio.objects.select_related("vehiculo__propietario"), pk=pk)
    return JsonResponse(s_orden(o, detalle=True))


@api("POST")
def orden_servicio(request, pk):
    o = get_object_or_404(OrdenServicio, pk=pk)
    if not o.acepta_servicios:
        return _error("Esta orden ya no admite más servicios.", 409)
    form = DetalleForm(request.datos)
    if not form.is_valid():
        return _error("Datos no válidos.", 400, _errores_form(form))
    detalle = form.save(commit=False)
    detalle.orden = o
    detalle.save()
    return JsonResponse(s_orden(o, detalle=True), status=201)


@api("POST")
def orden_avanzar(request, pk):
    o = get_object_or_404(OrdenServicio, pk=pk)
    o = services.avanzar_orden(
        o, observaciones_cierre=str(request.datos.get("observaciones_cierre", ""))
    )
    return JsonResponse(s_orden(o, detalle=True))


# ---------- Catálogo de servicios ----------

@api("GET", "POST")
def servicios(request):
    if request.method == "POST":
        datos = {"es_preventivo": True, "activo": True, **request.datos}
        s, err = _guardar(TipoServicioForm, datos)
        return err or JsonResponse(s_servicio(s), status=201)
    return JsonResponse({"resultados": [s_servicio(s) for s in TipoServicio.objects.order_by("nombre")]})


@api("PUT")
def servicio(request, pk):
    s = get_object_or_404(TipoServicio, pk=pk)
    s, err = _guardar(TipoServicioForm, request.datos, s)
    return err or JsonResponse(s_servicio(s))
