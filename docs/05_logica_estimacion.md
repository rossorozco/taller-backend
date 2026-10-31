# 05. Lógica de estimación del próximo servicio

## Problema

El taller no sabe cuántos kilómetros recorre cada día el vehículo, solo conoce el kilometraje cuando ingresa. Entonces la fecha del próximo servicio se estima combinando dos límites: el **tiempo** recomendado y el **kilometraje** recomendado.

## Datos de entrada

- `intervalo_km` e `intervalo_dias` del servicio (catálogo).
- Fecha y kilometraje de la orden que se acaba de terminar.
- Uso diario estimado del vehículo (`km_por_dia`).

## Uso diario del vehículo

1. Si el vehículo ya tiene **uso real** (`km_dia_real`, mayor que cero), se usa ese valor.
2. Si no, se usa el **nivel de uso** que declara el taller:

| Nivel de uso | Km por día supuestos |
|---|---|
| Bajo | 15 |
| Normal | 40 |
| Alto | 80 |

El uso real se calcula cada vez que el vehículo vuelve al taller:

```
km_dia_real = (km del ingreso actual - km del ingreso anterior)
              / (días entre ambos ingresos)
```

Solo se actualiza si ambos valores son mayores que cero.

## Fórmula

```
dias_por_km   = intervalo_km / km_por_dia
dias          = max(1, entero( min(intervalo_dias, dias_por_km) ))
fecha_estimada = fecha_de_la_orden + dias
km_estimado    = km_de_la_orden + intervalo_km
```

Se toma **lo que ocurra primero**: si el vehículo se usa mucho, el límite de kilometraje llega antes que el de tiempo; si casi no se usa, el servicio igual se programa al cumplirse el plazo en días.

## Ejemplos

Cambio de aceite: 3000 km o 90 días, orden del 1 de enero con 1000 km.

| Uso | Cálculo | Días | Fecha estimada |
|---|---|---|---|
| Bajo (15 km/día) | 3000 / 15 = 200 → min(90, 200) | 90 | 1 de abril |
| Normal (40 km/día) | 3000 / 40 = 75 → min(90, 75) | 75 | 17 de marzo |
| Alto (80 km/día) | 3000 / 80 = 37,5 → min(90, 37) | 37 | 7 de febrero |

En los tres casos `km_estimado` = 1000 + 3000 = 4000 km.

## Ajuste con el uso real

Cuando el vehículo vuelve al taller con un kilometraje nuevo, el sistema:

1. Actualiza `km_actual` y calcula el nuevo `km_dia_real`.
2. Recalcula la fecha de los servicios **pendientes** del vehículo, tomando como punto de partida la fecha y el km de la orden que los originó.

Ejemplo: un cambio de aceite se programó con uso normal (75 días). Treinta días después el vehículo regresa con 3000 km más: el uso real es 3000 / 30 = 100 km/día. La fecha se recalcula con 3000 / 100 = 30 días, es decir, se adelanta porque el vehículo se usa más de lo supuesto.

## Cuándo se genera y se reemplaza

- Se genera un `ProximoServicio` por cada servicio **preventivo** al pasar la orden a *Terminado*.
- Al terminar de nuevo un servicio del mismo tipo, el pendiente anterior pasa a *Cumplido* y se crea el nuevo.
- Los servicios no preventivos no generan próximo servicio.

## Alertas y recordatorios

| Situación (días restantes) | Alerta | Recordatorio |
|---|---|---|
| Menor que 0 | Vencido | VENCIDO |
| 0 o 1 | Próximo a 7 días | UN_DIA |
| 2 a 7 | Próximo a 7 días | SIETE_DIAS |
| 8 a 30 | Próximo a 30 días | (aún no se genera) |

Cada tipo de recordatorio se genera una sola vez por servicio (restricción única). El mensaje se guarda en el sistema y el taller lo marca como *Enviada* cuando lo comunica al cliente.
