import requests
import os
import re
from urllib.parse import quote, quote_plus
from dotenv import load_dotenv
from neo_app.config import leer_ajustes
from neo_app.sanitizacion import sanitizar_api_keys

load_dotenv()


class LimiteApiError(Exception):
    """NASA rechazó la petición porque se alcanzó el límite de uso."""


def _sanitizar_error_peticion(error, api_key):
    mensaje = str(error)
    if api_key:
        variantes_clave = {
            api_key,
            quote(api_key, safe=""),
            quote_plus(api_key, safe=""),
        }
        for variante in variantes_clave:
            if variante:
                mensaje = mensaje.replace(variante, "[REDACTED]")

    return re.sub(
        r"([?&]api_key=)[^&\s'\"<>]+",
        r"\1[REDACTED]",
        mensaje,
        flags=re.IGNORECASE,
    )


def obtener_api_key():
    ajustes = leer_ajustes()
    clave_ajustes = ajustes.get("NASA_API_KEY", "").strip()

    if clave_ajustes:
        return clave_ajustes, clave_ajustes == "DEMO_KEY"

    clave_entorno = os.getenv("NASA_API_KEY", "").strip()
    if clave_entorno:
        return clave_entorno, clave_entorno == "DEMO_KEY"

    return "DEMO_KEY", True

def peticion(fecha, fecha_final):
    nasa_api_key, es_demo = obtener_api_key()
    website_request = "https://api.nasa.gov/neo/rest/v1/feed"

    query = {
        "start_date": fecha,
        "end_date": fecha_final,
        "api_key": nasa_api_key,
    }

    try:
        response = requests.get(website_request, params=query, timeout=10)

        if response.status_code == 429:
            raise LimiteApiError(
                "NASA indicó que se alcanzó el límite de solicitudes. "
                "Espera antes de volver a intentarlo o configura tu propia API key."
            )
        response.raise_for_status()
        datos = sanitizar_api_keys(response.json())
    except LimiteApiError:
        raise
    except requests.exceptions.RequestException as error:
        raise requests.exceptions.RequestException(
            _sanitizar_error_peticion(error, nasa_api_key)
        ) from None

    return datos, es_demo
