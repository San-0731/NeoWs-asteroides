#Exportación a archivo CSV de los datos obtenidos de la API de NASA
import csv
import os
from datetime import datetime

def exportar_a_csv(resultados, nombre_archivo):
    # Verificar si el archivo ya existe
    archivo_existe = os.path.isfile(nombre_archivo)

    with open(nombre_archivo, mode='a', newline='', encoding='utf-8') as archivo_csv:
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

        # Escribir encabezado solo si el archivo no existía previamente
        if not archivo_existe:
            escritor.writeheader()

        fecha_importacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for resultado in resultados:
            escritor.writerow(
                {
                    "Fecha Importación": fecha_importacion,
                    "Fecha Asteroide": resultado.get("Fecha"),
                    "Name": resultado.get("Name"),
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
                }
            )
