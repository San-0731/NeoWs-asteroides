import matplotlib.pyplot as plt #Permite crear graficos de manera sencilla y rapida

def construccion_grafica(fechas, conteos, resultados):

    #Primero realizaremos el grafico de cantidad por dia
    # Realizamos un gráfico de barras para mostrar la cantidad de objetos cercanos a la Tierra por día.
    plt.bar(fechas, conteos)
    plt.xlabel("Fecha")
    plt.ylabel("Cantidad de Objetos Cercanos")
    plt.title("Distribución de Objetos Cercanos a la Tierra por Fecha")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    #Ahora realizaremos el grafico de Distancia vs Tamaño
    # Realizamos un gráfico de dispersión para mostrar la relación entre la distancia de aproximación
    resultados_scatter = [r for r in resultados if r["Close_Approach_Distance_(km)"] is not None and r["Estimated_Diameter_(Km)"] is not None]
    plt.scatter([r["Close_Approach_Distance_(km)"] for r in resultados_scatter], [r["Estimated_Diameter_(Km)"] for r in resultados_scatter])
    plt.xlabel("Distancia de Aproximación (km)")
    plt.ylabel("Tamaño Estimado (km)")
    plt.title("Relación entre Distancia de Aproximación y Tamaño")
    plt.tight_layout()
    plt.show()

    #Ahora realizaremos el grafico de peligrosos vs No peligrosos siendo una comparación
    # Contamos la cantidad de objetos peligrosos y no peligrosos.
    Peligrosos = sum(1 for r in resultados if r["Threat_Level"] == True)
    No_Peligrosos = sum(1 for r in resultados if r["Threat_Level"] == False)
    plt.bar("Peligrosos", Peligrosos, color='red')
    plt.bar("No Peligrosos", No_Peligrosos, color='blue')
    plt.xlabel("Nivel de Amenaza")
    plt.ylabel("Cantidad de Objetos")
    plt.title("Comparación de Objetos Peligrosos y No Peligrosos")
    plt.tight_layout()
    plt.show()   