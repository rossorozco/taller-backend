"""CORS mínimo (sin dependencias) para que el frontend consuma la API."""
from django.conf import settings
from django.http import HttpResponse


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _permitido(self, origen):
        lista = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS if o.strip()]
        return bool(origen) and ("*" in lista or origen in lista)

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        origen = request.headers.get("Origin")
        if request.method == "OPTIONS" and origen:
            respuesta = HttpResponse(status=204)
        else:
            respuesta = self.get_response(request)

        if self._permitido(origen):
            respuesta["Access-Control-Allow-Origin"] = origen
            respuesta["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
            respuesta["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            respuesta["Access-Control-Max-Age"] = "600"
            respuesta["Vary"] = "Origin"
        return respuesta
