import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from . import services
from .models import Notificacion, Propietario, ProximoServicio, TipoServicio, Vehiculo


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ApiBase(TestCase):
    def setUp(self):
        get_user_model().objects.create_user("tester", password="secreto")
        r = self.client.post("/api/login/", json.dumps({"username": "tester", "password": "secreto"}), content_type="application/json")
        self.token = r.json()["token"]
        self.h = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.prop = Propietario.objects.create(nombre="Ana Pérez", documento="123", telefono="5555-0000")
        self.v = Vehiculo.objects.create(propietario=self.prop, marca="Honda", modelo="CB125", anio=2022, placa="M101AAA", km_actual=1000)
        self.aceite = TipoServicio.objects.create(nombre="Cambio de aceite", intervalo_km=3000, intervalo_dias=90)

    def get(self, url, **kw):
        return self.client.get(url, **self.h, **kw)

    def send(self, metodo, url, datos=None):
        return getattr(self.client, metodo)(url, json.dumps(datos or {}), content_type="application/json", **self.h)


class AccesoTest(ApiBase):
    def test_login_incorrecto(self):
        r = self.client.post("/api/login/", json.dumps({"username": "tester", "password": "mal"}), content_type="application/json")
        self.assertEqual(r.status_code, 401)

    def test_sin_token_o_token_falso(self):
        self.assertEqual(self.client.get("/api/vehiculos/").status_code, 401)
        r = self.client.get("/api/vehiculos/", HTTP_AUTHORIZATION="Bearer falso")
        self.assertEqual(r.status_code, 401)

    def test_json_invalido(self):
        r = self.client.post("/api/propietarios/", "{no", content_type="application/json", **self.h)
        self.assertEqual(r.status_code, 400)

    def test_cors(self):
        r = self.client.options("/api/vehiculos/", HTTP_ORIGIN="http://localhost:5173")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r["Access-Control-Allow-Origin"], "http://localhost:5173")


class CrudTest(ApiBase):
    def test_propietario_crear_y_editar(self):
        r = self.send("post", "/api/propietarios/", {"nombre": "Luis", "documento": "999", "tipo": "INDIVIDUAL", "telefono": "5555-1111"})
        self.assertEqual(r.status_code, 201)
        pk = r.json()["id"]
        self.assertTrue(r.json()["activo"])
        r = self.send("put", f"/api/propietarios/{pk}/", {"telefono": "4444-1111"})
        self.assertEqual(r.json()["telefono"], "4444-1111")
        self.assertEqual(r.json()["nombre"], "Luis")

    def test_propietario_exige_contacto(self):
        r = self.send("post", "/api/propietarios/", {"nombre": "Luis", "documento": "999"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("teléfono o un correo", json.dumps(r.json(), ensure_ascii=False))

    def test_placa_unica(self):
        r = self.send("post", "/api/vehiculos/", {
            "propietario": self.prop.pk, "tipo": "MOTOCICLETA", "marca": "X", "modelo": "Y",
            "anio": 2020, "placa": "M101AAA", "km_actual": 0, "estado": "ACTIVO", "nivel_uso": "NORMAL",
            "fecha_ingreso": date.today().isoformat()})
        self.assertEqual(r.status_code, 400)
        self.assertIn("placa", r.json()["campos"])

    def test_catalogo(self):
        r = self.send("post", "/api/servicios/", {"nombre": "Alineación", "intervalo_km": 10000, "intervalo_dias": 180})
        self.assertEqual(r.status_code, 201)
        r = self.send("put", f"/api/servicios/{r.json()['id']}/", {"intervalo_km": 8000})
        self.assertEqual(r.json()["intervalo_km"], 8000)
        self.assertTrue(r.json()["activo"])
        self.assertEqual(len(self.get("/api/servicios/").json()["resultados"]), 2)

    def test_busqueda_vehiculos(self):
        self.assertEqual(self.get("/api/vehiculos/?q=m-101 aaa").json()["total"], 1)
        self.assertEqual(self.get("/api/vehiculos/?q=zzz").json()["total"], 0)


class OrdenesTest(ApiBase):
    def crear(self, km=1200):
        return self.send("post", "/api/ordenes/", {
            "vehiculo": self.v.pk, "fecha_ingreso": date.today().isoformat(),
            "km_ingreso": km, "motivo": "Mantenimiento"})

    def test_km_menor_rechazado(self):
        r = self.crear(km=500)
        self.assertEqual(r.status_code, 400)
        self.assertIn("km_ingreso", r.json()["campos"])

    def test_una_orden_activa(self):
        self.assertEqual(self.crear().status_code, 201)
        self.assertEqual(self.crear().status_code, 400)

    def test_flujo_completo(self):
        pk = self.crear().json()["id"]
        r = self.send("post", f"/api/ordenes/{pk}/servicios/", {"tipo_servicio": self.aceite.pk})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["servicios"][0]["nombre"], "Cambio de aceite")
        self.send("post", f"/api/ordenes/{pk}/avanzar/")
        r = self.send("post", f"/api/ordenes/{pk}/avanzar/", {"observaciones_cierre": "  Todo bien "})
        self.assertEqual(r.json()["estado"], "TERMINADO")
        self.assertEqual(r.json()["observaciones_cierre"], "Todo bien")
        self.assertEqual(r.json()["acepta_servicios"], False)
        r = self.send("post", f"/api/ordenes/{pk}/servicios/", {"tipo_servicio": self.aceite.pk})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(ProximoServicio.objects.filter(estado="PENDIENTE").count(), 1)
        self.assertEqual(self.get(f"/api/vehiculos/{self.v.pk}/").json()["historial"][0]["id"], pk)


class AlertasTest(ApiBase):
    def proximo(self, dias):
        return ProximoServicio.objects.create(
            vehiculo=self.v, tipo_servicio=self.aceite,
            fecha_estimada=date.today() + timedelta(days=dias), km_estimado=4000)

    def test_grupos_y_recordatorios(self):
        self.proximo(-2); self.proximo(3); self.proximo(20)
        r = self.get("/api/alertas/").json()
        self.assertEqual([len(r[k]) for k in ("vencidos", "proximos7", "proximos30")], [1, 1, 1])
        self.assertEqual(r["vencidos"][0]["plazo"], "vencido")
        self.assertEqual(Notificacion.objects.count(), 2)

    def test_resumen_y_periodo_invalido(self):
        self.proximo(3)
        r = self.get("/api/resumen/?dias=abc").json()
        self.assertEqual(r["dias"], 30)
        self.assertEqual(len(r["proximos"]), 1)
        self.assertEqual(r["tarjetas"][0]["valor"], 1)

    def test_marcar_enviada(self):
        self.proximo(3)
        services.generar_recordatorios()
        n = Notificacion.objects.get()
        r = self.send("post", f"/api/notificaciones/{n.pk}/enviada/")
        self.assertEqual(r.json()["estado"], "ENVIADA")
        self.assertEqual(self.get("/api/notificaciones/?estado=GENERADA").json()["total"], 0)
