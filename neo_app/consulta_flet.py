import asyncio

from neo_app.consulta import obtener_datos
from neo_app.procesamiento import construir_datos


def consultar_y_procesar(fecha, fecha_final, cache, archivo_cache, api_key=None):
    if api_key is None:
        datos, desde_cache, es_demo = obtener_datos(
            fecha, fecha_final, cache, archivo_cache
        )
    else:
        datos, desde_cache, es_demo = obtener_datos(
            fecha, fecha_final, cache, archivo_cache, api_key=api_key
        )

    resultados, fechas_grafica, conteos = construir_datos(datos)
    return resultados, fechas_grafica, conteos, desde_cache, es_demo


async def consultar_en_segundo_plano(fecha, fecha_final, cache, archivo_cache, api_key=None):
    return await asyncio.to_thread(
        consultar_y_procesar,
        fecha,
        fecha_final,
        cache,
        archivo_cache,
        api_key
    )
