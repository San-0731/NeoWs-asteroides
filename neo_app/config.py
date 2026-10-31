from pathlib import Path
from platformdirs import user_data_dir


APP_NAME = "NeoWs-Asteroides"
APP_AUTHOR = "San-0731"

DIRECTORIO_DATOS = Path(user_data_dir(APP_NAME, APP_AUTHOR))
ARCHIVO_CACHE = DIRECTORIO_DATOS / "cache_neows.json"
ARCHIVO_CSV = DIRECTORIO_DATOS / "Historial_Consultas.csv"
ARCHIVO_AJUSTES = DIRECTORIO_DATOS / "settings.json"

def prepara_directorios_datos():
    DIRECTORIO_DATOS.mkdir(parents=True, exist_ok=True)
    if not ARCHIVO_AJUSTES.exists():
        guardar_ajustes({"NASA_API_KEY": ""})

import json

def leer_ajustes():
    if not ARCHIVO_AJUSTES.exists():
        return {"NASA_API_KEY": ""}

    try:
        with ARCHIVO_AJUSTES.open(encoding="utf-8") as archivo:
            ajustes = json.load(archivo)
    except json.JSONDecodeError as error:
        raise ValueError("El archivo de ajustes contiene JSON inválido.") from error

    if not isinstance(ajustes, dict):
        raise ValueError("El archivo de ajustes debe contener un objeto JSON.")

    ajustes.setdefault("NASA_API_KEY", "")
    if not isinstance(ajustes["NASA_API_KEY"], str):
        raise ValueError("NASA_API_KEY debe ser texto.")

    return ajustes


def guardar_ajustes(ajustes):
    if not isinstance(ajustes, dict):
        raise ValueError("Los ajustes deben ser un diccionario.")

    clave = ajustes.get("NASA_API_KEY", "")
    if not isinstance(clave, str):
        raise ValueError("NASA_API_KEY debe ser texto.")

    DIRECTORIO_DATOS.mkdir(parents=True, exist_ok=True)
    with ARCHIVO_AJUSTES.open("w", encoding="utf-8") as archivo:
        json.dump(ajustes, archivo, ensure_ascii=False, indent=2)