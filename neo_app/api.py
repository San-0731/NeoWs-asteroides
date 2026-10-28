import requests
import os
from dotenv import load_dotenv

load_dotenv()

def peticion(fecha, fecha_final):
    nasa_api_key = os.getenv("NASA_API_KEY") or "DEMO_KEY"
    website_request = "https://api.nasa.gov/neo/rest/v1/feed"

    query = {
        "start_date": fecha,
        "end_date": fecha_final,
        "api_key": nasa_api_key,
    }

    response=requests.get(website_request, params=query, timeout=10)
    
    #Si la respuesta no es exitosa (código de estado diferente de 200), se lanza una excepción.
    response.raise_for_status()

    #Si la respuesta es exitosa, se devuelve el contenido de la respuesta en formato JSON.
    return response.json()

