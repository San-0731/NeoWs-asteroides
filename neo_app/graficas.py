from matplotlib.figure import Figure

def grafica_por_fecha(fechas, conteos):
    figura=Figure()
    ejes = figura.subplots()
    ejes.bar(fechas, conteos)
    ejes.set_xlabel("Fechas")
    ejes.set_ylabel("Cantidad")
    ejes.set_title("Distribución por fecha")
    figura.tight_layout()
    return figura

def grafica_distancia_vs_tamaño(resultados):
    figura = Figure()
    ejes = figura.subplots()

    resultados_validos = [
        resultado
        for resultado in resultados
        if resultado["Close_Approach_Distance_(km)"] is not None
        and resultado["Estimated_Diameter_(Km)"] is not None
    ]

    distancias = [
        resultado["Close_Approach_Distance_(km)"]
        for resultado in resultados_validos
    ]
    tamanos = [
        resultado["Estimated_Diameter_(Km)"]
        for resultado in resultados_validos
    ]

    ejes.scatter(distancias, tamanos)
    ejes.set_xlabel("Distancia de aproximación (km)")
    ejes.set_ylabel("Diámetro estimado (km)")
    ejes.set_title("Distancia de aproximación vs. tamaño")
    figura.tight_layout()

    return figura


def grafica_peligrosos_no_peligrosos(resultados):
    cantidad_peligrosos = sum(
        resultado["Threat_Level"] is True for resultado in resultados
    )
    cantidad_no_peligrosos = sum(
        resultado["Threat_Level"] is False for resultado in resultados
    )

    figura = Figure()
    ejes = figura.subplots()
    ejes.bar(
        ["Peligrosos", "No Peligrosos"],
        [cantidad_peligrosos, cantidad_no_peligrosos],
        color=["red", "blue"],
    )
    ejes.set_xlabel("Nivel de amenaza")
    ejes.set_ylabel("Cantidad de objetos")
    ejes.set_title("Comparación de objetos peligrosos y no peligrosos")
    figura.tight_layout()
    return figura