# 02. Requerimientos

## Requerimientos funcionales

| ID | Requerimiento | Dónde se cumple |
|---|---|---|
| RF-01 | Registrar propietarios individuales y empresas con documento (DPI/NIT), teléfono, correo y dirección. | Propietarios (`/propietarios/`) |
| RF-02 | Registrar y editar vehículos: tipo, marca, modelo, año, placa, kilometraje, fecha de ingreso, estado, nivel de uso y observaciones. El ID lo genera el sistema. | Vehículos (`/vehiculos/`) |
| RF-03 | Buscar vehículos por placa o nombre del propietario. | Lista de vehículos |
| RF-04 | Abrir una orden de servicio al ingresar un vehículo, con fecha, kilometraje de ingreso y motivo. | Órdenes (`/ordenes/nueva/`) |
| RF-05 | Agregar a la orden los servicios realizados, con descripción y observaciones. | Detalle de orden |
| RF-06 | Controlar los estados de la orden: Recibido → En proceso → Terminado → Entregado, y registrar las observaciones de cierre al terminarla. | Botón de avanzar estado |
| RF-07 | Conservar el historial completo de cada vehículo (ingresos, kilometrajes, servicios y observaciones). | Detalle del vehículo |
| RF-08 | Al terminar una orden con servicios preventivos, calcular y registrar el próximo servicio (fecha y km estimados). | `services.avanzar_orden` |
| RF-09 | Mostrar servicios vencidos, próximos a 7 días y próximos a 30 días, con propietario, vehículo, servicio, fecha estimada y estado del recordatorio. | Alertas (`/alertas/`) |
| RF-10 | Generar recordatorios para el propietario desde 7 días antes (más un aviso 1 día antes y otro al vencer), registrando el mensaje. Se generan al abrir el panel o las alertas, o con el comando `generar_recordatorios`. | `services.generar_recordatorios` |
| RF-11 | Listar las notificaciones generadas y marcarlas como enviadas. | Notificaciones (`/notificaciones/`) |
| RF-12 | Mostrar un dashboard con vehículos registrados, servicios próximos, vencidos, vehículos atendidos en el período, órdenes en proceso y listado de próximos servicios. El período de los vehículos atendidos se elige (7, 30, 90 días o 1 año). | Inicio (`/`) |
| RF-13 | Reajustar la fecha estimada de los servicios pendientes cuando el vehículo regresa con un kilometraje nuevo. | `services.reajustar_pendientes` |
| RF-14 | Administrar el catálogo de tipos de servicio (intervalos en km y días, preventivo o no). | Catálogo de servicios (`/servicios/`) y panel `/admin/` |
| RF-15 | Exigir inicio de sesión para usar el sistema; mostrar el usuario y permitir cerrar sesión. | Pantalla de acceso (`/login/`) |
| RF-16 | Consultar la ficha de un propietario con sus vehículos, órdenes, mantenimientos pendientes y datos de contacto. | Propietarios (`/propietarios/<id>/`) |
| RF-17 | Buscar y filtrar vehículos, propietarios, órdenes y notificaciones (texto, tipo, estado y fechas), con paginación que conserva los filtros. | Listas del sistema |
| RF-18 | Abrir WhatsApp con el recordatorio ya escrito para el propietario, sin API ni costo externo. | Notificaciones, alertas y ficha del propietario |

## Requerimientos no funcionales

| ID | Requerimiento |
|---|---|
| RNF-01 | Integridad de datos garantizada por la base de datos (claves foráneas, únicos y restricciones) y no solo por la interfaz. |
| RNF-02 | Las operaciones críticas (abrir orden, terminar orden, generar recordatorios) son atómicas (`transaction.atomic`). |
| RNF-03 | La aplicación se ejecuta en contenedor con `docker compose up --build`, con datos de demostración. |
| RNF-04 | Reglas de negocio verificadas con pruebas automáticas (`python manage.py test`). |
| RNF-05 | Interfaz web responsiva (Bootstrap) en español. |
| RNF-06 | Código versionado en Git con commits descriptivos. |
