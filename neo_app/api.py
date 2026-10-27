import requests
import os
from dotenv import load_dotenv

#La función load_dotenv introduce las variables de entorno del archivo .env 
# al archivo os.environque pueden utilizarse como cualquier otra variable de entorno establecida por el sistema operativo.
load_dotenv()

def peticion(fecha, fecha_final):
    nasa_api_key = os.getenv("NASA_API_KEY") or "DEMO_KEY"
    website_request = "https://api.nasa.gov/neo/rest/v1/feed"

    query = {
        "start_date": fecha,
        "end_date": fecha_final,
        "api_key": nasa_api_key,
    }

    #Se hace la petición a la API de NASA con los parámetros de fecha y la clave de API, y se obtiene la respuesta en formato JSON.
    response=requests.get(website_request, params=query, timeout=10)
    
    #Si la respuesta no es exitosa (código de estado diferente de 200), se lanza una excepción.
    response.raise_for_status()

    #Si la respuesta es exitosa, se devuelve el contenido de la respuesta en formato JSON.
    return response.json()

#Ya se hace la petición y los resultados de la petición se guardan en el siguiente función
# por eso la variable data guardando el resultado del JSON de la petición, que es un diccionario de Python 
#  y se puede acceder a sus elementos como cualquier otro diccionario.