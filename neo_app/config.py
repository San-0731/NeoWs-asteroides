import json
import os
import tempfile
from pathlib import Path
from platformdirs import user_data_dir

APP_NAME = "NeoWs-Asteroides"
APP_AUTHOR = "San-0731"

DIRECTORIO_DATOS = Path(user_data_dir(APP_NAME, APP_AUTHOR))
ARCHIVO_CACHE = DIRECTORIO_DATOS / "cache_neows.json"
ARCHIVO_CSV = DIRECTORIO_DATOS / "Historial_Consultas.csv"
ARCHIVO_AJUSTES = DIRECTORIO_DATOS / "settings.json"

class AjustesInvalidosError(ValueError):
    """El archivo de ajustes contiene datos inválidos."""

def prepara_directorios_datos():
    DIRECTORIO_DATOS.mkdir(parents=True, exist_ok=True)
    if not ARCHIVO_AJUSTES.exists():
        guardar_ajustes({"NASA_API_KEY": ""})


def leer_ajustes():
    if not ARCHIVO_AJUSTES.exists():
        return {"NASA_API_KEY": ""}

    try:
        with ARCHIVO_AJUSTES.open(encoding="utf-8") as archivo:
            ajustes = json.load(archivo)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AjustesInvalidosError(
            "El archivo de ajustes contiene JSON inválido."
        ) from error

    if not isinstance(ajustes, dict):
        raise AjustesInvalidosError(
            "El archivo de ajustes debe contener un objeto JSON."
        )

    ajustes.setdefault("NASA_API_KEY", "")
    if not isinstance(ajustes["NASA_API_KEY"], str):
        raise AjustesInvalidosError("NASA_API_KEY debe ser texto.")

    return ajustes


def guardar_ajustes(ajustes):
    if not isinstance(ajustes, dict):
        raise ValueError("Los ajustes deben ser un diccionario.")

    clave = ajustes.get("NASA_API_KEY", "")
    if not isinstance(clave, str):
        raise ValueError("NASA_API_KEY debe ser texto.")

    DIRECTORIO_DATOS.mkdir(parents=True, exist_ok=True)
    archivo_temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DIRECTORIO_DATOS,
            prefix=f".{ARCHIVO_AJUSTES.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            archivo_temporal = Path(archivo.name)
            json.dump(ajustes, archivo, ensure_ascii=False, indent=2)
            archivo.flush()
            os.fsync(archivo.fileno())

        os.replace(archivo_temporal, ARCHIVO_AJUSTES)
        archivo_temporal = None
    finally:
        if archivo_temporal is not None and archivo_temporal.exists():
            archivo_temporal.unlink()