import asyncio
import json
import logging
import flet as ft
from datetime import datetime
from requests.exceptions import RequestException

from neo_app.api import LimiteApiError
from neo_app.cache import CacheFormatError, cargar_cache, respaldar_cache_invalido
from neo_app.config import (
    ARCHIVO_CACHE,
    AjustesInvalidosError,
    prepara_directorios_datos,
)
from neo_app.consulta_flet import consultar_en_segundo_plano
from neo_app.fechas import validar_rango
from neo_app.exportacion import crear_csv_bytes
from neo_app.presentacion_flet import (
    crear_grafica_data_uri,
    crear_tarjetas_resultados,
    crear_tabla_resultados,
)


BACKGROUND = "#030817"
PANEL = "#081833"
PANEL_LIGHT = "#10244A"
BLUE = "#0866FF"
BLUE_LIGHT = "#65A8FF"
TEXT = "#F4F7FF"
MUTED = "#B6C8E8"
BORDER = "#244D91"


logger = logging.getLogger(__name__)


def main(page: ft.Page):
    page.title = "NASA Asteroid Explorer"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BACKGROUND
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    breakpoints = {"phone": 0, "tablet": 600, "desktop": 1000}
    responsive_columns = {
        "phone": 12,
        "tablet": 6,
        "desktop": 6,
    }

    status_text = ft.Text(
        "Selecciona un rango de fechas para consultar.",
        color=MUTED,
        size=13,
        text_align=ft.TextAlign.CENTER,
    )
    cache = {}
    datos_actuales = {
        "resultados": [],
        "fechas_grafica": [],
        "conteos": [],
        "graficas": {},
        "consulta_realizada": False,
        "fecha_inicio": None,
        "fecha_final": None,
    }
    api_key_sesion = {"valor": None}
    selector_archivo = ft.FilePicker()
    page.services.append(selector_archivo)
    cache_listo = True
    try:
        prepara_directorios_datos()
        try:
            cache = cargar_cache(ARCHIVO_CACHE)
        except FileNotFoundError:
            pass
    except (json.JSONDecodeError, CacheFormatError) as error:
        try:
            respaldo_cache = respaldar_cache_invalido(ARCHIVO_CACHE)
        except OSError as error_respaldo:
            cache_listo = False
            status_text.value = (
                "No se pudo preservar el caché inválido; la consulta está "
                f"deshabilitada. Detalle: {error_respaldo}"
            )
        else:
            status_text.value = (
                "El caché inválido se movió a "
                f"{respaldo_cache}. Se iniciará uno nuevo. Detalle: {error}"
            )
    except OSError as error:
        cache_listo = False
        status_text.value = (
            f"No se pudieron preparar los datos de la aplicación: {error}"
        )

    start_date_text = ft.Text("Seleccionar fecha", color=TEXT, size=16)
    end_date_text = ft.Text("Seleccionar fecha", color=TEXT, size=16)

    def update_date_label(date_picker: ft.DatePicker, label: ft.Text):
        if date_picker.value is not None:
            label.value = date_picker.value.strftime("%Y-%m-%d")
            page.update()

    start_date_picker = ft.DatePicker(
        current_date=datetime.now(),
        first_date=datetime(1990, 1, 1),
        last_date=datetime(2050, 12, 31),
        help_text="Selecciona la fecha inicial",
        cancel_text="Cancelar",
        confirm_text="Aceptar",
        on_change=lambda _: update_date_label(
            start_date_picker, start_date_text
        ),
    )
    end_date_picker = ft.DatePicker(
        current_date=datetime.now(),
        first_date=datetime(1990, 1, 1),
        last_date=datetime(2050, 12, 31),
        help_text="Selecciona la fecha final",
        cancel_text="Cancelar",
        confirm_text="Aceptar",
        on_change=lambda _: update_date_label(end_date_picker, end_date_text),
    )

    def make_date_card(
        title: str, selected_date: ft.Text, date_picker: ft.DatePicker
    ) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CALENDAR_MONTH,
                        color=BLUE_LIGHT,
                        size=28,
                    ),
                    ft.Column(
                        [
                            ft.Text(title, color=MUTED, size=13),
                            selected_date,
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=MUTED),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=PANEL_LIGHT,
            border=ft.Border.all(1, BORDER),
            border_radius=18,
            padding=14,
            ink=True,
            on_click=lambda _: page.show_dialog(date_picker),
        )

    empty_state = ft.Column(
        [
            ft.Icon(ft.Icons.EVENT, color=BLUE_LIGHT, size=86),
            ft.Text(
                "Selecciona una fecha\npara consultar",
                color=TEXT,
                size=25,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "Los asteroides aparecerán aquí.",
                color=MUTED,
                size=14,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
    )
    table_placeholder_text = ft.Text(
        "Los resultados de la consulta aparecerán aquí.",
        color=TEXT,
        size=16,
        text_align=ft.TextAlign.CENTER,
    )
    table_view = ft.Column(
        [
            ft.Icon(ft.Icons.TABLE_VIEW, color=BLUE_LIGHT, size=64),
            table_placeholder_text,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=14,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    def actualizar_tabla():
        table_view.controls.clear()
        resultados = datos_actuales["resultados"]
        if not resultados:
            table_view.alignment = ft.MainAxisAlignment.CENTER
            table_view.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            table_view.controls.extend(
                [
                    ft.Icon(ft.Icons.TABLE_VIEW, color=BLUE_LIGHT, size=64),
                    ft.Text(
                        "No se encontraron asteroides en ese rango.",
                        color=TEXT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ]
            )
        elif page.width is not None and page.width < 900:
            table_view.controls.extend(
                crear_tarjetas_resultados(resultados)
            )
            table_view.alignment = ft.MainAxisAlignment.START
            table_view.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        else:
            tabla = crear_tabla_resultados(resultados)
            table_view.controls.append(
                ft.Row(
                    [tabla],
                    scroll=ft.ScrollMode.AUTO,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )
            table_view.alignment = ft.MainAxisAlignment.START
            table_view.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    chart_display = ft.Container(
        content=ft.Text(
            "Realiza una consulta y selecciona una gráfica.",
            color=MUTED,
            text_align=ft.TextAlign.CENTER,
        ),
        height=300,
        alignment=ft.Alignment.CENTER,
        expand=True,
    )

    chart_buttons = {}
    chart_specs = (
        ("fecha", "Por fecha", "Distribución de asteroides por fecha"),
        (
            "distancia_tamano",
            "Distancia / tamaño",
            "Distancia de aproximación frente al diámetro estimado",
        ),
        (
            "peligrosidad",
            "Peligrosos",
            "Comparación de asteroides potencialmente peligrosos",
        ),
    )
    chart_buttons_row = ft.ResponsiveRow(
        [
            ft.Container(
                content=ft.Button(
                    label,
                    color=TEXT,
                    bgcolor=PANEL_LIGHT,
                    expand=True,
                    tooltip=descripcion,
                ),
                col={"phone": 6, "tablet": 4, "desktop": 4},
            )
            for _, label, descripcion in chart_specs
        ],
        columns=12,
        breakpoints=breakpoints,
        spacing=8,
        run_spacing=8,
    )
    chart_buttons = {
        tipo: control.content
        for (tipo, _, _), control in zip(chart_specs, chart_buttons_row.controls)
    }

    charts_view = ft.Column(
        [chart_buttons_row, chart_display],
        spacing=10,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    async def seleccionar_grafica(tipo):
        if not datos_actuales["consulta_realizada"]:
            chart_display.content = ft.Text(
                "Primero realiza una consulta para ver las gráficas.",
                color=MUTED,
                text_align=ft.TextAlign.CENTER,
            )
            page.update()
            return

        for graph_type, button in chart_buttons.items():
            button.bgcolor = BLUE if graph_type == tipo else PANEL_LIGHT

        chart_display.content = ft.ProgressRing(color=BLUE_LIGHT)
        page.update()

        try:
            uri = datos_actuales["graficas"].get(tipo)
            if uri is None:
                uri = await asyncio.to_thread(
                    crear_grafica_data_uri,
                    tipo,
                    datos_actuales["fechas_grafica"],
                    datos_actuales["conteos"],
                    datos_actuales["resultados"],
                )
                datos_actuales["graficas"][tipo] = uri
        except Exception as error:
            logger.exception(
                "No se pudo generar la gráfica '%s' (%s).",
                tipo,
                type(error).__name__,
            )
            chart_display.content = ft.Text(
                "No se pudo generar esta gráfica. Inténtalo de nuevo.",
                color=MUTED,
                text_align=ft.TextAlign.CENTER,
            )
            status_text.value = "Error al generar la gráfica."
        else:
            chart_display.content = ft.Image(
                src=uri,
                fit=ft.BoxFit.CONTAIN,
                expand=True,
            )
        finally:
            page.update()

    def crear_manejador_grafica(tipo):
        async def manejar_click(_):
            await seleccionar_grafica(tipo)

        return manejar_click

    for tipo, button in chart_buttons.items():
        button.on_click = crear_manejador_grafica(tipo)

    content_panel = ft.Container(
        content=empty_state,
        bgcolor=PANEL,
        border=ft.Border.all(1, BORDER),
        border_radius=24,
        padding=16,
        height=430,
        alignment=ft.Alignment.CENTER,
    )
    table_button = ft.Button(
        "Tabla",
        icon=ft.Icons.TABLE_VIEW,
        color=TEXT,
        bgcolor=BLUE,
        expand=True,
    )
    charts_button = ft.Button(
        "Gráficas",
        icon=ft.Icons.BAR_CHART,
        color=TEXT,
        bgcolor=PANEL_LIGHT,
        expand=True,
    )

    vista_actual = {"valor": "empty"}

    def select_view(view: str):
        if view == "table":
            if datos_actuales["resultados"]:
                actualizar_tabla()
            content_panel.content = table_view
            table_button.bgcolor = BLUE
            charts_button.bgcolor = PANEL_LIGHT
        else:
            content_panel.content = charts_view
            table_button.bgcolor = PANEL_LIGHT
            charts_button.bgcolor = BLUE
        vista_actual["valor"] = view
        page.update()

    table_button.on_click = lambda _: select_view("table")
    charts_button.on_click = lambda _: select_view("charts")

    api_key_field = ft.TextField(
        label="NASA API Key",
        password=True,
        can_reveal_password=True,
        autofocus=True,
        border_color=BORDER,
        focused_border_color=BLUE_LIGHT,
    )

    def cerrar_configuracion_api(_=None):
        page.pop_dialog()

    api_active=ft.Text("Configure Su clave", color=MUTED, size=13, text_align=ft.TextAlign.CENTER)
    
    def clave_activa():
        if api_key_sesion["valor"]:
            return "Clave personal (esta sesión)"
        return "DEMO_KEY"

    api_active.value = f"Clave usada: {clave_activa()}"
    
    def guardar_api_key_sesion(_):
        api_key = api_key_field.value.strip() if api_key_field.value else ""
        api_key_sesion["valor"] = api_key or None
        api_active.value = f"Clave usada: {clave_activa()}"
        status_text.value = (
            "La clave se usará solo durante esta sesión de Flet; "
            "todavía no se guarda."
        )
        cerrar_configuracion_api()
        page.update()

    api_key_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Configurar NASA API Key"),
        content=ft.Column(
            [
                api_key_field,
                ft.TextButton(
                    "Solicitar API Key gratis en NASA",
                    url="https://api.nasa.gov/",
                ),
                ft.Text(
                    "“Se envía al servidor de esta aplicación solo para hacer la consulta "
                    "No se guarda en el archivo de ajustes.",
                    color=MUTED,
                    size=13,
                ),
            ],
            tight=True,
            spacing=12,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=cerrar_configuracion_api),
            ft.Button(
                "Usar clave",
                on_click=guardar_api_key_sesion,
                bgcolor=BLUE,
                color=TEXT,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def abrir_configuracion_api(_):
        api_key_field.value = api_key_sesion["valor"] or ""
        page.show_dialog(api_key_dialog)

    settings_button = ft.Button(
        "Configurar API Key",
        icon=ft.Icons.KEY,
        color=TEXT,
        bgcolor=PANEL_LIGHT,
        expand=True,
        on_click=abrir_configuracion_api,
    )
    mobile_menu = ft.PopupMenuButton(
        icon=ft.Icons.MENU,
        icon_color=TEXT,
        tooltip="Abrir menú",
        items=[
            ft.PopupMenuItem(
                content="Tabla",
                icon=ft.Icons.TABLE_VIEW,
                on_click=lambda _: select_view("table"),
            ),
            ft.PopupMenuItem(
                content="Gráficas",
                icon=ft.Icons.BAR_CHART,
                on_click=lambda _: select_view("charts"),
            ),
            ft.PopupMenuItem(
                content="Configurar API Key",
                icon=ft.Icons.KEY,
                on_click=abrir_configuracion_api,
            ),
        ],
    )
    query_button = ft.Button(
        "Consultar",
        icon=ft.Icons.SEARCH,
        color=TEXT,
        bgcolor=BLUE,
        height=58,
        expand=True,
        disabled=not cache_listo,
    )
    export_button = ft.Button(
        "Exportar CSV",
        icon=ft.Icons.DOWNLOAD,
        color=TEXT,
        bgcolor=PANEL_LIGHT,
        height=58,
        expand=True,
        disabled=True,
    )
    api_status_dot=ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.GREEN, size=12)
    api_status_text=ft.Text("Listo",color=MUTED, size=13, text_align=ft.TextAlign.CENTER,)

    ESTADOS_API = {
    "api": ("Éxito", ft.Colors.GREEN),
    "cache": ("Éxito", ft.Colors.GREEN),
    "error": ("Error", ft.Colors.RED),
    }

    def mostrar_estado_api(estado):
        texto, color = ESTADOS_API[estado]
        api_status_text.value = texto
        api_status_dot.color = color
        page.update()

    async def puntos(etiqueta):
        n = 0
        while True:
            n = n % 3 + 1
            api_status_text.value = f"{etiqueta}{'.' * n}"
            api_status_dot.color = BLUE_LIGHT
            page.update()
            await asyncio.sleep(0.4)

    async def consultar(_):
        if not cache_listo:
            status_text.value = (
                "La consulta está deshabilitada porque no se pudo preparar "
                "el caché."
            )
            page.update()
            return

        if start_date_picker.value is None:
            status_text.value = "Error: selecciona una fecha inicial."
            page.update()
            return

        fecha_inicial = start_date_picker.value.strftime("%Y-%m-%d")
        fecha_final_texto = (
            end_date_picker.value.strftime("%Y-%m-%d")
            if end_date_picker.value is not None
            else fecha_inicial
        )
        try:
            fecha, fecha_final, fecha_recortada = validar_rango(
                fecha_inicial,
                fecha_final_texto,
            )
        except ValueError as error:
            status_text.value = f"Error de validación: {error}"
            page.update()
            return

        if fecha_recortada:
            end_date_picker.value = datetime.fromisoformat(fecha_final)
            end_date_text.value = fecha_final

        query_button.disabled = True
        estado_final = "error"
        page.update()

        tarea = asyncio.create_task(puntos("Consultando"))

        try:
            api_key_consulta = api_key_sesion["valor"]
            if page.web and api_key_consulta is None:
                api_key_consulta = "DEMO_KEY"
            (
                resultados,
                datos_actuales["fechas_grafica"],
                datos_actuales["conteos"],
                desde_cache,
                es_demo,
            ) = await consultar_en_segundo_plano(
                fecha,
                fecha_final,
                cache,
                ARCHIVO_CACHE,
                api_key=api_key_consulta,
            )
            datos_actuales["resultados"] = resultados
            datos_actuales["consulta_realizada"] = True
            datos_actuales["fecha_inicio"] = fecha
            datos_actuales["fecha_final"] = fecha_final
        except LimiteApiError as error:
            status_text.value = f"Error: {error}"
        except RequestException as error:
            status_text.value = f"Error de red: {error}"
        except AjustesInvalidosError as error:
            status_text.value = f"Los ajustes son inválidos: {error}"
        except ValueError as error:
            status_text.value = f"Error al procesar la respuesta: {error}"
        except (KeyError, TypeError) as error:
            status_text.value = (
                f"La respuesta de NASA tiene un formato inesperado: {error}"
            )
        except Exception as error:
            logger.error(
                "Error inesperado durante la consulta Flet (%s).",
                type(error).__name__,
            )
            status_text.value = (
                "Ocurrió un error inesperado durante la consulta. "
                "Revisa la configuración e inténtalo de nuevo."
            )
        else:
            estado_final = "cache" if desde_cache else "api"
            origen = "cache" if desde_cache else "API"
            mensaje = (
                f"Consulta exitosa: {len(resultados)} asteroide(s), "
                f"datos desde {origen}."
            )
            if fecha_recortada:
                mensaje += f" Rango recortado a {fecha} - {fecha_final}."

            actualizar_tabla()
            export_button.disabled = not resultados
            datos_actuales["graficas"].clear()
            chart_display.content = ft.Text(
                "Selecciona una gráfica para visualizarla.",
                color=MUTED,
                text_align=ft.TextAlign.CENTER,
            )
            for button in chart_buttons.values():
                button.bgcolor = PANEL_LIGHT
            status_text.value = mensaje
            select_view("table")
        finally:
            tarea.cancel()
            try:
                await tarea
            except asyncio.CancelledError:
                pass

            mostrar_estado_api(estado_final)
            query_button.disabled = False
            page.update()

    query_button.on_click = consultar

    async def exportar(_):
        resultados = datos_actuales["resultados"]
        if not resultados:
            status_text.value = (
                "No hay resultados para exportar. Realiza una consulta primero."
            )
            page.update()
            return

        export_button.disabled = True
        status_text.value = "Preparando el archivo CSV…"
        page.update()

        try:
            contenido = await asyncio.to_thread(crear_csv_bytes, resultados)
            if contenido is None:
                status_text.value = (
                    "No hay resultados para exportar. Realiza una consulta primero."
                )
                return

            nombre_archivo = (
                f"asteroides_{datos_actuales['fecha_inicio']}_"
                f"{datos_actuales['fecha_final']}.csv"
            )
            ruta_guardada = await selector_archivo.save_file(
                dialog_title="Guardar resultados como CSV",
                file_name=nombre_archivo,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
                src_bytes=contenido,
            )
        except Exception as error:
            logger.exception(
                "No se pudo exportar la consulta a CSV (%s).",
                type(error).__name__,
            )
            status_text.value = (
                f"No se pudo exportar el archivo CSV: {error}"
            )
        else:
            if ruta_guardada:
                status_text.value = f"CSV exportado en: {ruta_guardada}"
            elif page.web or page.platform.is_mobile():
                status_text.value = (
                    f"Se inició la descarga de {nombre_archivo}."
                )
            else:
                status_text.value = "Exportación cancelada."
        finally:
            export_button.disabled = not datos_actuales["resultados"]
            page.update()

    export_button.on_click = exportar

    header = ft.Row(
        [
            ft.Container(
                content=ft.Icon(
                    ft.Icons.ROCKET_LAUNCH,
                    color=TEXT,
                    size=32,
                ),
                width=58,
                height=58,
                bgcolor=BLUE,
                border_radius=29,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Column(
                [
                    ft.Text(
                        "NASA Asteroid Explorer",
                        color=TEXT,
                        size=22,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        "Explora asteroides cercanos a la Tierra",
                        color=MUTED,
                        size=13,
                    ),
                ],
                spacing=2,
                expand=True,
            ),
            mobile_menu,
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
    )
    desktop_navigation = ft.Row(
        [table_button, charts_button, settings_button],
        spacing=10,
    )

    def update_navigation_visibility(_=None):
        is_mobile = page.width is not None and page.width < 600
        mobile_menu.visible = is_mobile
        desktop_navigation.visible = not is_mobile
        if vista_actual["valor"] == "table" and datos_actuales["resultados"]:
            actualizar_tabla()
        page.update()

    page.on_resize = update_navigation_visibility

    date_controls = ft.ResponsiveRow(
        [
            ft.Container(
                content=make_date_card(
                    "Desde", start_date_text, start_date_picker
                ),
                col=responsive_columns,
            ),
            ft.Container(
                content=make_date_card("Hasta", end_date_text, end_date_picker),
                col=responsive_columns,
            ),
        ],
        columns=12,
        breakpoints=breakpoints,
        spacing=12,
        run_spacing=12,
    )
    action_controls = ft.ResponsiveRow(
        [
            ft.Container(content=query_button, col=responsive_columns),
            ft.Container(content=export_button, col=responsive_columns),
        ],
        columns=12,
        breakpoints=breakpoints,
        spacing=12,
        run_spacing=12,
    )
   
    connection_status = ft.ResponsiveRow(
        [
            ft.Container(
                content=ft.Row(
                    [
                        api_status_dot,
                        api_status_text
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
                col=responsive_columns,
            ),
            ft.Container(
                content=ft.Row(
                    [
                        api_active,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                col=responsive_columns,
            ),
        ],
        columns=12,
        breakpoints=breakpoints,
        spacing=8,
        run_spacing=8,
    )

    page.add(
        ft.Container(
            expand=True,
            padding=18,
            content=ft.Column(
                [
                    header,
                    desktop_navigation,
                    content_panel,
                    date_controls,
                    action_controls,
                    ft.Container(
                        content=status_text,
                        alignment=ft.Alignment.CENTER,
                        padding=8,
                    ),
                    ft.Container(
                        content=connection_status,
                        bgcolor=PANEL,
                        border=ft.Border.all(1, BORDER),
                        border_radius=22,
                        padding=12,
                    ),
                ],
                spacing=14,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )
    )
    update_navigation_visibility()

if __name__ == "__main__":
    ft.run(main)