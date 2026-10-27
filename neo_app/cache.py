from datetime import datetime, date, timedelta
from pathlib import Path
import json

CACHE_TTL = timedelta(hours=12)


def esta_vencida(entrada, fecha_final):
    guardado_en = datetime.fromisoformat(entrada["guardado_en"])
    fecha_final = date.fromisoformat(fecha_final)

    if guardado_en.date() > fecha_final:
        return False

    return datetime.now().astimezone() - guardado_en >= CACHE_TTL


def cargar_cache(archivo):
    cache_cargado = {}
    hubo_vencidas = False

    with open(archivo, encoding="utf-8") as archivo_json:
        cache_leido = json.load(archivo_json)

    for registro in cache_leido:
        clave = (registro["fecha"], registro["fecha_final"])
        if esta_vencida(registro, registro["fecha_final"]):
            hubo_vencidas = True
            continue

        cache_cargado[clave] = {
            "respuesta": registro["respuesta"],
            "guardado_en": registro["guardado_en"],
        }

    if hubo_vencidas:
        guardar_cache(cache_cargado, archivo)

    return cache_cargado

def guardar_cache(cache, archivo):
    entradas = []
    ruta_cache = Path(archivo)
    ruta_temporal = ruta_cache.with_name(ruta_cache.name + ".tmp")

    for (fecha, fecha_final), entrada in cache.items():
        entradas.append({
            "fecha": fecha,
            "fecha_final": fecha_final,
            "respuesta": entrada["respuesta"],
            "guardado_en": entrada["guardado_en"],
        })

    try:
        with open(ruta_temporal, "w", encoding="utf-8") as archivo_json:
            json.dump(entradas, archivo_json, ensure_ascii=False, indent=2)

        ruta_temporal.replace(ruta_cache)
    finally:
        if ruta_temporal.exists():
            ruta_temporal.unlink()