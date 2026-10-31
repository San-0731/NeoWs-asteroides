#Exportación a archivo CSV de los datos obtenidos de la API de NASA
import csv
from datetime import datetime
from pathlib import Path

def exportar_a_csv(resultados, nombre_archivo):
    ruta_archivo = Path(nombre_archivo)
    archivo_existe = ruta_archivo.is_file()
    claves_existentes = set()

    if archivo_existe and ruta_archivo.stat().st_size:
        with ruta_archivo.open(newline="", encoding="utf-8") as archivo_csv:
            lector = csv.DictReader(archivo_csv)
            claves_existentes = {
                (fila["Fecha Asteroide"], fila["Name"])
                for fila in lector
                if fila.get("Fecha Asteroide") and fila.get("Name")
            }

    with ruta_archivo.open(mode="a", newline="", encoding="utf-8") as archivo_csv:
        campos = [
            "Fecha Importación",
            "Fecha Asteroide",
            "Name",
            "Estimated_Diameter_(Km)",
            "Threat_Level",
            "Close_Approach_Distance_(km)",
            "Close_Approach_Velocity_(km/h)",
        ]
        escritor = csv.DictWriter(archivo_csv, fieldnames=campos)

        if not archivo_existe or ruta_archivo.stat().st_size == 0:
            escritor.writeheader()

        fecha_importacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for resultado in resultados:
            fecha = resultado.get("Fecha") or ""
            nombre = resultado.get("Name") or ""
            clave = None
            if fecha and nombre:
                clave = (str(fecha), str(nombre))
                if clave in claves_existentes:
                    continue

            escritor.writerow({
                "Fecha Importación": fecha_importacion,
                "Fecha Asteroide": fecha,
                "Name": nombre,
                "Estimated_Diameter_(Km)": resultado.get(
                    "Estimated_Diameter_(Km)"
                ),
                "Threat_Level": resultado.get("Threat_Level"),
                "Close_Approach_Distance_(km)": resultado.get(
                    "Close_Approach_Distance_(km)"
                ),
                "Close_Approach_Velocity_(km/h)": resultado.get(
                    "Close_Approach_Velocity_(km/h)"
                ),
            })
            if clave is not None:
                claves_existentes.add(clave)
