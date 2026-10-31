"""Utilidades de contacto: enlaces de WhatsApp (wa.me), sin API ni costo."""
from urllib.parse import quote

PREFIJO_GT = "502"


def telefono_internacional(telefono, prefijo=PREFIJO_GT):
    """Devuelve el teléfono solo con dígitos y con código de país, o None.

    - "5555-0000"        -> "50255550000" (8 dígitos: se asume Guatemala)
    - "+502 5555 0000"   -> "50255550000"
    - "00502 5555 0000"  -> "50255550000"
    - "12345"            -> None (no es un número utilizable)
    """
    texto = (telefono or "").strip()
    digitos = "".join(c for c in texto if c.isdigit())
    if not digitos:
        return None

    if texto.startswith("+"):
        pass
    elif digitos.startswith("00"):
        digitos = digitos[2:]
    elif len(digitos) == 8:
        digitos = prefijo + digitos

    return digitos if 10 <= len(digitos) <= 15 else None


def enlace_whatsapp(telefono, mensaje=""):
    """Enlace que abre el chat de WhatsApp con el mensaje ya escrito."""
    numero = telefono_internacional(telefono)
    if not numero:
        return None
    enlace = f"https://wa.me/{numero}"
    if mensaje:
        enlace += "?text=" + quote(mensaje, safe="")
    return enlace
