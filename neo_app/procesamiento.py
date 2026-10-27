
def construir_datos(data):

    #mostramos la cantiadad de elementos encontrados habiendo buscado la linea del json con element_count, 
    # pero al ser solo de construcción de datos no es necesario mostrarlo, por eso se comenta para proximas revisiones
    #print("Element Count: ", data.get("element_count"))

    #se hace una lista con el inicio de la fecha y hasta el final de la fecha
    #fechas=list(data.get("near_earth_objects",{}).keys())
    #muestra la lista de las fechas que se buscaran
    # pero ahora como el usuario las dijita no es necesario mostrarlas, por eso se comenta para proximas revisiones
    #  print("Fechas Disponibles:", fechas_organizadas)
    
    #Al ser las fechas la entrada del arblo del .json de respuesta empezamos en ellas a 
    # ir mas profundo dentro del arbol

    resultados = []
    fechas_grafica = []
    conteos = []

    for fecha, objetos in sorted(data.get("near_earth_objects", {}).items()):

        #Print de depuración por si quieres ver las fechas que entraran a la busqueda
        #  y la cantidad de objetos cercanos a la tierra en esa fecha 
        #print(f"Fecha: {fecha} -> {len(objetos)} objetos cercanos")
        #print("------------------------------")
        
        #muestra el nombre de los asteroides)
        for asteroide in objetos:

            #obtiene la lista y si esta vacia es que no existe
            close_approach_data = asteroide.get("close_approach_data", [])

            #Probablemente esto se puede optimizar en un solo diccionario que me traiga todos los valores resumen
            ## Yo futuro -- Si se hizo todo en uno solo  
            resumen_completo = {
                "Fecha": fecha,
                "Name": asteroide.get("name", None),
                "Estimated_Diameter_(Km)": asteroide.get(
                    "estimated_diameter", {}).get("kilometers", {}).get(
                        "estimated_diameter_max", None
                        ),
                "Threat_Level": asteroide.get(
                    "is_potentially_hazardous_asteroid", None
                    ),
                "Close_Approach_Distance_(km)": (
                    float(close_approach_data[0]["miss_distance"]["kilometers"]) 
                    if close_approach_data else None
                    ),
                "Close_Approach_Velocity_(km/h)": (
                    float(close_approach_data[0]["relative_velocity"]["kilometers_per_hour"]) 
                    if close_approach_data else None
                    )
            }
            resultados.append(resumen_completo)
            #Esto lo que hace es guardar los datos de resumen en un diccionario "Resultados"
            #  y luego se imprime en formato JSON para que sea más legible y fácil de entender.
        fechas_grafica.append(fecha)
        conteos.append(len(objetos))
                    
    return resultados, fechas_grafica, conteos
