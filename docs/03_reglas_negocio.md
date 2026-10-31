# 03. Reglas de negocio

## A. Reglas obligatorias del enunciado

| ID | Regla | Cómo se garantiza |
|---|---|---|
| RN-01 | Todo vehículo debe estar asociado a un propietario. | Clave foránea obligatoria `Vehiculo.propietario`. |
| RN-02 | El ID del vehículo lo genera el sistema. | Clave primaria autoincremental; el formulario no la muestra. |
| RN-03 | Una placa no puede registrarse más de una vez. | `placa` única; se normaliza (mayúsculas, sin espacios ni guiones) para que `M 123-ABC` y `M123ABC` sean la misma. |
| RN-04 | El nuevo kilometraje no puede ser menor al último válido. | Validación en el vehículo y en la orden de servicio. |
| RN-05 | Cada ingreso al taller queda registrado. | Todo ingreso crea una `OrdenServicio`. |
| RN-06 | Los servicios anteriores se conservan como historial. | Los servicios viven en `DetalleServicio` ligados a su orden; nada se sobrescribe. |
| RN-07 | Al finalizar un servicio preventivo se establece el próximo mantenimiento. | Al pasar la orden a *Terminado* se crea un `ProximoServicio` por cada servicio preventivo. |
| RN-08 | Con 7 días o menos para la fecha estimada, el servicio aparece en las alertas. | Consulta de alertas: fecha entre hoy y hoy + 7 días. |
| RN-09 | Si la fecha estimada pasó sin registrarse el servicio, se marca como vencido. | Consulta de alertas: pendiente con fecha anterior a hoy. |
| RN-10 | No se duplican las notificaciones. | Restricción única (`proximo`, `tipo`) en la base y `get_or_create` en el servicio. |
| RN-11 | Una orden terminada debe contener información del servicio realizado. | No se puede pasar a *Terminado* una orden sin servicios. |

## B. Reglas adicionales definidas por el equipo

| ID | Regla | Justificación |
|---|---|---|
| RA-01 | El documento (DPI/NIT) del propietario es único. | Evita propietarios duplicados. |
| RA-02 | El propietario debe tener teléfono o correo. | Sin contacto no se puede enviar el recordatorio. |
| RA-03 | Un vehículo solo puede tener una orden activa (Recibido o En proceso). | Evita dos ingresos simultáneos del mismo vehículo. Se garantiza con un índice único parcial. |
| RA-04 | No se puede abrir una orden para un vehículo inactivo. | Un vehículo dado de baja no recibe servicio. |
| RA-05 | Los estados solo avanzan en orden y una orden *Entregada* es de solo lectura. | Conserva la trazabilidad del historial. |
| RA-06 | No se agregan servicios a una orden *Terminada* o *Entregada*. | La información cerrada no cambia. |
| RA-07 | El año del vehículo debe estar entre 1980 y el año actual + 1. | Evita errores de captura. |
| RA-08 | Los intervalos de un servicio (km y días) deben ser mayores que cero. | Evita fechas de próximo servicio inválidas. |
| RA-09 | El kilometraje de un vehículo existente solo cambia al registrar una orden. | Garantiza que cada actualización de km corresponda a un ingreso (RN-05). |
| RA-10 | Al terminar un servicio preventivo del mismo tipo, el pendiente anterior pasa a *Cumplido*. | Solo existe un próximo servicio vigente por tipo y vehículo. |
| RA-11 | Los servicios no preventivos (por ejemplo, reparación general) no generan próximo servicio. | No requieren recordatorio periódico. |
| RA-12 | Tipos de aviso: 7 días antes (2 a 7 días), 1 día antes (0 y 1 día) y vencido. | Dar seguimiento sin saturar al cliente. |
| RA-13 | Con dos ingresos consecutivos con km y días mayores que cero, el uso real (km/día) sustituye al nivel declarado. | Refina la estimación con datos reales. |
| RA-14 | Al ingresar con km nuevo, se recalcula la fecha de los servicios pendientes del vehículo. | La estimación se ajusta con la nueva información. |
| RA-15 | No se puede eliminar un propietario con vehículos, un vehículo con órdenes ni un tipo de servicio en uso. | Protege el historial (relaciones `PROTECT`). |
| RA-16 | Al terminar una orden se pueden registrar observaciones de cierre (trabajo realizado, repuestos, recomendaciones); junto con la fecha de cierre y los servicios forman la información de cierre. | Deja constancia de lo realizado al cerrar la atención. |
| RA-17 | Los recordatorios se generan al abrir el panel o las alertas, o con el comando `generar_recordatorios`, sin duplicar los ya generados. | Un mismo aviso nunca se registra dos veces. |
| RA-18 | El período de los vehículos atendidos en el panel solo admite 7, 30, 90 días o 1 año; cualquier otro valor usa 30 días. | Evita consultas con períodos inválidos. |
| RA-19 | Todas las pantallas, excepto el acceso, exigen una sesión iniciada; quien no la tiene es enviado al login y, al entrar, vuelve a la página que pedía. | Protege los datos de clientes y vehículos. |
| RA-20 | Los filtros de las listas ignoran valores inválidos (tipos, estados o fechas inexistentes) en lugar de fallar. | El sistema no se rompe con direcciones manipuladas. |
| RA-21 | Los teléfonos de 8 dígitos se tratan como guatemaltecos (+502) al abrir WhatsApp; un teléfono inválido no muestra el botón. | Evita enlaces rotos. |
