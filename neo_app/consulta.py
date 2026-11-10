import logging
from datetime import datetime

from neo_app.api import peticion
from neo_app.cache import esta_vencida, guardar_cache


logger = logging.getLogger(__name__)


def obtener_datos(fecha, fecha_final, cache, archivo_cache, api_key=None):
    clave = (fecha, fecha_final)
    entrada = cache.get(clave)

    if entrada is not None and esta_vencida(entrada, fecha_final):
        del cache[clave]
        try:
            guardar_cache(cache, archivo_cache)
        except OSError as error:
            logger.warning("No se pudo guardar el caché: %s", error)
        entrada = None

    if entrada is not None:
        return entrada["respuesta"], True, False

    if api_key is None:
        datos, es_demo = peticion(fecha, fecha_final)
    else:
        datos, es_demo = peticion(fecha, fecha_final, api_key=api_key)    
    cache[clave] = {
        "respuesta": datos,
        "guardado_en": datetime.now().astimezone().isoformat(),
    }
    try:
        guardar_cache(cache, archivo_cache)
    except OSError as error:
        logger.warning("No se pudo guardar el caché: %s", error)

    return datos, False, es_demo
