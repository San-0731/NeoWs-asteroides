import json
import logging
import requests #permite emular metodos del protocolo HTTP dando como respuesta un objeto de los datos obtenidos respuesta del servidor
import matplotlib.pyplot as plt
from datetime import datetime
#-------------------------------
from neo_app.cache import guardar_cache, cargar_cache, esta_vencida
from neo_app.fechas import solicitar_fechas
from neo_app.api import peticion
from neo_app.procesamiento import construir_datos
from neo_app.graficas import (
    grafica_por_fecha,
    grafica_distancia_vs_tamaño,
    grafica_peligrosos_no_peligrosos,
)
from neo_app.exportacion import exportar_a_csv
from neo_app.config import (
    ARCHIVO_CACHE,
    ARCHIVO_CSV,
    prepara_directorios_datos
)

logger = logging.getLogger(__name__)

def mostrar_resultados(resultados):
    for resultado in resultados:
        print(json.dumps(resultado, indent=4))

def obtener_datos(fecha, fecha_final, cache):
    clave = (fecha, fecha_final)
    entrada = cache.get(clave)

    if entrada is not None and esta_vencida(entrada, fecha_final):
        del cache[clave]
        try:
            guardar_cache(cache, ARCHIVO_CACHE)
        except OSError as error:
            logger.warning("No se pudo guardar el caché: %s", error)
        entrada = None

    if entrada is not None:
        return entrada["respuesta"], True

    datos = peticion(fecha, fecha_final)
    cache[clave] = {
        "respuesta": datos,
        "guardado_en": datetime.now().astimezone().isoformat(),
    }
    try:
        guardar_cache(cache, ARCHIVO_CACHE)
    except OSError as error:
        logger.warning("No se pudo guardar el caché: %s", error)

    return datos, False

def mostrar_figura(figura):
    figura_consola = plt.figure()
    canvas = figura_consola.canvas
    canvas.figure = figura
    figura.set_canvas(canvas)
    plt.show()

def menu_graficas(fechas, conteos, resultados):
    graficas = {
        1: lambda: grafica_por_fecha(fechas, conteos),
        2: lambda: grafica_distancia_vs_tamaño(resultados),
        3: lambda: grafica_peligrosos_no_peligrosos(resultados),
    }

    while True:
        print("\nGráficas disponibles:")
        print("1. Cantidad de objetos por fecha")
        print("2. Distancia de aproximación vs. tamaño")
        print("3. Asteroides peligrosos vs. no peligrosos")
        print("4. Volver al menú principal")

        try:
            opcion = int(input("Seleccione una gráfica: "))
        except ValueError:
            print("Entrada no válida. Ingrese un número.")
            continue

        if opcion == 4:
            return

        crear_grafica = graficas.get(opcion)
        if crear_grafica is None:
            print("Opción no válida. Intente nuevamente.")
            continue

        mostrar_figura(crear_grafica())

def main():
    prepara_directorios_datos()
    datos = None
    resultados = None
    fechas_grafica = None
    conteos = None
    opc = 0
    cache = {}
    try:
        cache = cargar_cache(ARCHIVO_CACHE)
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
                datos, desde_cache = obtener_datos(fecha, fecha_final, cache)
                if desde_cache:
                    print("Respuesta cargada desde el caché.")
                else:
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
                menu_graficas(fechas_grafica, conteos, resultados)

        elif opc == 4:
            if resultados is None:
                print("Primero realice la petición y construya los datos con las opciones 1 y 2")
            else:
                exportar_a_csv(
                    resultados,
                    ARCHIVO_CSV,
                )
                print("Datos exportados sin problemas.")

        elif opc == 5:
            print("Saliendo del programa.")
            
        else:
            print("Opción no válida. Intente nuevamente.")

if __name__ == "__main__":
    main()
            
