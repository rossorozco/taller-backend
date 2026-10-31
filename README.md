# Taller de Mantenimiento · Backend (API)

Backend Django del sistema de control de servicios y mantenimiento preventivo. Conserva modelos, reglas de negocio (`services.py`), migraciones, panel `/admin/` y comandos del proyecto original, y reemplaza las vistas HTML por una **API JSON** para un frontend independiente.

## Ejecución local
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_demo          # datos de demostración (opcional)
python manage.py createsuperuser
python manage.py runserver 8000
```
Con Docker: copiar `.env.example` a `.env`, definir `SECRET_KEY`, `DJANGO_SUPERUSER_*` y `docker compose up --build`.

Pruebas: `python manage.py test` (31 pruebas: reglas de negocio y API).

## Autenticación
`POST /api/login/` con `{"username": "...", "password": "..."}` devuelve `{"token": "...", "usuario": "..."}`.
Todas las demás rutas exigen `Authorization: Bearer <token>`. El token vence a las `API_TOKEN_HORAS` (12 por defecto). Sin cookies, por lo que no usa CSRF.

## Endpoints (prefijo `/api/`)
| Ruta | Métodos | Notas |
|---|---|---|
| `login/` | POST | Obtiene el token |
| `resumen/?dias=30` | GET | Tarjetas del panel y próximos 30 días (dias: 7, 30, 90, 365) |
| `alertas/` | GET | `vencidos`, `proximos7`, `proximos30` |
| `notificaciones/` | GET | Filtros `q`, `estado`, `tipo`; paginada |
| `notificaciones/<id>/enviada/` | POST | Marca como enviada |
| `propietarios/`, `propietarios/<id>/` | GET, POST / GET, PUT | Filtros `q`, `tipo`, `estado` (activo/inactivo) |
| `vehiculos/`, `vehiculos/<id>/` | GET, POST / GET, PUT | Filtros `q`, `tipo`, `estado`, `propietario`; el detalle incluye historial y pendientes |
| `ordenes/`, `ordenes/<id>/` | GET, POST / GET | Filtros `q` (`#12` por número), `estado`, `desde`, `hasta` |
| `ordenes/<id>/servicios/` | POST | Agrega un servicio a la orden |
| `ordenes/<id>/avanzar/` | POST | Siguiente estado; `observaciones_cierre` al terminar |
| `servicios/`, `servicios/<id>/` | GET, POST / PUT | Catálogo de servicios |

Las listas paginadas aceptan `pagina` y `tam` (máx. 100) y responden `{total, pagina, paginas, resultados}`. Los errores llegan como `{"error": "...", "campos": {"campo": ["mensaje"]}}`. En `PUT` basta con enviar los campos a cambiar.

## Configuración (variables de entorno)
`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_PATH`, `CORS_ALLOWED_ORIGINS` (orígenes del frontend, por coma; `*` solo en desarrollo) y `API_TOKEN_HORAS`.

## Estructura
```
config/    Configuración de Django
taller/    models, services (reglas), forms (validación), api.py, urls.py, middleware.py (CORS), tests
db/        schema.sql y datos_prueba.sql
docs/      Documentación del proyecto
```

## Recordatorios
Se generan al consultar `resumen/` y `alertas/`, o con `python manage.py generar_recordatorios`.
