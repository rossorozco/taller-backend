from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from . import services
from .models import (DetalleServicio, OrdenServicio, Propietario, ProximoServicio, TipoServicio, Vehiculo)


class ReglasNegocioTest(TestCase):
    def setUp(self):
        self.prop = Propietario.objects.create(nombre="Ana", documento="1", telefono="5555-0000")
        self.v = Vehiculo.objects.create(propietario=self.prop, marca="Honda", modelo="CB", anio=2022,
                                         placa="m 123 abc", km_actual=1000, nivel_uso="NORMAL")
        self.aceite = TipoServicio.objects.create(nombre="Aceite", intervalo_km=3000, intervalo_dias=90)

    def test_placa_se_normaliza_y_no_se_duplica(self):
        self.assertEqual(self.v.placa, "M123ABC")
        otro = Vehiculo(propietario=self.prop, marca="X", modelo="Y", anio=2020, placa="M-123-ABC")
        with self.assertRaises(ValidationError):
            otro.full_clean()

    def test_km_menor_es_rechazado(self):
        with self.assertRaises(ValidationError):
            OrdenServicio(vehiculo=self.v, km_ingreso=500, motivo="x").full_clean()

    def test_una_sola_orden_activa(self):
        OrdenServicio.objects.create(vehiculo=self.v, km_ingreso=1000, motivo="a")
        with self.assertRaises(ValidationError):
            OrdenServicio(vehiculo=self.v, km_ingreso=1100, motivo="b").full_clean()

    def test_estimacion_segun_uso(self):
        esperado = {"BAJO": 90, "NORMAL": 75, "ALTO": 37}
        for uso, dias in esperado.items():
            self.v.nivel_uso = uso
            fecha, km = services.calcular_proximo(self.v, self.aceite, date(2026, 1, 1), 1000)
            self.assertEqual(fecha, date(2026, 1, 1) + timedelta(days=dias))
            self.assertEqual(km, 4000)

    def test_orden_sin_servicios_no_termina(self):
        o = OrdenServicio.objects.create(vehiculo=self.v, km_ingreso=1000, motivo="a")
        services.avanzar_orden(o)                       # En proceso
        with self.assertRaises(ValidationError):
            services.avanzar_orden(o)                   # Terminado sin detalles

    def test_terminar_crea_proximo_y_reemplaza_el_anterior(self):
        for km in (1000, 1500):
            o = OrdenServicio.objects.create(vehiculo=self.v, km_ingreso=km, motivo="Mant")
            DetalleServicio.objects.create(orden=o, tipo_servicio=self.aceite)
            for _ in range(3):
                services.avanzar_orden(o)
        self.assertEqual(ProximoServicio.objects.filter(estado="PENDIENTE").count(), 1)
        self.assertEqual(ProximoServicio.objects.filter(estado="CUMPLIDO").count(), 1)

    def test_recordatorios_sin_duplicados(self):
        ProximoServicio.objects.create(vehiculo=self.v, tipo_servicio=self.aceite, km_estimado=4000,
                                       fecha_estimada=date.today() + timedelta(days=3))
        self.assertEqual(services.generar_recordatorios(), 1)
        self.assertEqual(services.generar_recordatorios(), 0)

    def test_vencido_aparece_en_alertas(self):
        ProximoServicio.objects.create(vehiculo=self.v, tipo_servicio=self.aceite, km_estimado=4000,
                                       fecha_estimada=date.today() - timedelta(days=2))
        self.assertEqual(services.alertas()["vencidos"].count(), 1)

    def test_reajusta_pendiente_con_uso_real(self):
        base = date.today() - timedelta(days=30)
        o1 = OrdenServicio.objects.create(
            vehiculo=self.v, fecha_ingreso=base, km_ingreso=1000, motivo="Mant")
        DetalleServicio.objects.create(orden=o1, tipo_servicio=self.aceite)
        for _ in range(3):
            services.avanzar_orden(o1)
        pend = ProximoServicio.objects.get(estado="PENDIENTE")
        self.assertEqual(pend.fecha_estimada, base + timedelta(days=75))   # uso NORMAL: 40 km/dia

        # vuelve con uso real alto: 3000 km en 30 dias = 100 km/dia
        OrdenServicio.objects.create(
            vehiculo=self.v, fecha_ingreso=date.today(), km_ingreso=4000, motivo="Revision")
        pend.refresh_from_db()
        self.assertEqual(pend.fecha_estimada, base + timedelta(days=30))   # 3000 km / 100 km/dia

    def test_formulario_no_permite_cambiar_km_al_editar(self):
        from .forms import VehiculoForm
        form = VehiculoForm(instance=self.v)
        self.assertTrue(form.fields["km_actual"].disabled)
