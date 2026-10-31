# 06. Generación de recordatorios

## Cuándo se generan

Los recordatorios (7 días antes, 1 día antes y vencido) se generan de dos maneras:

1. Cada vez que se abre el **panel principal** o las **alertas**.
2. A demanda, con el comando:

   ```
   docker compose exec web python manage.py generar_recordatorios
   ```

Ambas usan la misma función, `services.generar_recordatorios()`. La restricción única `(proximo, tipo)` de la tabla de notificaciones impide registrar dos veces el mismo aviso, así que ejecutarla muchas veces no duplica nada.

## Limitación y cómo automatizarlo

Si nadie abre el sistema, los recordatorios no se crean hasta que alguien lo haga o se ejecute el comando. Para generarlos de forma periódica sin intervención, la opción más simple es un segundo servicio en Docker Compose que ejecute el comando cada hora (ejemplo; debe adaptarse al `docker-compose.yml` del proyecto):

```yaml
  recordatorios:
    build: .
    command: sh -c "while true; do python manage.py generar_recordatorios; sleep 3600; done"
```

Se prefiere un servicio separado, y no un hilo dentro de Gunicorn, porque Gunicorn arranca varios procesos y cada uno ejecutaría la tarea.

## Actualizar el texto de recordatorios antiguos

Si ya existían recordatorios con un texto anterior, se reescriben sin duplicarlos con:

```
docker compose exec web python manage.py generar_recordatorios --actualizar-mensajes
```

## Envío por WhatsApp

El botón de WhatsApp (notificaciones, alertas y ficha del propietario) abre `https://wa.me/<teléfono>?text=<mensaje>` con el mensaje ya escrito. No usa ninguna API ni tiene costo: la persona del taller revisa el mensaje y pulsa enviar. Después marca la notificación como enviada.
