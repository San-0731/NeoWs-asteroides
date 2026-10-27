import json
import requests #permite emular metodos del protocolo HTTP dando como respuesta un objeto de los datos obtenidos respuesta del servidor
from datetime import datetime
from pathlib import Path
#-------------------------------
from neo_app.cache import guardar_cache, cargar_cache, esta_vencida
from neo_app.fechas import solicitar_fechas
from neo_app.api import peticion
from neo_app.procesamiento import construir_datos
from neo_app.graficas import construccion_grafica
from neo_app.exportacion import exportar_a_csv

DIRECTORIO_DATOS = Path(__file__).resolve().parent / "datos"

def mostrar_resultados(resultados):
    for resultado in resultados:
        print(json.dumps(resultado, indent=4))

def main():
    DIRECTORIO_DATOS.mkdir(parents=True, exist_ok=True)
    datos = None
    resultados = None
    fechas_grafica = None
    conteos = None
    opc = 0
    cache = {}
    cache_archivo = DIRECTORIO_DATOS / "cache_neows.json"
    try:
        cache = cargar_cache(cache_archivo)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        print(f"No se pudo cargar el caché; se iniciará vacío: {error}")

    while opc != 5:
        print("\nOpciones:")
        print("1. Realizar petición a la API de NASA")
        print("2. Construir datos y mostrar resultados")
        print("3. Construir gráficos")
        print("4. Guardar resultados a CSV")
        print("5. Salir")
        try:
            opc = int(input("Seleccione una opción: "))
        except ValueError:
            print("Entrada no válida. Por favor ingrese un número.")
            continue

        if opc == 1:
            try:
                fecha, fecha_final = solicitar_fechas()
                clave = (fecha, fecha_final)
                entrada = cache.get(clave)

                if entrada is not None and esta_vencida(entrada, fecha_final):
                    del cache[clave]
                    guardar_cache(cache, cache_archivo)
                    entrada = None

                if entrada is not None:
                    datos = entrada["respuesta"]
                    print("Respuesta cargada desde el caché.")
                else:
                    datos = peticion(fecha, fecha_final)
                    fecha_y_hora = datetime.now().astimezone().isoformat()
                    cache[clave] = {
                        "respuesta": datos,
                        "guardado_en": fecha_y_hora,
                    }
                    guardar_cache(cache, cache_archivo)
                    print(f"Petición para {fecha} - {fecha_final} realizada con éxito.")

                resultados = None
            except requests.exceptions.RequestException as error:
                print(f"Error al realizar la petición: {error}")
                continue

        elif opc == 2:
            if datos is None:
                print("Primero realice una petición en la opción 1.")
            else:
                resultados, fechas_grafica, conteos = construir_datos(datos)
                mostrar_resultados(resultados)

        elif opc == 3:
            if resultados is None:
                print("Primero realice una petición y construya los datos con las opciones 1 y 2.")
            else:
                construccion_grafica(fechas_grafica, conteos, resultados)

        elif opc == 4:
            if resultados is None:
                print("Primero realice la petición y construya los datos con las opciones 1 y 2")
            else:
                exportar_a_csv(
                    resultados,
                    DIRECTORIO_DATOS / "Historial_Consultas.csv",
                )
                print("Datos exportados sin problemas.")

        elif opc == 5:
            print("Saliendo del programa.")
            
        else:
            print("Opción no válida. Intente nuevamente.")

if __name__ == "__main__":
    main()
            
