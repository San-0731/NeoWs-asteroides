from datetime import timedelta, date

def validar_rango (fecha, fecha_final):

    try:
            
        fecha_validada=date.fromisoformat(fecha)
        fecha_final_validada=date.fromisoformat(fecha_final)
    except ValueError as error:
        raise ValueError(
            "Fecha no válida. Use el formato AAAA-MM-DD, por ejemplo 2024-05-20."
        ) from error     
    if fecha_validada.isoformat() != fecha or fecha_final_validada.isoformat() != fecha_final:
        raise ValueError(
            "Fecha no válida. Use el formato AAAA-MM-DD, por ejemplo 2024-05-20."
        )
    # Validación de que la fecha final no sea anterior a la fecha inicial
    if fecha_final_validada < fecha_validada:
        raise ValueError("La fecha final no puede ser anterior a la fecha inicial.")
        
    #validación de que la fecha final no sea mayor a 7 días después de la fecha inicial
    # casteo automatico al rango de fechas por default osea 7 diasss
    recortado = (fecha_final_validada - fecha_validada).days > 7

    if recortado:
        fecha_final_validada = fecha_validada + timedelta(days=7)

    return fecha_validada.isoformat(), fecha_final_validada.isoformat(), recortado

def solicitar_fechas():
    while True:
        fecha = input("Ingrese la fecha que desea revisar (AAAA-MM-DD): ").strip()
        fecha_final = input(
            "Ingrese la fecha final (AAAA-MM-DD), o presione Enter "
            "para consultar solo la fecha inicial: "
        ).strip()
        if not fecha_final:
            fecha_final = fecha

        try:
            fecha_validada, fecha_final_validada, recortado = validar_rango(fecha, fecha_final)
        except ValueError as error:
            print(error)
            continue
        if recortado:
            print("Conversión automática a 7 días después de la fecha inicial.")
        
        return fecha_validada, fecha_final_validada
