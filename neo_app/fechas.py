from datetime import timedelta, date

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
            fecha_validada = date.fromisoformat(fecha)
            fecha_final_validada = date.fromisoformat(fecha_final)
        except ValueError:
            print("Fecha no válida. Use el formato AAAA-MM-DD, por ejemplo 2024-05-20.")
            continue

        if fecha_validada.isoformat() != fecha or fecha_final_validada.isoformat() != fecha_final:
            print("Fecha no válida. Use el formato AAAA-MM-DD, por ejemplo 2024-05-20.")
            continue
        # Validación de que la fecha final no sea anterior a la fecha inicial
        if fecha_final_validada < fecha_validada:
            print("La fecha final no puede ser anterior a la fecha inicial.")
            continue
        #validación de que la fecha final no sea mayor a 7 días después de la fecha inicial
        # casteo automatico al rango de fechas por default osea 7 diasss
        if (fecha_final_validada - fecha_validada).days > 7:
            print("Conversión automatica a 7 días después de la fecha inicial.")
            fecha_final_validada = fecha_validada + timedelta(days=7)

        return fecha_validada.isoformat(), fecha_final_validada.isoformat()
