
def construir_datos(data):

    resultados = []
    fechas_grafica = []
    conteos = []

    for fecha, objetos in sorted(data.get("near_earth_objects", {}).items()):

        
        #muestra el nombre de los asteroides
        for asteroide in objetos:

            #obtiene la lista y si esta vacia es que no existe
            close_approach_data = asteroide.get("close_approach_data", [])

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
        
        fechas_grafica.append(fecha)
        conteos.append(len(objetos))
                    
    return resultados, fechas_grafica, conteos
