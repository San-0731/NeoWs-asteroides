import json
import logging
from queue import Empty, Queue
from threading import Thread

from customtkinter import CTk, CTkButton, CTkLabel, CTkEntry, CTkFrame, CTkTabview, CTkToplevel, set_appearance_mode
from tkinter import messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from requests.exceptions import RequestException

from neo_app.cache import CacheFormatError, cargar_cache, respaldar_cache_invalido
from neo_app.fechas import validar_rango
from neo_app.api import LimiteApiError, obtener_api_key
from neo_app.consulta import obtener_datos
from neo_app.procesamiento import construir_datos
from neo_app.graficas import (
    grafica_por_fecha,
    grafica_distancia_vs_tamano,
    grafica_peligrosos_no_peligrosos,
)
from neo_app.exportacion import exportar_a_csv
from neo_app.config import (
    ARCHIVO_CACHE,
    ARCHIVO_CSV,
    AjustesInvalidosError,
    guardar_ajustes,
    leer_ajustes,
    prepara_directorios_datos,
)

logger = logging.getLogger(__name__)

COLORES = {
    "fondo": "#080B1F",
    "panel": "#111936",
    "superficie": "#1B2547",
    "morado": "#8B5CF6",
    "morado_hover": "#7044D2",
    "azul": "#38BDF8",
    "blanco": "#F8FAFC",
    "texto_secundario": "#A5B4FC",
    "borde": "#344675",
    "fila_alterna": "#182343",
}


def aplicar_tema_figura(figura):
    figura.patch.set_facecolor(COLORES["fondo"])
    for ejes in figura.axes:
        ejes.set_facecolor(COLORES["panel"])
        ejes.title.set_color(COLORES["blanco"])
        ejes.xaxis.label.set_color(COLORES["texto_secundario"])
        ejes.yaxis.label.set_color(COLORES["texto_secundario"])
        ejes.tick_params(colors=COLORES["texto_secundario"])
        ejes.grid(color=COLORES["borde"], alpha=0.55)
        for borde in ejes.spines.values():
            borde.set_color(COLORES["borde"])

        for indice, barra in enumerate(ejes.patches):
            barra.set_facecolor(
                COLORES["morado"] if indice == 0 else COLORES["azul"]
            )
            barra.set_edgecolor(COLORES["blanco"])

        for coleccion in ejes.collections:
            coleccion.set_color(COLORES["azul"])


def interpolar_color(color_inicial, color_final, progreso):
    inicio = tuple(
        int(color_inicial[indice:indice + 2], 16)
        for indice in (1, 3, 5)
    )
    fin = tuple(
        int(color_final[indice:indice + 2], 16)
        for indice in (1, 3, 5)
    )
    canales = tuple(
        round(valor_inicio + (valor_fin - valor_inicio) * progreso)
        for valor_inicio, valor_fin in zip(inicio, fin)
    )
    return "#{:02X}{:02X}{:02X}".format(*canales)


def animar_tabla(app, tabla, animaciones, pasos=8, intervalo=18):
    identificador = id(tabla)
    anterior = animaciones.pop(identificador, None)
    if anterior is not None:
        app.after_cancel(anterior)

    filas = tabla.get_children()
    if not filas:
        return

    filas_por_tono = {
        fila: "par" if indice % 2 == 0 else "impar"
        for indice, fila in enumerate(filas)
    }
    color_texto_inicio = COLORES["panel"]
    colores_fondo_finales = {
        "par": COLORES["panel"],
        "impar": COLORES["fila_alterna"],
    }

    def configurar_etapa(paso):
        progreso = paso / pasos
        nombres_tags = {}
        for tono, color_fondo_final in colores_fondo_finales.items():
            nombre_tag = f"transicion_{tono}_{paso}"
            tabla.tag_configure(
                nombre_tag,
                foreground=interpolar_color(
                    color_texto_inicio,
                    COLORES["blanco"],
                    progreso,
                ),
                background=interpolar_color(
                    color_texto_inicio,
                    color_fondo_final,
                    progreso,
                ),
            )
            nombres_tags[tono] = nombre_tag
        return nombres_tags

    nombres_tags = configurar_etapa(0)
    for fila, tono in filas_por_tono.items():
        tabla.item(fila, tags=(nombres_tags[tono],))

    def avanzar(paso):
        nombres_tags = configurar_etapa(paso)

        for fila, tono in filas_por_tono.items():
            tabla.item(fila, tags=(nombres_tags[tono],))

        if paso == pasos:
            for fila, tono in filas_por_tono.items():
                tabla.item(fila, tags=(f"fila_{tono}",))
            animaciones.pop(identificador, None)
            return

        animaciones[identificador] = app.after(
            intervalo,
            lambda: avanzar(paso + 1),
        )

    animaciones[identificador] = app.after(intervalo, lambda: avanzar(1))


def animar_figura(
    app,
    figura,
    lienzo,
    animaciones,
    opacidades_originales,
    pasos=8,
    intervalo=18,
):
    identificador = id(lienzo)
    anterior = animaciones.pop(identificador, None)
    if anterior is not None:
        app.after_cancel(anterior)

    identificador_figura = id(figura)
    if identificador_figura not in opacidades_originales:
        artistas = []
        identificadores_artistas = set()
        for artista in figura.findobj():
            if artista is figura or id(artista) in identificadores_artistas:
                continue
            if callable(getattr(artista, "get_alpha", None)) and callable(
                getattr(artista, "set_alpha", None)
            ):
                artistas.append((artista, artista.get_alpha()))
                identificadores_artistas.add(id(artista))
        opacidades_originales[identificador_figura] = artistas
    artistas = opacidades_originales[identificador_figura]

    for artista, _ in artistas:
        artista.set_alpha(0)
    lienzo.draw_idle()

    def avanzar(paso):
        progreso = paso / pasos
        for artista, alpha_original in artistas:
            alpha_final = 1.0 if alpha_original is None else alpha_original
            artista.set_alpha(alpha_final * progreso)
        lienzo.draw_idle()

        if paso == pasos:
            for artista, alpha_original in artistas:
                artista.set_alpha(alpha_original)
            animaciones.pop(identificador, None)
            lienzo.draw_idle()
            return

        animaciones[identificador] = app.after(
            intervalo,
            lambda: avanzar(paso + 1),
        )

    animaciones[identificador] = app.after(intervalo, lambda: avanzar(1))


def iniciar_animacion_consulta(app, estado, animacion):
    animacion["activa"] = True
    animacion["puntos"] = 0
    animar_estado_consulta(app, estado, animacion)


def animar_estado_consulta(app, estado, animacion):
    if not animacion.get("activa"):
        return

    puntos = animacion.get("puntos", 0) % 3 + 1
    animacion["puntos"] = puntos
    estado.configure(text=f"Consultando{'.' * puntos}")
    animacion["after_id"] = app.after(
        450,
        lambda: animar_estado_consulta(app, estado, animacion),
    )


def detener_animacion_consulta(app, animacion):
    animacion["activa"] = False
    despues_id = animacion.get("after_id")
    if despues_id is not None:
        app.after_cancel(despues_id)
        animacion["after_id"] = None


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
    except AjustesInvalidosError as error:
        resultados_pendientes.put(
            ("error", None, f"Los ajustes son inválidos. Revisa settings.json: {error}")
        )
    except ValueError as error:
        resultados_pendientes.put(("error", None, f"Error al procesar la respuesta: {error}"))
    except (KeyError, TypeError) as error:
        resultados_pendientes.put(
            ("error", None, f"La respuesta de NASA tiene un formato inesperado: {error}")
        )
    except Exception as error:
        logger.error(
            "Error inesperado durante la consulta (%s).",
            type(error).__name__,
        )
        resultados_pendientes.put(
            (
                "error",
                None,
                "Ocurrió un error inesperado durante la consulta. "
                "Revisa la configuración e inténtalo de nuevo.",
            )
        )
def actualizar_info_api(etiqueta_api, etiqueta_limite):
    _, es_demo = obtener_api_key()
    etiqueta_api.configure(text=f"API Key: {'DEMO_KEY' if es_demo else 'Personal'}")
    etiqueta_limite.configure(
        text=f"Límite de peticiones: {'30' if es_demo else '1.000'} por hora"
    )


def aplicar_resultado_consulta(
    tipo,
    datos_resultado,
    mensaje,
    tabla_resultados,
    resultados_actuales,
    actualizar_graficas,
    tabs_zona_central,
    boton_consultar,
    estado,
):
    estado.configure(text=mensaje)
    if tipo == "success":
        resultados, fechas_grafica, conteos = datos_resultado
        resultados_actuales[:] = resultados

        for item in tabla_resultados.get_children():
            tabla_resultados.delete(item)

        for indice, resultado in enumerate(resultados):
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
                tags=("fila_par" if indice % 2 == 0 else "fila_impar",),
            )
        actualizar_graficas(fechas_grafica, conteos, resultados)
        tabs_zona_central.set("Resultados")

    boton_consultar.configure(state="normal")


def consultar(
    app,
    entrada_inicial,
    entrada_final,
    boton_consultar,
    cache,
    estado,
    resultados_pendientes,
    animacion_consulta=None,
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

    boton_consultar.configure(state="disabled")
    if animacion_consulta is not None:
        iniciar_animacion_consulta(app, estado, animacion_consulta)
    else:
        estado.configure(text="Consultando.")

    try:
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
    except Exception as error:
        if animacion_consulta is not None:
            detener_animacion_consulta(app, animacion_consulta)
        logger.error(
            "No se pudo iniciar el hilo de consulta (%s).",
            type(error).__name__,
        )
        boton_consultar.configure(state="normal")
        estado.configure(
            text="No se pudo iniciar la consulta. Inténtalo de nuevo."
        )

def panel_izquierdo(app):
    panel = CTkFrame(
        app,
        fg_color=COLORES["panel"],
        border_color=COLORES["borde"],
        border_width=1,
        corner_radius=16,
    )
    panel.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")

    # Hace que la única columna del panel pueda estirarse.
    panel.grid_columnconfigure(0, weight=1)

    # Etiquetas y entradas para las fechas
    CTkLabel(
        panel,
        text="Consultar asteroides",
        text_color=COLORES["blanco"],
        font=("Arial", 18, "bold"),
    ).grid(
        row=0, column=0, padx=16, pady=(20, 12), sticky="w"
    )

    CTkLabel(
        panel,
        text="Fecha inicial (AAAA-MM-DD)",
        text_color=COLORES["texto_secundario"],
    ).grid(
        row=1, column=0, padx=16, pady=(8, 4), sticky="w"
    )
    entrada_panel_inicial = CTkEntry(
        panel,
        placeholder_text="2026-11-02",
        fg_color=COLORES["fondo"],
        border_color=COLORES["borde"],
        text_color=COLORES["blanco"],
        placeholder_text_color=COLORES["texto_secundario"],
    )
    entrada_panel_inicial.grid(
        row=2, column=0, padx=16, pady=(0, 12), sticky="ew"
    )

    CTkLabel(
        panel,
        text="Fecha final (AAAA-MM-DD)",
        text_color=COLORES["texto_secundario"],
    ).grid(
        row=3, column=0, padx=16, pady=(8, 4), sticky="w"
    )
    entrada_panel_final = CTkEntry(
        panel,
        placeholder_text="2026-11-02",
        fg_color=COLORES["fondo"],
        border_color=COLORES["borde"],
        text_color=COLORES["blanco"],
        placeholder_text_color=COLORES["texto_secundario"],
    )
    entrada_panel_final.grid(
        row=4, column=0, padx=16, pady=(0, 16), sticky="ew"
    )

    # Botones de acción
    boton_consultar = CTkButton(
        panel,
        text="Consultar",
        fg_color=COLORES["morado"],
        hover_color=COLORES["morado_hover"],
        text_color=COLORES["blanco"],
        corner_radius=10,
    )
    boton_consultar.grid(
        row=5, column=0, padx=16, pady=8, sticky="ew"
    )

    boton_exportar = CTkButton(
        panel,
        text="Exportar CSV",
        fg_color=COLORES["azul"],
        hover_color="#168FC2",
        text_color=COLORES["fondo"],
        corner_radius=10,
    )
    boton_exportar.grid(
        row=6, column=0, padx=16, pady=8, sticky="ew"
    )

    boton_api_key = CTkButton(
        panel,
        text="Configurar API Key",
        fg_color=COLORES["superficie"],
        hover_color=COLORES["borde"],
        text_color=COLORES["blanco"],
        border_color=COLORES["azul"],
        border_width=1,
        corner_radius=10,
    )
    boton_api_key.grid(
        row=7, column=0, padx=16, pady=8, sticky="ew"
    )

    return entrada_panel_inicial, entrada_panel_final, boton_consultar, boton_exportar, boton_api_key

def zona_central(app):
    #panel central donde se mostraran los resultados de las opciones seleccionadas
    contenedor_zona_central = CTkFrame(
        app,
        fg_color=COLORES["panel"],
        border_color=COLORES["borde"],
        border_width=1,
        corner_radius=16,
    )
    contenedor_zona_central.grid(row=0, column=1, padx=(8,16), pady=16, sticky="nsew")
    contenedor_zona_central.grid_columnconfigure(0, weight=1)
    contenedor_zona_central.grid_rowconfigure(0, weight=1)

    #Vista de pestañas para mostrar resultados y gráficas
    tabs_zona_central = CTkTabview(
        contenedor_zona_central,
        fg_color=COLORES["panel"],
        segmented_button_fg_color=COLORES["fondo"],
        segmented_button_selected_color=COLORES["morado"],
        segmented_button_selected_hover_color=COLORES["morado_hover"],
        segmented_button_unselected_color=COLORES["superficie"],
        segmented_button_unselected_hover_color=COLORES["borde"],
        text_color=COLORES["blanco"],
        text_color_disabled=COLORES["texto_secundario"],
        corner_radius=12,
    )
    tabs_zona_central.grid(row=0, column=0, sticky="nsew")
    tabs_zona_central.add("Resultados")
    tabs_zona_central.add("Gráficas")

    #Configuración de la pestaña de gráficas con vizualizaciones de los datos obtenidos
    # y una grafica por pestaña, se mostrara un mensaje de que se debe realizar una consulta para generar las gráficas
    contenedor_pestana_graficas = tabs_zona_central.tab("Gráficas")
    contenedor_pestana_graficas.grid_columnconfigure(0, weight=1)
    contenedor_pestana_graficas.grid_rowconfigure(0, weight=1)

    pestanas_graficas = CTkTabview(
        tabs_zona_central.tab("Gráficas"),
        fg_color=COLORES["panel"],
        segmented_button_fg_color=COLORES["fondo"],
        segmented_button_selected_color=COLORES["azul"],
        segmented_button_selected_hover_color="#168FC2",
        segmented_button_unselected_color=COLORES["superficie"],
        segmented_button_unselected_hover_color=COLORES["borde"],
        text_color=COLORES["blanco"],
        text_color_disabled=COLORES["texto_secundario"],
        corner_radius=12,
    )
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
        text_color=COLORES["texto_secundario"],
    ).grid(row=0, column=0, columnspan=2, sticky="nsew")

    contenedor_de_grafica_distancia_tamano = pestanas_graficas.tab("Distancia y tamaño")
    contenedor_de_grafica_distancia_tamano.grid_columnconfigure(0, weight=1)
    contenedor_de_grafica_distancia_tamano.grid_rowconfigure(0, weight=1)
    CTkLabel(
        contenedor_de_grafica_distancia_tamano,
        text="Realiza una consulta para generar las gráficas.",
        text_color=COLORES["texto_secundario"],
    ).grid(row=0, column=0, columnspan=2, sticky="nsew")

    contenedor_de_grafica_nivel_amenaza = pestanas_graficas.tab("Nivel de amenaza")
    contenedor_de_grafica_nivel_amenaza.grid_columnconfigure(0, weight=1)
    contenedor_de_grafica_nivel_amenaza.grid_rowconfigure(0, weight=1)
    CTkLabel(
        contenedor_de_grafica_nivel_amenaza,
        text="Realiza una consulta para generar las gráficas.",
        text_color=COLORES["texto_secundario"],
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
    estilo_tabla = ttk.Style(app)
    estilo_tabla.theme_use("clam")
    estilo_tabla.configure(
        "NeoWs.Treeview",
        background=COLORES["panel"],
        fieldbackground=COLORES["fondo"],
        foreground=COLORES["blanco"],
        rowheight=32,
        borderwidth=1,
        relief="solid",
        font=("Arial", 10),
    )
    estilo_tabla.configure(
        "NeoWs.Treeview.Heading",
        background=COLORES["superficie"],
        foreground=COLORES["blanco"],
        font=("Arial", 10, "bold"),
        padding=(8, 10),
        borderwidth=1,
        relief="raised",
    )
    estilo_tabla.map(
        "NeoWs.Treeview",
        background=[("selected", COLORES["morado"])],
        foreground=[("selected", COLORES["blanco"])],
    )
    estilo_tabla.map(
        "NeoWs.Treeview.Heading",
        background=[("active", COLORES["morado"])],
        foreground=[("active", COLORES["blanco"])],
    )
    estilo_tabla.configure(
        "NeoWs.Vertical.TScrollbar",
        background=COLORES["superficie"],
        troughcolor=COLORES["fondo"],
        bordercolor=COLORES["borde"],
        arrowcolor=COLORES["blanco"],
    )
    estilo_tabla.configure(
        "NeoWs.Horizontal.TScrollbar",
        background=COLORES["superficie"],
        troughcolor=COLORES["fondo"],
        bordercolor=COLORES["borde"],
        arrowcolor=COLORES["blanco"],
    )

    tabla_resultados = ttk.Treeview(
        tabs_zona_central.tab("Resultados"),
        columns=columnas,
        show="headings",
        style="NeoWs.Treeview",
    )
    tabla_resultados.tag_configure("fila_par", background=COLORES["panel"])
    tabla_resultados.tag_configure(
        "fila_impar",
        background=COLORES["fila_alterna"],
    )
    tabla_resultados.grid(row=0, column=0, sticky="nsew")
    anchos_columnas = {
        "Fecha": 95,
        "Name": 140,
        "Estimated_Diameter_(Km)": 150,
        "Threat_Level": 155,
        "Close_Approach_Distance_(km)": 155,
        "Close_Approach_Velocity_(km/h)": 155,
    }
    for col in columnas:
        tabla_resultados.heading(col, text=encabezados.get(col, col))
        tabla_resultados.column(
            col,
            anchor="center",
            width=anchos_columnas[col],
            minwidth=80,
            stretch=True,
        )

    contenedor_de_tabla.grid_columnconfigure(0, weight=1)
    contenedor_de_tabla.grid_columnconfigure(1, weight=0)
    contenedor_de_tabla.grid_rowconfigure(1, weight=0)

    scrollbar_vertical = ttk.Scrollbar(
        contenedor_de_tabla,
        orient="vertical",
        command=tabla_resultados.yview,
        style="NeoWs.Vertical.TScrollbar",
    )
    scrollbar_vertical.grid(row=0, column=1, sticky="ns")
    tabla_resultados.configure(yscrollcommand=scrollbar_vertical.set)

    scrollbar_horizontal = ttk.Scrollbar(
        contenedor_de_tabla,
        orient="horizontal",
        command=tabla_resultados.xview,
        style="NeoWs.Horizontal.TScrollbar",
    )
    scrollbar_horizontal.grid(row=1, column=0, sticky="ew")
    tabla_resultados.configure(xscrollcommand=scrollbar_horizontal.set)

    return (
        tabla_resultados,
        tabs_zona_central,
        pestanas_graficas,
        contenedor_graficas_fechas,
        contenedor_de_grafica_distancia_tamano,
        contenedor_de_grafica_nivel_amenaza,
    )

def barra_inferior(app):
    #se mostrara la informacion sobre que clave de api se usa (personal o demo) y el limite de peticiones que se pueden hacer
    barra_inferior = CTkFrame(
        app,
        height=50,
        fg_color=COLORES["panel"],
        border_color=COLORES["borde"],
        border_width=1,
        corner_radius=12,
    )
    barra_inferior.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0,16))

    for column in range(4):
        barra_inferior.grid_columnconfigure(column, weight=1)

    usuario = CTkLabel(
        barra_inferior,
        text="NeoWs App",
        text_color=COLORES["blanco"],
    )
    usuario.grid(row=0, column=0, padx=16, pady=8, sticky="w")

    api_key = CTkLabel(
        barra_inferior,
        text="API Key: DEMO_KEY",
        text_color=COLORES["texto_secundario"],
    )
    api_key.grid(row=0, column=1, padx=16, pady=8, sticky="w")

    limite = CTkLabel(
        barra_inferior,
        text="Límite de peticiones: 30 por hora",
        text_color=COLORES["texto_secundario"],
    )
    limite.grid(row=0, column=2, padx=16, pady=8, sticky="w")

    #permite ver que los errores esten lejibles abajo y arriba esten los datos de la api y el usuario
    estado = CTkLabel(
        barra_inferior,
        text="Estado: Listo para consultar",
        anchor="w",
        justify="left",
        wraplength=700,
        text_color=COLORES["blanco"],
    )
    estado.grid(row=1, column=0, columnspan=4, padx=16, pady=(8,8), sticky="ew")

    return usuario, api_key, limite, estado

def ventana_api_key(app, actualizar_info_api):
    ventana = CTkToplevel(app)
    ventana.configure(fg_color=COLORES["fondo"])
    ventana.title("Configurar API Key")
    ventana.geometry("400x250")
    ventana.resizable(False, False)

    CTkLabel(
        ventana,
        text="Ingresa tu API Key de la NASA:",
        text_color=COLORES["blanco"],
    ).pack(pady=(20, 10))
    entrada_api_key = CTkEntry(
        ventana,
        placeholder_text="API Key",
        fg_color=COLORES["panel"],
        border_color=COLORES["borde"],
        text_color=COLORES["blanco"],
        placeholder_text_color=COLORES["texto_secundario"],
        show="*",
    )
    entrada_api_key.pack(pady=(0, 20), padx=20, fill="x")

    api_key_visible = False

    def alternar_visibilidad_api_key():
        nonlocal api_key_visible
        api_key_visible = not api_key_visible
        entrada_api_key.configure(show="" if api_key_visible else "*")
        boton_mostrar.configure(
            text="Ocultar API" if api_key_visible else "Mostrar API"
        )

    boton_mostrar = CTkButton(
        ventana,
        text="Mostrar API",
        command=alternar_visibilidad_api_key,
        fg_color=COLORES["superficie"],
        hover_color=COLORES["borde"],
        text_color=COLORES["blanco"],
    )
    boton_mostrar.pack(pady=(0, 12))

    def guardar_api_key():
        try:
            ajustes = leer_ajustes()
            ajustes["NASA_API_KEY"] = entrada_api_key.get().strip()
            guardar_ajustes(ajustes)
        except (OSError, ValueError) as error:
            messagebox.showerror("Error", f"No se pudo guardar la API key: {error}", parent=ventana)
            return

        messagebox.showinfo("Éxito", "API Key guardada correctamente.", parent=ventana)
        actualizar_info_api()
        ventana.destroy()

    boton_guardar = CTkButton(
        ventana,
        text="Guardar",
        command=guardar_api_key,
        fg_color=COLORES["morado"],
        hover_color=COLORES["morado_hover"],
        text_color=COLORES["blanco"],
    )
    boton_guardar.pack(pady=(0, 20))

def main():

    prepara_directorios_datos()

    set_appearance_mode("dark")
    app = CTk(fg_color=COLORES["fondo"])
    app.title("NeoWs App")
    app.geometry("1280x800")
    app.minsize(800, 600)

    try:
        cache = cargar_cache(ARCHIVO_CACHE)
    except FileNotFoundError:
        cache = {}
    except (json.JSONDecodeError, CacheFormatError) as error:
        cache = {}
        try:
            respaldo_cache = respaldar_cache_invalido(ARCHIVO_CACHE)
        except OSError as error_respaldo:
            messagebox.showerror(
                "No se pudo respaldar el caché",
                "No se pudo preservar el archivo de caché inválido. "
                "La aplicación se cerrará para evitar sobrescribirlo.\n\n"
                f"Detalle: {error_respaldo}",
                parent=app,
            )
            app.destroy()
            return

        messagebox.showwarning(
            "Caché inválido",
            "El archivo de caché no es válido y se movió a este respaldo:\n"
            f"{respaldo_cache}\n\nSe iniciará un caché vacío.\n\nDetalle: {error}",
            parent=app,
        )

    app.grid_columnconfigure(0, weight=0, minsize=280)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)

    entrada_inicial, entrada_final, boton_consultar, boton_exportar, boton_api_key = panel_izquierdo(app)
    (
        tabla_resultados,
        tabs_zona_central,
        pestanas_graficas,
        contenedor_graficas_fechas,
        contenedor_graficas_distancia_tamano,
        contenedor_graficas_nivel_amenaza,
    ) = zona_central(app)
    usuario, api_key, limite, estado = barra_inferior(app)

    def refrescar_info_api():
        actualizar_info_api(api_key, limite)

    try:
        refrescar_info_api()
    except (OSError, ValueError) as error:
        api_key.configure(text="API Key: No disponible")
        limite.configure(text="Revisa settings.json")
        messagebox.showwarning(
            "Ajustes inválidos",
            "No se pudo leer settings.json. La ventana se abrirá, pero debes "
            "corregir el archivo manualmente antes de consultar. No se "
            f"sobrescribió el archivo.\n\nDetalle: {error}",
            parent=app,
        )

    resultados_pendientes = Queue()
    resultados_actuales = []
    animacion_consulta = {}

    boton_consultar.configure(command=lambda: consultar(
        app,
        entrada_inicial,
        entrada_final,
        boton_consultar,
        cache,
        estado,
        resultados_pendientes,
        animacion_consulta,
    ))

    boton_api_key.configure(command=lambda: ventana_api_key(app, refrescar_info_api))

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
    graficas_por_pestana = {}
    animaciones_figuras = {}
    opacidades_originales_graficas = {}
    animacion_tabla = {}

    def actualizar_graficas(fechas, conteos, resultados):
        for identificador, despues_id in tuple(animaciones_figuras.items()):
            app.after_cancel(despues_id)
            del animaciones_figuras[identificador]
        lienzos_graficas.clear()
        graficas_por_pestana.clear()
        opacidades_originales_graficas.clear()
        contenedores = (
            contenedor_graficas_fechas,
            contenedor_graficas_distancia_tamano,
            contenedor_graficas_nivel_amenaza,
        )
        nombres_pestanas = (
            "Por fecha",
            "Distancia y tamaño",
            "Nivel de amenaza",
        )
        figuras = (
            grafica_por_fecha(fechas, conteos),
            grafica_distancia_vs_tamano(resultados),
            grafica_peligrosos_no_peligrosos(resultados),
        )

        for nombre, contenedor, figura in zip(
            nombres_pestanas,
            contenedores,
            figuras,
        ):
            for widget in contenedor.winfo_children():
                widget.destroy()

            figura.set_size_inches(7, 4.5)
            aplicar_tema_figura(figura)
            lienzo = FigureCanvasTkAgg(figura, master=contenedor)
            lienzo.draw()
            lienzo.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
            lienzos_graficas.append(lienzo)
            graficas_por_pestana[nombre] = (figura, lienzo)

    def animar_grafica_seleccionada():
        grafica = graficas_por_pestana.get(pestanas_graficas.get())
        if grafica is not None:
            figura, lienzo = grafica
            animar_figura(
                app,
                figura,
                lienzo,
                animaciones_figuras,
                opacidades_originales_graficas,
            )

    def animar_pestana_principal():
        if tabs_zona_central.get() == "Resultados":
            animar_tabla(app, tabla_resultados, animacion_tabla)
        else:
            animar_grafica_seleccionada()

    tabs_zona_central.configure(command=animar_pestana_principal)
    pestanas_graficas.configure(command=animar_grafica_seleccionada)

    def procesar_resultados():
        try:
            tipo, datos_resultado, mensaje = resultados_pendientes.get_nowait()
        except Empty:
            app.after(100, procesar_resultados)
            return

        detener_animacion_consulta(app, animacion_consulta)

        if tipo == "success":
            for identificador, despues_id in tuple(animacion_tabla.items()):
                app.after_cancel(despues_id)
                del animacion_tabla[identificador]

        aplicar_resultado_consulta(
            tipo,
            datos_resultado,
            mensaje,
            tabla_resultados,
            resultados_actuales,
            actualizar_graficas,
            tabs_zona_central,
            boton_consultar,
            estado,
        )
        if tipo == "success":
            animar_tabla(app, tabla_resultados, animacion_tabla)
        app.after(100, procesar_resultados)

    app.after(100, procesar_resultados)

    app.mainloop()

if __name__ == "__main__":
    main()