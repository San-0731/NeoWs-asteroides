import requests
import os
import json
from dotenv import load_dotenv
from neo_app.config import ARCHIVO_AJUSTES, leer_ajustes

load_dotenv()
class LimiteApiError(Exception):
    """NASA rechazó la petición porque se alcanzó el límite de uso."""

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

    response=requests.get(website_request, params=query, timeout=10)

    if response.status_code == 429:
        raise LimiteApiError(
            "NASA indicó que se alcanzó el límite de solicitudes. "
            "Espera antes de volver a intentarlo o configura tu propia API key."
        )
    #Si la respuesta no es exitosa (código de estado diferente de 200), se lanza una excepción.
    response.raise_for_status()
    #Si la respuesta es exitosa, se devuelve el contenido de la respuesta en formato JSON.
    return response.json(), es_demo
