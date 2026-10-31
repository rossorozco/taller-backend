# 01. Análisis del problema

**Proyecto:** Sistema de Control de Servicios y Mantenimiento Preventivo de Vehículos
**Curso:** Seminario de Tecnología
**Equipo:** [Nombres de los integrantes]

## 1. Contexto

Un taller mecánico de motocicletas y vehículos atiende a clientes que son personas individuales o empresas. Hoy el taller no tiene una forma ordenada de saber qué vehículos deben volver a mantenimiento, ni de recordárselo a tiempo al propietario. Cuando el cliente olvida el servicio, el vehículo se deteriora y el taller pierde trabajo recurrente.

## 2. Problema a resolver

El taller necesita:

1. Llevar el control de propietarios, vehículos, órdenes de servicio e historial de mantenimiento.
2. Anticipar cuándo toca el siguiente mantenimiento de cada vehículo.
3. Avisar al propietario con tiempo suficiente (desde 7 días antes).

**Dificultad central:** el taller no conoce el kilometraje diario del vehículo. Solo lo conoce cuando el vehículo ingresa. Por eso el sistema no puede depender únicamente del kilometraje: además estima una **fecha** para el próximo servicio según el uso del vehículo (ver `05_logica_estimacion.md`).

## 3. Actores

| Actor | Rol en el sistema |
|---|---|
| Encargado del taller / recepción | Registra propietarios y vehículos, abre órdenes, agrega servicios, avanza estados y revisa alertas y notificaciones. Es el usuario principal. |
| Mecánico | Realiza el servicio; la información que produce (servicios, observaciones) la registra el encargado en la orden. |
| Propietario (persona o empresa) | No usa el sistema. Recibe el recordatorio por el medio de contacto registrado. |
| Administrador | Mantiene el catálogo de servicios y los datos mediante el panel `/admin/`. |

## 4. Alcance

**Incluido (mínimo del enunciado):**

- Registro de propietarios individuales y empresas.
- Registro y administración de vehículos con ID automático.
- Órdenes de servicio con estados Recibido, En proceso, Terminado y Entregado.
- Historial de servicios por vehículo, sin sustituir información anterior.
- Registro del kilometraje en cada ingreso y estimación de la fecha del próximo servicio.
- Alertas de servicios vencidos, próximos a 7 días y próximos a 30 días.
- Recordatorios al propietario a partir de 7 días antes, registrados en el sistema y sin duplicados.
- Dashboard con el resumen de la situación del taller.

**Mejoras opcionales incluidas:** segundo recordatorio un día antes, aviso de servicio vencido y despliegue con Docker.

**Fuera de alcance:** envío real de SMS, WhatsApp o correo (puede requerir costos externos; los mensajes se generan y quedan registrados con estado *Generada* o *Enviada* marcado manualmente), agenda de citas, costos y repuestos, y Kubernetes.

## 5. Supuestos

- El kilometraje solo se conoce cuando el vehículo ingresa al taller.
- Un vehículo tiene una sola orden activa a la vez.
- Cada propietario tiene al menos un medio de contacto (teléfono o correo).
- El catálogo de servicios y sus intervalos (km y días) los define el taller.
- La aplicación se usa dentro del taller; la autenticación se delega por ahora al panel de administración de Django.

## 6. Riesgos y decisiones

| Riesgo | Decisión |
|---|---|
| El uso real del vehículo no es conocido | Nivel de uso declarado (bajo, normal, alto) y ajuste automático con el uso real observado entre visitas. |
| Recordatorios repetidos molestan al cliente | Restricción única por servicio y tipo de aviso. |
| Datos de historial perdidos por borrados | Relaciones protegidas: no se puede eliminar un vehículo ni un propietario con historial. |
| Costos de mensajería externa | Se registra el mensaje dentro del sistema; el envío real queda como mejora. |

## 7. Tecnologías elegidas

Python y Django (aplicación web y ORM), SQLite (base de datos relacional), Bootstrap (interfaz), Git (control de versiones), Docker y Docker Compose (contenedores) y gunicorn con WhiteNoise (servidor y archivos estáticos en contenedor).
