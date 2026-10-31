from django.core.management.base import BaseCommand

from taller import services


class Command(BaseCommand):
    help = "Genera recordatorios pendientes de servicios"

    def add_arguments(self, parser):
        parser.add_argument(
            "--actualizar-mensajes",
            action="store_true",
            help="Reescribe el texto de los recordatorios ya generados.",
        )

    def handle(self, *args, **options):
        if options["actualizar_mensajes"]:
            cambiados = services.actualizar_mensajes()
            self.stdout.write(
                self.style.SUCCESS(f"Mensajes actualizados: {cambiados}")
            )

        cantidad = services.generar_recordatorios()
        self.stdout.write(
            self.style.SUCCESS(f"Recordatorios nuevos: {cantidad}")
        )
