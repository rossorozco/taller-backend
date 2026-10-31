-- Taller de Mantenimiento · script de creación (SQLite)
-- Estado final del modelo: migraciones 0001 y 0002.
BEGIN;
--
-- Tabla taller_propietario
--
CREATE TABLE "taller_propietario" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "tipo" varchar(10) NOT NULL, "nombre" varchar(120) NOT NULL, "documento" varchar(20) NOT NULL UNIQUE, "telefono" varchar(20) NOT NULL, "correo" varchar(254) NOT NULL, "direccion" varchar(200) NOT NULL, "activo" bool NOT NULL);
--
-- Tabla taller_tiposervicio
--
CREATE TABLE "taller_tiposervicio" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nombre" varchar(80) NOT NULL UNIQUE, "intervalo_km" integer unsigned NOT NULL CHECK ("intervalo_km" >= 0), "intervalo_dias" integer unsigned NOT NULL CHECK ("intervalo_dias" >= 0), "es_preventivo" bool NOT NULL, "activo" bool NOT NULL);
--
-- Tabla taller_vehiculo
--
CREATE TABLE "taller_vehiculo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "tipo" varchar(12) NOT NULL, "marca" varchar(60) NOT NULL, "modelo" varchar(60) NOT NULL, "anio" smallint unsigned NOT NULL CHECK ("anio" >= 0), "placa" varchar(15) NOT NULL UNIQUE, "km_actual" integer unsigned NOT NULL CHECK ("km_actual" >= 0), "fecha_ingreso" date NOT NULL, "estado" varchar(10) NOT NULL, "nivel_uso" varchar(8) NOT NULL, "km_dia_real" real NULL, "observaciones" text NOT NULL, "propietario_id" bigint NOT NULL REFERENCES "taller_propietario" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Tabla taller_ordenservicio
--
CREATE TABLE "taller_ordenservicio" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "fecha_ingreso" date NOT NULL, "km_ingreso" integer unsigned NOT NULL CHECK ("km_ingreso" >= 0), "motivo" varchar(200) NOT NULL, "estado" varchar(12) NOT NULL, "observaciones" text NOT NULL, "fecha_cierre" date NULL, "vehiculo_id" bigint NOT NULL REFERENCES "taller_vehiculo" ("id") DEFERRABLE INITIALLY DEFERRED, "observaciones_cierre" text NOT NULL);
--
-- Tabla taller_detalleservicio
--
CREATE TABLE "taller_detalleservicio" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "descripcion" varchar(200) NOT NULL, "observaciones" text NOT NULL, "orden_id" bigint NOT NULL REFERENCES "taller_ordenservicio" ("id") DEFERRABLE INITIALLY DEFERRED, "tipo_servicio_id" bigint NOT NULL REFERENCES "taller_tiposervicio" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Tabla taller_proximoservicio
--
CREATE TABLE "taller_proximoservicio" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "fecha_estimada" date NOT NULL, "km_estimado" integer unsigned NOT NULL CHECK ("km_estimado" >= 0), "estado" varchar(10) NOT NULL, "detalle_origen_id" bigint NULL REFERENCES "taller_detalleservicio" ("id") DEFERRABLE INITIALLY DEFERRED, "tipo_servicio_id" bigint NOT NULL REFERENCES "taller_tiposervicio" ("id") DEFERRABLE INITIALLY DEFERRED, "vehiculo_id" bigint NOT NULL REFERENCES "taller_vehiculo" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Tabla taller_notificacion
--
CREATE TABLE "taller_notificacion" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "tipo" varchar(12) NOT NULL, "mensaje" text NOT NULL, "fecha_generada" datetime NOT NULL, "canal" varchar(15) NOT NULL, "estado" varchar(10) NOT NULL, "proximo_id" bigint NOT NULL REFERENCES "taller_proximoservicio" ("id") DEFERRABLE INITIALLY DEFERRED, CONSTRAINT "notificacion_unica" UNIQUE ("proximo_id", "tipo"));
--
-- Índices
--
CREATE INDEX "taller_detalleservicio_orden_id_0311f409" ON "taller_detalleservicio" ("orden_id");
CREATE INDEX "taller_detalleservicio_tipo_servicio_id_979ad338" ON "taller_detalleservicio" ("tipo_servicio_id");
CREATE INDEX "taller_vehiculo_propietario_id_ee19cc76" ON "taller_vehiculo" ("propietario_id");
CREATE INDEX "taller_proximoservicio_detalle_origen_id_9967660e" ON "taller_proximoservicio" ("detalle_origen_id");
CREATE INDEX "taller_proximoservicio_tipo_servicio_id_750d0216" ON "taller_proximoservicio" ("tipo_servicio_id");
CREATE INDEX "taller_proximoservicio_vehiculo_id_7149f594" ON "taller_proximoservicio" ("vehiculo_id");
CREATE INDEX "taller_notificacion_proximo_id_830e933d" ON "taller_notificacion" ("proximo_id");
CREATE INDEX "taller_ordenservicio_vehiculo_id_cc25f94d" ON "taller_ordenservicio" ("vehiculo_id");
COMMIT;
