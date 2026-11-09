import flet as ft
from datetime import datetime


BACKGROUND = "#030817"
PANEL = "#081833"
PANEL_LIGHT = "#10244A"
BLUE = "#0866FF"
BLUE_LIGHT = "#65A8FF"
TEXT = "#F4F7FF"
MUTED = "#B6C8E8"
BORDER = "#244D91"


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
        "Maqueta visual · la consulta todavía no está conectada",
        color=MUTED,
        size=13,
        text_align=ft.TextAlign.CENTER,
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
    table_placeholder = ft.Column(
        [
            ft.Icon(ft.Icons.TABLE_VIEW, color=BLUE_LIGHT, size=64),
            ft.Text(
                "Aquí se mostrarán los resultados en una tabla.",
                color=TEXT,
                size=18,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=14,
    )
    charts_placeholder = ft.Column(
        [
            ft.Icon(ft.Icons.BAR_CHART, color=BLUE_LIGHT, size=64),
            ft.Text(
                "Aquí aparecerán las gráficas de la consulta.",
                color=TEXT,
                size=18,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=14,
    )

    content_panel = ft.Container(
        content=empty_state,
        bgcolor=PANEL,
        border=ft.Border.all(1, BORDER),
        border_radius=24,
        padding=24,
        height=310,
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

    def show_placeholder_status(action: str):
        status_text.value = f"{action}: esta función se conectará en el siguiente paso."
        page.update()

    def select_view(view: str):
        if view == "table":
            content_panel.content = table_placeholder
            table_button.bgcolor = BLUE
            charts_button.bgcolor = PANEL_LIGHT
        else:
            content_panel.content = charts_placeholder
            table_button.bgcolor = PANEL_LIGHT
            charts_button.bgcolor = BLUE
        page.update()

    table_button.on_click = lambda _: select_view("table")
    charts_button.on_click = lambda _: select_view("charts")

    settings_button = ft.Button(
        "Configurar API Key",
        icon=ft.Icons.KEY,
        color=TEXT,
        bgcolor=PANEL_LIGHT,
        expand=True,
        on_click=lambda _: show_placeholder_status("Ajustes"),
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
                on_click=lambda _: show_placeholder_status("Ajustes"),
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
        on_click=lambda _: show_placeholder_status("Consulta"),
    )
    export_button = ft.Button(
        "Exportar CSV",
        icon=ft.Icons.DOWNLOAD,
        color=TEXT,
        bgcolor=PANEL_LIGHT,
        height=58,
        expand=True,
        on_click=lambda _: show_placeholder_status("Exportación CSV"),
    )

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
                        ft.Icon(
                            ft.Icons.CIRCLE,
                            color=ft.Colors.GREEN,
                            size=12,
                        ),
                        ft.Text("API NASA · estado visual", color=MUTED, size=13),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                col=responsive_columns,
            ),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.KEY, color=BLUE_LIGHT, size=18),
                        ft.Text("Clave: DEMO_KEY", color=MUTED, size=13),
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


ft.run(main)