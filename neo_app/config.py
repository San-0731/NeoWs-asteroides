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