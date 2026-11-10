import base64
from io import BytesIO

import flet as ft
from matplotlib.backends.backend_agg import FigureCanvasAgg

from neo_app.graficas import (
    grafica_distancia_vs_tamano,
    grafica_peligrosos_no_peligrosos,
    grafica_por_fecha,
)


COLUMNAS_RESULTADOS = (
    ("Fecha", "Fecha"),
    ("Name", "Nombre"),
    ("Estimated_Diameter_(Km)", "Diámetro máx. (km)"),
    ("Threat_Level", "Peligroso"),
    ("Close_Approach_Distance_(km)", "Distancia (km)"),
    ("Close_Approach_Velocity_(km/h)", "Velocidad (km/h)"),
)


def _formatear_valor(valor):
    if valor is None:
        return "—"
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    return str(valor)


def crear_tabla_resultados(resultados):
    columnas = [
        ft.DataColumn(
            ft.Text(titulo, weight=ft.FontWeight.BOLD),
            tooltip=titulo,
        )
        for _, titulo in COLUMNAS_RESULTADOS
    ]
    filas = [
        ft.DataRow(
            cells=[
                ft.DataCell(
                    ft.Text(
                        _formatear_valor(resultado.get(campo)),
                        no_wrap=True,
                    )
                )
                for campo, _ in COLUMNAS_RESULTADOS
            ],
        )
        for resultado in resultados
    ]
    return ft.DataTable(
        columns=columnas,
        rows=filas,
        column_spacing=20,
        heading_row_color="#10244A",
        data_row_color="#081833",
        heading_text_style=ft.TextStyle(color="#F4F7FF"),
        data_text_style=ft.TextStyle(color="#F4F7FF"),
        border=ft.Border.all(1, "#244D91"),
        divider_thickness=0.5,
    )


def crear_tarjetas_resultados(resultados):
    tarjetas = []
    for resultado in resultados:
        campos = [
            ("Diámetro máx. (km)", "Estimated_Diameter_(Km)"),
            ("Peligroso", "Threat_Level"),
            ("Distancia (km)", "Close_Approach_Distance_(km)"),
            ("Velocidad (km/h)", "Close_Approach_Velocity_(km/h)"),
        ]
        informacion = ft.ResponsiveRow(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(etiqueta, color="#B6C8E8", size=12),
                            ft.Text(
                                _formatear_valor(resultado.get(campo)),
                                color="#F4F7FF",
                                size=14,
                            ),
                        ],
                        spacing=2,
                    ),
                    col=6,
                )
                for etiqueta, campo in campos
            ],
            columns=12,
            spacing=8,
            run_spacing=8,
        )
        tarjetas.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    _formatear_valor(resultado.get("Name")),
                                    color="#F4F7FF",
                                    weight=ft.FontWeight.BOLD,
                                    expand=True,
                                ),
                                ft.Text(
                                    _formatear_valor(resultado.get("Fecha")),
                                    color="#B6C8E8",
                                    size=12,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        informacion,
                    ],
                    spacing=10,
                ),
                bgcolor="#10244A",
                border=ft.Border.all(1, "#244D91"),
                border_radius=14,
                padding=12,
            )
        )
    return tarjetas


def _aplicar_tema_oscuro(figura):
    figura.set_facecolor("#081833")

    for ejes in figura.axes:
        ejes.set_facecolor("#081833")
        ejes.title.set_color("#F4F7FF")
        ejes.xaxis.label.set_color("#B6C8E8")
        ejes.yaxis.label.set_color("#B6C8E8")
        ejes.tick_params(colors="#B6C8E8")
        ejes.grid(color="#244D91", alpha=0.5)
        for borde in ejes.spines.values():
            borde.set_color("#244D91")
        for coleccion in ejes.collections:
            coleccion.set_color("#65A8FF")


def crear_grafica_data_uri(tipo, fechas, conteos, resultados):
    generadores = {
        "fecha": lambda: grafica_por_fecha(fechas, conteos),
        "distancia_tamano": lambda: grafica_distancia_vs_tamano(resultados),
        "peligrosidad": lambda: grafica_peligrosos_no_peligrosos(resultados),
    }
    try:
        figura = generadores[tipo]()
    except KeyError as error:
        raise ValueError(f"El tipo de gráfica no es válido: {tipo}.") from error

    _aplicar_tema_oscuro(figura)
    figura.tight_layout()

    imagen = BytesIO()
    FigureCanvasAgg(figura).print_png(imagen)
    contenido = base64.b64encode(imagen.getvalue()).decode("ascii")
    return f"data:image/png;base64,{contenido}"
