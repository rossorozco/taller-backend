from datetime import date, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand

from taller import services
from taller.models import DetalleServicio, OrdenServicio, Propietario, TipoServicio, Vehiculo


class Command(BaseCommand):
    help = "Carga catálogo y datos de demostración con fechas relativas a hoy"

    def handle(self, *args, **options):
        if not TipoServicio.objects.exists():
            call_command("loaddata", "datos_prueba", verbosity=0)
        hoy = date.today()
        p1 = Propietario.objects.get_or_create(documento="2456789010101", defaults=dict(
            nombre="Juan Pérez", telefono="5555-1234"))[0]
        p2 = Propietario.objects.get_or_create(documento="1234567-8", defaults=dict(
            tipo="EMPRESA", nombre="Transportes Maya, S.A.", correo="contacto@maya.com", telefono="2222-3333"))[0]

        # propietario, placa, tipo, marca, modelo, año, uso, días desde la visita, km, servicio
        casos = [
            (p1, "M101AAA", "MOTOCICLETA", "Honda", "CB125", 2022, "NORMAL", 80, 5000, "Cambio de aceite"),      # vencido
            (p1, "M102BBB", "MOTOCICLETA", "Yamaha", "FZ150", 2021, "ALTO", 33, 12000, "Cambio de aceite"),      # en ~4 días
            (p2, "P201CCC", "PICKUP", "Toyota", "Hilux", 2020, "BAJO", 70, 80000, "Cambio de aceite"),           # en ~20 días
            (p2, "C301DDD", "PANEL", "Nissan", "NV350", 2019, "NORMAL", 175, 120000, "Revisión de frenos"),      # en ~5 días
        ]
        for prop, placa, tipo, marca, modelo, anio, uso, dias, km, servicio in casos:
            if Vehiculo.objects.filter(placa=placa).exists():
                continue
            fecha = hoy - timedelta(days=dias)
            v = Vehiculo.objects.create(propietario=prop, placa=placa, tipo=tipo, marca=marca, modelo=modelo,
                                        anio=anio, nivel_uso=uso, km_actual=km, fecha_ingreso=fecha)
            o = OrdenServicio.objects.create(vehiculo=v, fecha_ingreso=fecha, km_ingreso=km, motivo="Mantenimiento preventivo")
            DetalleServicio.objects.create(orden=o, tipo_servicio=TipoServicio.objects.get(nombre=servicio),
                                           descripcion=servicio)
            for _ in range(3):                      # Recibido → En proceso → Terminado → Entregado
                services.avanzar_orden(o)

        v = Vehiculo.objects.filter(placa="P201CCC").first()
        if v and not v.ordenes.filter(estado="EN_PROCESO").exists():
            o = OrdenServicio.objects.create(vehiculo=v, km_ingreso=80500, motivo="Ruido en el tren delantero")
            services.avanzar_orden(o)               # queda En proceso
        n = services.generar_recordatorios()
        self.stdout.write(self.style.SUCCESS(f"Datos de demostración listos. Recordatorios generados: {n}"))