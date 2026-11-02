import json
from queue import Empty, Queue
from threading import Thread

from customtkinter import CTk, CTkButton, CTkLabel, CTkEntry, CTkFrame, CTkTabview, CTkToplevel
from tkinter import messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from requests.exceptions import RequestException

from neo_app.cache import cargar_cache
from neo_app.fechas import validar_rango
from neo_app.api import LimiteApiError, obtener_api_key
from neo_app.consulta import obtener_datos
from neo_app.procesamiento import construir_datos
from neo_app.graficas import (
    grafica_por_fecha,
    grafica_distancia_vs_tamaño,
    grafica_peligrosos_no_peligrosos,
)
from neo_app.exportacion import exportar_a_csv
from neo_app.config import ARCHIVO_CACHE, ARCHIVO_CSV, DIRECTORIO_DATOS,prepara_directorios_datos, leer_ajustes, guardar_ajustes

def trabajo_consulta(fecha, fecha_final, fecha_recortada, cache, resultados_pendientes):
    try:
        datos, desde_cache, es_demo = obtener_datos(
            fecha, fecha_final, cache, ARCHIVO_CACHE
        )
        resultados, fechas_grafica, conteos = construir_datos(datos)

        mensaje = (
            "Consulta exitosa. Datos obtenidos desde "
            f"{'caché' if desde_cache else 'API'}."
        )
        if not desde_cache:
            mensaje += " Se usó DEMO_KEY." if es_demo else " Se usó una clave personal."
        if fecha_recortada:
            mensaje += f" Rango recortado a {fecha} - {fecha_final}."

        resultados_pendientes.put(
            ("success", (resultados, fechas_grafica, conteos), mensaje)
        )
    except LimiteApiError as error:
        resultados_pendientes.put(("error", None, f"Error: {error}"))
    except RequestException as error:
        resultados_pendientes.put(("error", None, f"Error de red: {error}"))
    except ValueError as error:
        resultados_pendientes.put(("error", None, f"Error al procesar la respuesta: {error}"))
    except (KeyError, TypeError) as error:
        resultados_pendientes.put(
            ("error", None, f"La respuesta de NASA tiene un formato inesperado: {error}")
        )

def consultar(
    app,
    entrada_inicial,
    entrada_final,
    boton_consultar,
    cache,
    estado,
    resultados_pendientes,
):
    fecha_inicial = entrada_inicial.get()
    fecha_final_texto = entrada_final.get().strip()

    if not fecha_inicial.strip():
        estado.configure(text="Error: La fecha inicial es obligatoria.")
        return

    try:
        fecha, fecha_final, fecha_recortada = validar_rango(
            fecha_inicial.strip(),
            fecha_final_texto or fecha_inicial.strip(),
        )
    except ValueError as error:
        estado.configure(text=f"Error de validación: {error}")
        return

    estado.configure(text="Consultando...")
    boton_consultar.configure(state="disabled")
    Thread(
        target=trabajo_consulta,
        args=(
            fecha,
            fecha_final,
            fecha_recortada,
            cache,
            resultados_pendientes,
        ),
        daemon=True,
    ).start()

def panel_izquierdo(app):
    panel = CTkFrame(app)
    panel.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")

    # Hace que la única columna del panel pueda estirarse.
    panel.grid_columnconfigure(0, weight=1)

    # Etiquetas y entradas para las fechas
    CTkLabel(panel, text="Consultar asteroides").grid(
        row=0, column=0, padx=16, pady=(20, 12), sticky="w"
    )

    CTkLabel(panel, text="Fecha inicial (AAAA-MM-DD)").grid(
        row=1, column=0, padx=16, pady=(8, 4), sticky="w"
    )
    entrada_panel_inicial = CTkEntry(panel, placeholder_text="2026-11-02")
    entrada_panel_inicial.grid(
        row=2, column=0, padx=16, pady=(0, 12), sticky="ew"
    )

    CTkLabel(panel, text="Fecha final (AAAA-MM-DD)").grid(
        row=3, column=0, padx=16, pady=(8, 4), sticky="w"
    )
    entrada_panel_final = CTkEntry(panel, placeholder_text="2026-11-02")
    entrada_panel_final.grid(
        row=4, column=0, padx=16, pady=(0, 16), sticky="ew"
    )

    # Botones de acción
    boton_consultar = CTkButton(panel, text="Consultar")
    boton_consultar.grid(
        row=5, column=0, padx=16, pady=8, sticky="ew"
    )

    boton_exportar = CTkButton(panel, text="Exportar CSV")
    boton_exportar.grid(
        row=6, column=0, padx=16, pady=8, sticky="ew"
    )

    boton_api_key = CTkButton(panel, text="configurar API Key")
    boton_api_key.grid(
        row=7, column=0, padx=16, pady=8, sticky="ew"
    )

    return entrada_panel_inicial, entrada_panel_final, boton_consultar, boton_exportar, boton_api_key

def zona_central(app):
    #panel central donde se mostraran los resultados de las opciones seleccionadas
    contenedor_zona_central = CTkFrame(app)
    contenedor_zona_central.grid(row=0, column=1, padx=(8,16), pady=16, sticky="nsew")
    contenedor_zona_central.grid_columnconfigure(0, weight=1)
    contenedor_zona_central.grid_rowconfigure(0, weight=1)

    #Vista de pestañas para mostrar resultados y gráficas
    tabs_zona_central = CTkTabview(contenedor_zona_central)
    tabs_zona_central.grid(row=0, column=0, sticky="nsew")
    tabs_zona_central.add("Resultados")
    tabs_zona_central.add("Gráficas")

    #Configuración de la pestaña de gráficas con vizualizaciones de los datos obtenidos
    # y una grafica por pestaña, se mostrara un mensaje de que se debe realizar una consulta para generar las gráficas
    contenedor_pestana_graficas = tabs_zona_central.tab("Gráficas")
    contenedor_pestana_graficas.grid_columnconfigure(0, weight=1)
    contenedor_pestana_graficas.grid_rowconfigure(0, weight=1)

    pestanas_graficas = CTkTabview(tabs_zona_central.tab("Gráficas"))
    pestanas_graficas.grid(row=0, column=0, padx=(8,16), pady=(0,16), sticky="nsew")

    pestanas_graficas.add("Por fecha")
    pestanas_graficas.add("Distancia y tamaño")
    pestanas_graficas.add("Nivel de amenaza")

    contenedor_graficas_fechas = pestanas_graficas.tab("Por fecha")
    contenedor_graficas_fechas.grid_columnconfigure(0, weight=1)
    contenedor_graficas_fechas.grid_rowconfigure(0, weight=1)
    CTkLabel(
        contenedor_graficas_fechas,
        text="Realiza una consulta para generar las gráficas.",
    ).grid(row=0, column=0, columnspan=2, sticky="nsew")

    contenedor_de_grafica_distancia_tamano = pestanas_graficas.tab("Distancia y tamaño")
    contenedor_de_grafica_distancia_tamano.grid_columnconfigure(0, weight=1)
    contenedor_de_grafica_distancia_tamano.grid_rowconfigure(0, weight=1)
    CTkLabel(
        contenedor_de_grafica_distancia_tamano,
        text="Realiza una consulta para generar las gráficas.",
    ).grid(row=0, column=0, columnspan=2, sticky="nsew")

    contenedor_de_grafica_nivel_amenaza = pestanas_graficas.tab("Nivel de amenaza")
    contenedor_de_grafica_nivel_amenaza.grid_columnconfigure(0, weight=1)
    contenedor_de_grafica_nivel_amenaza.grid_rowconfigure(0, weight=1)
    CTkLabel(
        contenedor_de_grafica_nivel_amenaza,
        text="Realiza una consulta para generar las gráficas.",
    ).grid(row=0, column=0, columnspan=2, sticky="nsew")

    # Configuración de la pestaña de resultados
    contenedor_de_tabla = tabs_zona_central.tab("Resultados")
    contenedor_de_tabla.grid_columnconfigure(0, weight=1)
    contenedor_de_tabla.grid_rowconfigure(0, weight=1)

    # Configuración de la tabla de resultados
    columnas = (
        "Fecha",
        "Name",
        "Estimated_Diameter_(Km)",
        "Threat_Level",
        "Close_Approach_Distance_(km)",
        "Close_Approach_Velocity_(km/h)",
    )

    encabezados = {
        "Fecha": "Fecha",
        "Name": "Nombre",
        "Estimated_Diameter_(Km)": "Diámetro estimado (km)",
        "Threat_Level": "Potencialmente peligroso",
        "Close_Approach_Distance_(km)": "Distancia (km)",
        "Close_Approach_Velocity_(km/h)": "Velocidad (km/h)",
    }
    tabla_resultados = ttk.Treeview(tabs_zona_central.tab("Resultados"), columns=columnas, show="headings")
    tabla_resultados.grid(row=0, column=0, sticky="nsew")
    for col in columnas:
        tabla_resultados.heading(col, text=encabezados.get(col, col))
        tabla_resultados.column(col, anchor="center")

    return tabla_resultados, tabs_zona_central, contenedor_graficas_fechas, contenedor_de_grafica_distancia_tamano, contenedor_de_grafica_nivel_amenaza

def barra_inferior(app):
    #se mostrara la informacion sobre que clave de api se usa (personal o demo) y el limite de peticiones que se pueden hacer
    barra_inferior = CTkFrame(app, height=50)
    barra_inferior.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0,16))

    for column in range(4):
        barra_inferior.grid_columnconfigure(column, weight=1)

    usuario = CTkLabel(barra_inferior, text="NeoWs App")
    usuario.grid(row=0, column=0, padx=16, pady=8, sticky="w")

    api_key = CTkLabel(barra_inferior, text="API Key: DEMO_KEY")
    api_key.grid(row=0, column=1, padx=16, pady=8, sticky="w")

    limite = CTkLabel(barra_inferior, text="Límite de peticiones: 30 por hora")
    limite.grid(row=0, column=2, padx=16, pady=8, sticky="w")

    #permite ver que los errores esten lejibles abajo y arriba esten los datos de la api y el usuario
    estado = CTkLabel(barra_inferior, text="Estado: Listo para consultar", anchor="w", justify="left", wraplength=700)
    estado.grid(row=1, column=0, columnspan=4, padx=16, pady=(8,8), sticky="ew")

    return usuario, api_key, limite, estado

def ventana_api_key(app, actualizar_info_api):
    ventana = CTkToplevel(app)
    ventana.title("Configurar API Key")
    ventana.geometry("400x200")
    ventana.resizable(False, False)

    CTkLabel(ventana, text="Ingresa tu API Key de la NASA:").pack(pady=(20, 10))
    entrada_api_key = CTkEntry(ventana, placeholder_text="API Key")
    entrada_api_key.pack(pady=(0, 20), padx=20, fill="x")

    def guardar_api_key():

        ajustes = leer_ajustes()
        ajustes["NASA_API_KEY"] = entrada_api_key.get().strip()

        try:
            guardar_ajustes(ajustes)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error", f"No se pudo guardar la API key: {error}", parent=ventana)
            return

        messagebox.showinfo("Éxito", "API Key guardada correctamente.", parent=ventana)
        actualizar_info_api()
        ventana.destroy()

    boton_guardar = CTkButton(ventana, text="Guardar", command=guardar_api_key)
    boton_guardar.pack(pady=(0, 20))

def main():

    prepara_directorios_datos()

    app = CTk()
    app.title("NeoWs App")
    app.geometry("1280x800")
    app.minsize(800, 600)

    try:
        cache = cargar_cache(ARCHIVO_CACHE)
    except FileNotFoundError:
        cache = {}
    except json.JSONDecodeError:
        cache = {}
        messagebox.showwarning(
            "Caché inválido",
            "El archivo de caché contiene JSON inválido. Se iniciará un caché vacío.",
            parent=app,
        )

    app.grid_columnconfigure(0, weight=1)
    app.grid_columnconfigure(1, weight=3)
    app.grid_rowconfigure(0, weight=1)

    entrada_inicial, entrada_final, boton_consultar, boton_exportar, boton_api_key = panel_izquierdo(app)
    tabla_resultados, tabs_zona_central, contenedor_graficas_fechas, contenedor_graficas_distancia_tamano, contenedor_graficas_nivel_amenaza = zona_central(app)
    usuario, api_key, limite, estado = barra_inferior(app)
    def actualizar_info_api():
        _, es_demo = obtener_api_key()
        api_key.configure(text=f"API Key: {'DEMO_KEY' if es_demo else 'Personal'}")
        limite.configure(text=f"Límite de peticiones: {'30' if es_demo else '1.000'} por hora")

    actualizar_info_api()

    resultados_pendientes = Queue()
    resultados_actuales = []

    boton_consultar.configure(command=lambda: consultar(
        app,
        entrada_inicial,
        entrada_final,
        boton_consultar,
        cache,
        estado,
        resultados_pendientes,
    ))

    boton_api_key.configure(command=lambda: ventana_api_key(app, actualizar_info_api))

    def exportar_resultados():
        if not resultados_actuales:
            estado.configure(text="No hay resultados para exportar. Realiza una consulta primero.")
            return

        try:
            exportar_a_csv(resultados_actuales, ARCHIVO_CSV)
        except OSError as error:
            estado.configure(text=f"No se pudo guardar el archivo CSV: {error}")
        else:
            estado.configure(text=f"Resultados exportados en: {ARCHIVO_CSV}")

    boton_exportar.configure(command=exportar_resultados)

    lienzos_graficas = []

    def actualizar_graficas(fechas, conteos, resultados):

        lienzos_graficas.clear()
        contenedores = (
            contenedor_graficas_fechas,
            contenedor_graficas_distancia_tamano,
            contenedor_graficas_nivel_amenaza,
        )
        figuras = (
            grafica_por_fecha(fechas, conteos),
            grafica_distancia_vs_tamaño(resultados),
            grafica_peligrosos_no_peligrosos(resultados),
        )

        for contenedor, figura in zip(contenedores, figuras):
            for widget in contenedor.winfo_children():
                widget.destroy()

            figura.set_size_inches(7, 4.5)
            lienzo = FigureCanvasTkAgg(figura, master=contenedor)
            lienzo.draw()
            lienzo.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            lienzos_graficas.append(lienzo)

    def procesar_resultados():
        try:
            tipo, datos_resultado, mensaje = resultados_pendientes.get_nowait()
        except Empty:
            app.after(100, procesar_resultados)
            return

        estado.configure(text=mensaje)
        if tipo == "success":
            resultados, fechas_grafica, conteos = datos_resultado
            resultados_actuales[:] = resultados
            for item in tabla_resultados.get_children():
                tabla_resultados.delete(item)

            for resultado in resultados:
                tabla_resultados.insert(
                    "",
                    "end",
                    values=(
                        resultado["Fecha"],
                        resultado["Name"],
                        resultado["Estimated_Diameter_(Km)"],
                        resultado["Threat_Level"],
                        resultado["Close_Approach_Distance_(km)"],
                        resultado["Close_Approach_Velocity_(km/h)"],
                    ),
                )
            actualizar_graficas(fechas_grafica, conteos, resultados)
            tabs_zona_central.set("Resultados")

        boton_consultar.configure(state="normal")
        app.after(100, procesar_resultados)

    app.after(100, procesar_resultados)

    app.mainloop()

if __name__ == "__main__":
    main()