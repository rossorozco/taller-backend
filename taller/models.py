
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q

from .contacto import enlace_whatsapp


KM_DIA = {"BAJO": 15, "NORMAL": 40, "ALTO": 80}


class Propietario(models.Model):
    TIPOS = [
        ("INDIVIDUAL", "Individual"),
        ("EMPRESA", "Empresa"),
    ]

    tipo = models.CharField(max_length=10, choices=TIPOS, default="INDIVIDUAL")
    nombre = models.CharField(max_length=120)
    documento = models.CharField("DPI / NIT", max_length=20, unique=True)
    telefono = models.CharField("Teléfono", max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    direccion = models.CharField("Dirección", max_length=200, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def clean(self):
        super().clean()
        self.documento = (self.documento or "").strip()
        if not self.telefono.strip() and not self.correo.strip():
            raise ValidationError(
                "Indique al menos un teléfono o un correo para los recordatorios."
            )

    def save(self, *args, **kwargs):
        self.documento = (self.documento or "").strip()
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def whatsapp_url(self):
        """Abre el chat con el propietario (None si no hay teléfono válido)."""
        return enlace_whatsapp(self.telefono)

    def __str__(self):
        return self.nombre


class Vehiculo(models.Model):
    TIPOS = [
        ("AUTOMOVIL", "Automóvil"),
        ("MOTOCICLETA", "Motocicleta"),
        ("PICKUP", "Pickup"),
        ("PANEL", "Panel"),
        ("OTRO", "Otro"),
    ]
    USOS = [
        ("BAJO", "Bajo"),
        ("NORMAL", "Normal"),
        ("ALTO", "Alto"),
    ]
    ESTADOS = [
        ("ACTIVO", "Activo"),
        ("INACTIVO", "Inactivo"),
    ]

    propietario = models.ForeignKey(
        Propietario, on_delete=models.PROTECT, related_name="vehiculos"
    )
    tipo = models.CharField(max_length=12, choices=TIPOS, default="MOTOCICLETA")
    marca = models.CharField(max_length=60)
    modelo = models.CharField(max_length=60)
    anio = models.PositiveSmallIntegerField("Año")
    placa = models.CharField(max_length=15, unique=True)
    km_actual = models.PositiveIntegerField("Kilometraje actual", default=0)
    fecha_ingreso = models.DateField(default=date.today)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="ACTIVO")
    nivel_uso = models.CharField(
        "Nivel de uso", max_length=8, choices=USOS, default="NORMAL"
    )
    km_dia_real = models.FloatField(null=True, blank=True, editable=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ["placa"]

    @staticmethod
    def normalizar(placa):
        return "".join(
            c for c in (placa or "").upper() if c.isalnum()
        )

    @property
    def km_por_dia(self):
        if self.km_dia_real is not None and self.km_dia_real > 0:
            return self.km_dia_real
        return KM_DIA[self.nivel_uso]

    def clean(self):
        super().clean()
        self.placa = self.normalizar(self.placa)

        if self.anio is not None and not 1980 <= self.anio <= date.today().year + 1:
            raise ValidationError({
                "anio": "Año fuera de rango: 1980 hasta el año actual + 1."
            })

        if self.pk:
            anterior = Vehiculo.objects.get(pk=self.pk)
            if self.km_actual < anterior.km_actual:
                raise ValidationError({
                    "km_actual": (
                        f"No puede ser menor al último kilometraje "
                        f"({anterior.km_actual})."
                    )
                })

    def save(self, *args, **kwargs):
        self.placa = self.normalizar(self.placa)
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.placa} - {self.marca} {self.modelo}"


class TipoServicio(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    intervalo_km = models.PositiveIntegerField(
        "Intervalo (km)", default=1000, validators=[MinValueValidator(1)]
    )
    intervalo_dias = models.PositiveIntegerField(
        "Intervalo (días)", default=90, validators=[MinValueValidator(1)]
    )
    es_preventivo = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class OrdenServicio(models.Model):
    ESTADOS = [
        ("RECIBIDO", "Recibido"),
        ("EN_PROCESO", "En proceso"),
        ("TERMINADO", "Terminado"),
        ("ENTREGADO", "Entregado"),
    ]
    SIGUIENTE = {
        "RECIBIDO": "EN_PROCESO",
        "EN_PROCESO": "TERMINADO",
        "TERMINADO": "ENTREGADO",
    }
    ACTIVOS = ("RECIBIDO", "EN_PROCESO")

    vehiculo = models.ForeignKey(
        Vehiculo,
        verbose_name="Vehículo",
        on_delete=models.PROTECT,
        related_name="ordenes",
    )
    fecha_ingreso = models.DateField(default=date.today)
    km_ingreso = models.PositiveIntegerField("Kilometraje de ingreso")
    motivo = models.CharField(max_length=200)
    estado = models.CharField(
        max_length=12, choices=ESTADOS, default="RECIBIDO", editable=False
    )
    observaciones = models.TextField(blank=True)
    fecha_cierre = models.DateField(null=True, blank=True, editable=False)
    observaciones_cierre = models.TextField(
        "Observaciones de cierre",
        blank=True,
        help_text="Trabajo realizado, repuestos y recomendaciones al terminar.",
    )

    class Meta:
        ordering = ["-fecha_ingreso", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo"],
                condition=Q(estado__in=["RECIBIDO", "EN_PROCESO"]),
                name="una_orden_activa_por_vehiculo",
            )
        ]

    @property
    def siguiente_display(self):
        siguiente = self.SIGUIENTE.get(self.estado)
        return dict(self.ESTADOS).get(siguiente)

    @property
    def acepta_servicios(self):
        return self.estado in self.ACTIVOS

    def clean(self):
        super().clean()
        if not self.vehiculo_id or self.km_ingreso is None:
            return

        vehiculo = self.vehiculo
        if self._state.adding:
            if vehiculo.estado != "ACTIVO":
                raise ValidationError("El vehículo está inactivo.")

            if self.km_ingreso < vehiculo.km_actual:
                raise ValidationError({
                    "km_ingreso": (
                        f"No puede ser menor al último kilometraje "
                        f"({vehiculo.km_actual})."
                    )
                })

            if vehiculo.ordenes.filter(estado__in=self.ACTIVOS).exists():
                raise ValidationError(
                    "El vehículo ya tiene una orden activa."
                )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self._state.adding:
                vehiculo = Vehiculo.objects.select_for_update().get(
                    pk=self.vehiculo_id
                )
                self.vehiculo = vehiculo
                self.full_clean()

                previa = vehiculo.ordenes.order_by(
                    "-fecha_ingreso", "-id"
                ).first()

                if previa:
                    dias = (self.fecha_ingreso - previa.fecha_ingreso).days
                    km = self.km_ingreso - previa.km_ingreso
                    if dias > 0 and km > 0:
                        vehiculo.km_dia_real = km / dias

                vehiculo.km_actual = self.km_ingreso
                vehiculo.save()
                from . import services  # evita import circular
                services.reajustar_pendientes(vehiculo)
                return super().save(*args, **kwargs)

            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden #{self.pk} - {self.vehiculo.placa}"


class DetalleServicio(models.Model):
    orden = models.ForeignKey(
        OrdenServicio, on_delete=models.CASCADE, related_name="detalles"
    )
    tipo_servicio = models.ForeignKey(
        TipoServicio, verbose_name="Tipo de servicio", on_delete=models.PROTECT
    )
    descripcion = models.CharField("Descripción", max_length=200, blank=True)
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tipo_servicio} (orden {self.orden_id})"


class ProximoServicio(models.Model):
    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("CUMPLIDO", "Cumplido"),
        ("CANCELADO", "Cancelado"),
    ]

    vehiculo = models.ForeignKey(
        Vehiculo,
        verbose_name="Vehículo",
        on_delete=models.CASCADE,
        related_name="proximos",
    )
    tipo_servicio = models.ForeignKey(
        TipoServicio, verbose_name="Tipo de servicio", on_delete=models.PROTECT
    )
    detalle_origen = models.ForeignKey(
        DetalleServicio,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    fecha_estimada = models.DateField()
    km_estimado = models.PositiveIntegerField()
    estado = models.CharField(
        max_length=10, choices=ESTADOS, default="PENDIENTE"
    )

    class Meta:
        ordering = ["fecha_estimada"]

    @property
    def dias_restantes(self):
        return (self.fecha_estimada - date.today()).days

    @property
    def estado_recordatorio(self):
        notificacion = self.notificaciones.first()
        return (
            notificacion.get_estado_display()
            if notificacion
            else "Sin generar"
        )

    def __str__(self):
        return (
            f"{self.tipo_servicio} - {self.vehiculo.placa} "
            f"- {self.fecha_estimada}"
        )


class Notificacion(models.Model):
    TIPOS = [
        ("SIETE_DIAS", "7 días antes"),
        ("UN_DIA", "1 día antes"),
        ("VENCIDO", "Servicio vencido"),
    ]
    ESTADOS = [
        ("GENERADA", "Generada"),
        ("ENVIADA", "Enviada"),
    ]

    proximo = models.ForeignKey(
        ProximoServicio, on_delete=models.CASCADE,
        related_name="notificaciones"
    )
    tipo = models.CharField(max_length=12, choices=TIPOS)
    mensaje = models.TextField()
    fecha_generada = models.DateTimeField(auto_now_add=True)
    canal = models.CharField(max_length=15, default="SISTEMA")
    estado = models.CharField(
        max_length=10, choices=ESTADOS, default="GENERADA"
    )

    class Meta:
        ordering = ["-fecha_generada"]
        constraints = [
            models.UniqueConstraint(
                fields=["proximo", "tipo"],
                name="notificacion_unica",
            )
        ]

    @property
    def whatsapp_url(self):
        """Abre WhatsApp con este recordatorio ya escrito (None si no hay teléfono)."""
        propietario = self.proximo.vehiculo.propietario
        return enlace_whatsapp(propietario.telefono, self.mensaje)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.proximo}"
