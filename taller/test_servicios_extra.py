from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings, TestCase

from . import services
from .models import (
    DetalleServicio,
    Notificacion,
    OrdenServicio,
    Propietario,
    ProximoServicio,
    TipoServicio,
    Vehiculo,
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BaseDatos(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("tester", password="x")
        self.prop = Propietario.objects.create(
            nombre="Ana Pérez", documento="123", telefono="5555-0000"
        )
        self.v = Vehiculo.objects.create(
            propietario=self.prop, marca="Honda", modelo="CB125",
            anio=2022, placa="M101AAA", km_actual=1000, nivel_uso="NORMAL",
        )
        self.aceite = TipoServicio.objects.create(
            nombre="Cambio de aceite", intervalo_km=3000, intervalo_dias=90
        )

    def proximo_en(self, dias):
        return ProximoServicio.objects.create(
            vehiculo=self.v, tipo_servicio=self.aceite,
            fecha_estimada=date.today() + timedelta(days=dias),
            km_estimado=4000,
        )


class PeriodoDelPanelTest(BaseDatos):
    def test_periodo_invalido_usa_30_dias(self):
        for valor in (None, "", "abc", "5", "-1"):
            self.assertEqual(services.periodo_valido(valor), 30)
        self.assertEqual(services.periodo_valido("90"), 90)

    def test_atendidos_depende_del_periodo(self):
        OrdenServicio.objects.create(
            vehiculo=self.v, km_ingreso=1000, motivo="x",
            fecha_ingreso=date.today() - timedelta(days=45),
            estado="ENTREGADO",
        )
        en_30 = dict((t, v) for t, v, _ in services.resumen(30)["tarjetas"])
        en_90 = dict((t, v) for t, v, _ in services.resumen(90)["tarjetas"])
        self.assertEqual(en_30["Vehículos atendidos (30 días)"], 0)
        self.assertEqual(en_90["Vehículos atendidos (90 días)"], 1)

    def test_vehiculos_registrados_cuenta_todos(self):
        self.v.estado = "INACTIVO"
        self.v.save()
        tarjetas = dict((t, v) for t, v, _ in services.resumen()["tarjetas"])
        self.assertEqual(tarjetas["Vehículos registrados"], 1)


class RecordatorioEnAlertasTest(BaseDatos):
    def test_mensaje_con_tildes(self):
        p = self.proximo_en(3)
        services.generar_recordatorios()
        n = Notificacion.objects.get(proximo=p)
        self.assertIn("vehículo", n.mensaje)
        self.assertIn("Comuníquese", n.mensaje)

    def test_actualizar_mensajes_no_duplica(self):
        p = self.proximo_en(3)
        services.generar_recordatorios()
        Notificacion.objects.filter(proximo=p).update(mensaje="texto viejo")
        self.assertEqual(services.actualizar_mensajes(), 1)
        self.assertEqual(Notificacion.objects.filter(proximo=p).count(), 1)
        call_command("generar_recordatorios", "--actualizar-mensajes")
        self.assertEqual(Notificacion.objects.filter(proximo=p).count(), 1)


class CierreDeOrdenTest(BaseDatos):
    def _orden_en_proceso(self):
        o = OrdenServicio.objects.create(
            vehiculo=self.v, km_ingreso=1200, motivo="Mantenimiento"
        )
        DetalleServicio.objects.create(orden=o, tipo_servicio=self.aceite)
        services.avanzar_orden(o)  # Recibido -> En proceso
        return o

    def test_guarda_observaciones_de_cierre(self):
        o = self._orden_en_proceso()
        services.avanzar_orden(o, observaciones_cierre="  Se cambió filtro  ")
        o.refresh_from_db()
        self.assertEqual(o.estado, "TERMINADO")
        self.assertEqual(o.observaciones_cierre, "Se cambió filtro")
        self.assertIsNotNone(o.fecha_cierre)
