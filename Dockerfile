FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
EXPOSE 8000
# Al iniciar: migra, carga datos de demostracion (si CARGAR_DEMO=1),
# crea el administrador (si no existe) y levanta gunicorn.
CMD ["sh", "-c", "set -e; python manage.py migrate --noinput; if [ \"$CARGAR_DEMO\" = \"1\" ]; then python manage.py cargar_demo; fi; python manage.py shell -c 'import os; from django.contrib.auth import get_user_model; U=get_user_model(); u=os.environ[\"DJANGO_SUPERUSER_USERNAME\"]; U.objects.filter(username=u).exists() or U.objects.create_superuser(u, os.environ[\"DJANGO_SUPERUSER_EMAIL\"], os.environ[\"DJANGO_SUPERUSER_PASSWORD\"])'; exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 60"]
