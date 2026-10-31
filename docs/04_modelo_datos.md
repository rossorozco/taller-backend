# 04. Modelo de datos

Base de datos relacional (SQLite). El diagrama entidad-relación está en [`diagrama_er.png`](diagrama_er.png). El script de creación es `db/schema.sql` y los datos de prueba `db/datos_prueba.sql`. Los nombres de tablas son los que genera Django (`taller_<modelo>`).

## 1. Entidades y relaciones

```
Propietario 1───N Vehiculo 1───N OrdenServicio 1───N DetalleServicio N───1 TipoServicio
                     │                                   │                       │
                     └──1───N ProximoServicio N──────────┘ (detalle_origen)      │
                                  │      └───────────N───1───────────────────────┘
                                  └──1───N Notificacion
```

## 2. Tablas, atributos y tipos

**taller_propietario**

| Campo | Tipo | Restricciones |
|---|---|---|
| id | integer | PK, autoincremental |
| tipo | varchar(10) | INDIVIDUAL o EMPRESA |
| nombre | varchar(120) | obligatorio |
| documento | varchar(20) | UNIQUE (DPI o NIT) |
| telefono, correo | varchar(20), varchar(254) | al menos uno obligatorio (regla de aplicación) |
| direccion | varchar(200) | opcional |
| activo | bool | |

**taller_vehiculo**

| Campo | Tipo | Restricciones |
|---|---|---|
| id | integer | PK, autoincremental (ID automático) |
| propietario_id | bigint | FK → propietario, obligatorio |
| tipo | varchar(12) | automóvil, motocicleta, pickup, panel u otro |
| marca, modelo | varchar(60) | obligatorios |
| anio | smallint | CHECK ≥ 0; rango 1980 a año actual + 1 |
| placa | varchar(15) | UNIQUE, normalizada |
| km_actual | integer | CHECK ≥ 0 |
| fecha_ingreso | date | fecha de registro del vehículo |
| estado | varchar(10) | ACTIVO o INACTIVO |
| nivel_uso | varchar(8) | BAJO, NORMAL o ALTO |
| km_dia_real | real | NULL; uso real calculado entre visitas |
| observaciones | text | |

**taller_tiposervicio** (catálogo)

| Campo | Tipo | Restricciones |
|---|---|---|
| id | integer | PK |
| nombre | varchar(80) | UNIQUE |
| intervalo_km | integer | ≥ 1 |
| intervalo_dias | integer | ≥ 1 |
| es_preventivo | bool | si genera próximo servicio |
| activo | bool | |

**taller_ordenservicio**

| Campo | Tipo | Restricciones |
|---|---|---|
| id | integer | PK (identificación de la orden) |
| vehiculo_id | bigint | FK → vehículo |
| fecha_ingreso | date | |
| km_ingreso | integer | CHECK ≥ 0 |
| motivo | varchar(200) | |
| estado | varchar(12) | RECIBIDO, EN_PROCESO, TERMINADO o ENTREGADO |
| observaciones | text | |
| fecha_cierre | date | NULL hasta terminar |

Índice único parcial `una_orden_activa_por_vehiculo`: un solo registro con estado RECIBIDO o EN_PROCESO por vehículo.

**taller_detalleservicio**: `id` (PK), `orden_id` (FK → orden), `tipo_servicio_id` (FK → tipo de servicio), `descripcion` varchar(200), `observaciones` text.

**taller_proximoservicio**: `id` (PK), `vehiculo_id` (FK), `tipo_servicio_id` (FK), `detalle_origen_id` (FK nula → detalle que lo originó), `fecha_estimada` date, `km_estimado` integer, `estado` (PENDIENTE, CUMPLIDO o CANCELADO).

**taller_notificacion**: `id` (PK), `proximo_id` (FK), `tipo` (SIETE_DIAS, UN_DIA o VENCIDO), `mensaje` text, `fecha_generada` datetime, `canal` (por defecto SISTEMA), `estado` (GENERADA o ENVIADA). Restricción `UNIQUE (proximo_id, tipo)`.

## 3. Justificación de las decisiones principales

1. **Propietario separado de Vehículo.** Un propietario puede tener muchos vehículos; así su teléfono y correo se guardan una sola vez (sin redundancia) y un cambio de contacto se refleja en todos sus vehículos. Un solo modelo cubre personas y empresas mediante el campo `tipo`.
2. **Orden y detalle separados.** Una orden puede incluir varios servicios (por ejemplo, aceite y frenos en la misma visita). `DetalleServicio` evita columnas repetidas y permite consultar cada servicio de forma independiente.
3. **Historial como consecuencia del modelo.** No hay una tabla de historial aparte: el historial de un vehículo es el conjunto de sus órdenes y sus detalles. Como las órdenes nunca se reemplazan, no se pierde información (RN-06).
4. **Catálogo `TipoServicio` con intervalos.** El taller puede agregar servicios y ajustar su periodicidad sin tocar el código. El campo `es_preventivo` decide si el servicio genera recordatorio.
5. **`ProximoServicio` como tabla propia.** Separa lo que ya pasó (órdenes) de lo que está por venir (pendientes). Permite obtener vencidos y próximos con una consulta simple por fecha y estado, sin recorrer el historial. Guarda `detalle_origen` para poder reajustar la fecha desde su punto de partida.
6. **`Notificacion` con restricción única.** La base impide duplicar un aviso del mismo tipo para el mismo servicio (RN-10), aunque la aplicación se ejecute varias veces o desde varios usuarios.
7. **`km_dia_real` en Vehículo.** Es un dato derivado que se guarda para no recalcularlo en cada consulta y que sustituye al nivel de uso cuando hay información real.
8. **Integridad referencial `PROTECT`.** Impide borrar propietarios, vehículos o servicios con historial, para no destruir registros.
9. **Normalización.** El modelo está en tercera forma normal: cada atributo depende de la clave de su tabla y los datos del propietario, vehículo y servicio no se repiten en las órdenes.

## 4. Consultas clave

Historial de un vehículo (sustituir `:id`):

```sql
SELECT o.id AS orden, o.fecha_ingreso, o.km_ingreso, o.motivo, o.estado,
       t.nombre AS servicio, d.observaciones
FROM taller_ordenservicio o
LEFT JOIN taller_detalleservicio d ON d.orden_id = o.id
LEFT JOIN taller_tiposervicio t ON t.id = d.tipo_servicio_id
WHERE o.vehiculo_id = :id
ORDER BY o.fecha_ingreso DESC, o.id DESC;
```

Servicios vencidos y próximos a 7 días:

```sql
SELECT p.nombre AS propietario, v.placa, t.nombre AS servicio,
       ps.fecha_estimada,
       CAST(julianday(ps.fecha_estimada) - julianday(date('now')) AS INTEGER) AS dias_restantes,
       CASE WHEN ps.fecha_estimada < date('now') THEN 'VENCIDO' ELSE 'PRÓXIMO' END AS situacion
FROM taller_proximoservicio ps
JOIN taller_vehiculo v ON v.id = ps.vehiculo_id
JOIN taller_propietario p ON p.id = v.propietario_id
JOIN taller_tiposervicio t ON t.id = ps.tipo_servicio_id
WHERE ps.estado = 'PENDIENTE'
  AND ps.fecha_estimada <= date('now', '+7 day')
ORDER BY ps.fecha_estimada;
```

Órdenes en proceso:

```sql
SELECT COUNT(*) FROM taller_ordenservicio WHERE estado = 'EN_PROCESO';
```

Notificaciones pendientes de envío:

```sql
SELECT n.tipo, n.mensaje, n.fecha_generada
FROM taller_notificacion n
WHERE n.estado = 'GENERADA'
ORDER BY n.fecha_generada;
```
