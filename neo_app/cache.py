from datetime import datetime, date, timedelta, timezone
from pathlib import Path
import json
from neo_app.sanitizacion import sanitizar_api_keys

CACHE_TTL = timedelta(hours=12)


class CacheFormatError(ValueError):
    """El archivo de caché no tiene la estructura esperada."""


def esta_vencida(entrada, fecha_final):
    guardado_en = datetime.fromisoformat(
        entrada["guardado_en"]
    ).astimezone(timezone.utc)
    fecha_final = date.fromisoformat(fecha_final)

    if guardado_en.date() > fecha_final:
        return False

    return datetime.now(timezone.utc) - guardado_en >= CACHE_TTL


def _validar_registro(registro, indice):
    if not isinstance(registro, dict):
        raise CacheFormatError(
            f"El registro {indice} del caché debe ser un objeto JSON."
        )

    campos_requeridos = ("fecha", "fecha_final", "respuesta", "guardado_en")
    campos_ausentes = [campo for campo in campos_requeridos if campo not in registro]
    if campos_ausentes:
        raise CacheFormatError(
            f"El registro {indice} no contiene: {', '.join(campos_ausentes)}."
        )

    if not isinstance(registro["fecha"], str):
        raise CacheFormatError(f"La fecha del registro {indice} debe ser texto.")
    if not isinstance(registro["fecha_final"], str):
        raise CacheFormatError(
            f"La fecha final del registro {indice} debe ser texto."
        )
    if not isinstance(registro["respuesta"], dict):
        raise CacheFormatError(
            f"La respuesta del registro {indice} debe ser un objeto JSON."
        )
    if not isinstance(registro["guardado_en"], str):
        raise CacheFormatError(
            f"La fecha de guardado del registro {indice} debe ser texto."
        )

    try:
        date.fromisoformat(registro["fecha"])
        date.fromisoformat(registro["fecha_final"])
        datetime.fromisoformat(registro["guardado_en"])
    except ValueError as error:
        raise CacheFormatError(
            f"El registro {indice} contiene una fecha inválida."
        ) from error


def cargar_cache(archivo):
    cache_cargado = {}
    hubo_vencidas = False
    hubo_api_keys = False

    with open(archivo, encoding="utf-8") as archivo_json:
        cache_leido = json.load(archivo_json)

    if not isinstance(cache_leido, list):
        raise CacheFormatError("El contenido del caché debe ser una lista.")

    for indice, registro in enumerate(cache_leido):
        _validar_registro(registro, indice)
        clave = (registro["fecha"], registro["fecha_final"])
        if esta_vencida(registro, registro["fecha_final"]):
            hubo_vencidas = True
            continue

        respuesta = sanitizar_api_keys(registro["respuesta"])
        hubo_api_keys = hubo_api_keys or respuesta != registro["respuesta"]
        cache_cargado[clave] = {
            "respuesta": respuesta,
            "guardado_en": registro["guardado_en"],
        }

    if hubo_vencidas or hubo_api_keys:
        guardar_cache(cache_cargado, archivo)

    return cache_cargado


def respaldar_cache_invalido(archivo):
    ruta_cache = Path(archivo)
    respaldo = ruta_cache.with_name(f"{ruta_cache.name}.bak")
    indice = 1
    while respaldo.exists():
        respaldo = ruta_cache.with_name(f"{ruta_cache.name}.bak.{indice}")
        indice += 1

    ruta_cache.replace(respaldo)
    return respaldo


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