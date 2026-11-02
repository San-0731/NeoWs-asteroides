import unittest
from queue import Queue
from unittest.mock import Mock, patch

import app
from requests.exceptions import ConnectionError


class EntradaFalsa:
    def __init__(self, valor):
        self.valor = valor

    def get(self):
        return self.valor


class TablaFalsa:
    def __init__(self):
        self.filas = []

    def get_children(self):
        return list(range(len(self.filas)))

    def delete(self, identificador):
        del self.filas[identificador]

    def insert(self, parent, posicion, values):
        self.filas.append(values)


class ConsultaGuiTests(unittest.TestCase):
    def test_fecha_inicial_vacia_muestra_error_y_no_inicia_hilo(self):
        estado = Mock()
        boton = Mock()

        with patch.object(app, "Thread") as hilo:
            app.consultar(
                Mock(),
                EntradaFalsa(" "),
                EntradaFalsa(""),
                boton,
                {},
                estado,
                Queue(),
            )

        estado.configure.assert_called_once_with(
            text="Error: La fecha inicial es obligatoria."
        )
        boton.configure.assert_not_called()
        hilo.assert_not_called()

    def test_fecha_invalida_muestra_error_y_no_inicia_hilo(self):
        estado = Mock()
        boton = Mock()

        with patch.object(app, "Thread") as hilo:
            app.consultar(
                Mock(),
                EntradaFalsa("fecha-invalida"),
                EntradaFalsa(""),
                boton,
                {},
                estado,
                Queue(),
            )

        self.assertIn("Error de validación:", estado.configure.call_args.kwargs["text"])
        boton.configure.assert_not_called()
        hilo.assert_not_called()

    def test_fecha_valida_inicia_hilo_con_rango_normalizado(self):
        cola = Queue()
        boton = Mock()
        estado = Mock()

        with patch.object(app, "Thread") as hilo:
            app.consultar(
                Mock(),
                EntradaFalsa("2026-10-20"),
                EntradaFalsa(""),
                boton,
                {"cached": "data"},
                estado,
                cola,
            )

        estado.configure.assert_called_once_with(text="Consultando...")
        boton.configure.assert_called_once_with(state="disabled")
        hilo.assert_called_once_with(
            target=app.trabajo_consulta,
            args=("2026-10-20", "2026-10-20", False, {"cached": "data"}, cola),
            daemon=True,
        )
        hilo.return_value.start.assert_called_once_with()

    def test_trabajo_consulta_publica_resultados_y_mensaje_de_origen(self):
        cola = Queue()
        datos = {"near_earth_objects": {}}
        resultados = [{"Name": "asteroide"}]

        with (
            patch.object(app, "obtener_datos", return_value=(datos, False, True)),
            patch.object(
                app,
                "construir_datos",
                return_value=(resultados, ["2026-10-20"], [1]),
            ),
        ):
            app.trabajo_consulta(
                "2026-10-20",
                "2026-10-20",
                True,
                {},
                cola,
            )

        tipo, datos_resultado, mensaje = cola.get_nowait()
        self.assertEqual(tipo, "success")
        self.assertEqual(
            datos_resultado,
            (resultados, ["2026-10-20"], [1]),
        )
        self.assertIn("API", mensaje)
        self.assertIn("DEMO_KEY", mensaje)
        self.assertIn("Rango recortado", mensaje)

    def test_trabajo_consulta_convierte_error_de_red_en_mensaje(self):
        cola = Queue()

        with patch.object(
            app,
            "obtener_datos",
            side_effect=ConnectionError("sin conexión"),
        ):
            app.trabajo_consulta("2026-10-20", "2026-10-20", False, {}, cola)

        tipo, resultado, mensaje = cola.get_nowait()
        self.assertEqual(tipo, "error")
        self.assertIsNone(resultado)
        self.assertIn("Error de red", mensaje)

    def test_trabajo_consulta_convierte_limite_api_en_mensaje(self):
        cola = Queue()

        with patch.object(
            app,
            "obtener_datos",
            side_effect=app.LimiteApiError("límite alcanzado"),
        ):
            app.trabajo_consulta("2026-10-20", "2026-10-20", False, {}, cola)

        tipo, resultado, mensaje = cola.get_nowait()
        self.assertEqual(tipo, "error")
        self.assertIsNone(resultado)
        self.assertIn("límite alcanzado", mensaje)

    def test_aplica_resultado_exitoso_a_tabla_graficas_y_controles(self):
        tabla = TablaFalsa()
        tabla.filas = [("fila anterior",)]
        resultados = []
        graficas = Mock()
        tabs = Mock()
        boton = Mock()
        estado = Mock()
        nuevos_resultados = [
            {
                "Fecha": "2026-10-20",
                "Name": "Asteroide",
                "Estimated_Diameter_(Km)": 0.2,
                "Threat_Level": True,
                "Close_Approach_Distance_(km)": 1200,
                "Close_Approach_Velocity_(km/h)": 18000,
            }
        ]
        datos_resultado = (nuevos_resultados, ["2026-10-20"], [1])

        app.aplicar_resultado_consulta(
            "success",
            datos_resultado,
            "Consulta exitosa",
            tabla,
            resultados,
            graficas,
            tabs,
            boton,
            estado,
        )

        self.assertEqual(resultados, nuevos_resultados)
        self.assertEqual(
            tabla.filas,
            [
                (
                    "2026-10-20",
                    "Asteroide",
                    0.2,
                    True,
                    1200,
                    18000,
                )
            ],
        )
        graficas.assert_called_once_with(["2026-10-20"], [1], nuevos_resultados)
        tabs.set.assert_called_once_with("Resultados")
        estado.configure.assert_called_once_with(text="Consulta exitosa")
        boton.configure.assert_called_once_with(state="normal")

    def test_aplica_error_sin_modificar_resultados_anteriores(self):
        tabla = TablaFalsa()
        tabla.filas = [("fila anterior",)]
        resultados = [{"Name": "previo"}]
        estado = Mock()
        boton = Mock()
        actualizar_graficas = Mock()
        tabs = Mock()

        app.aplicar_resultado_consulta(
            "error",
            None,
            "Error de red",
            tabla,
            resultados,
            actualizar_graficas,
            tabs,
            boton,
            estado,
        )

        self.assertEqual(resultados, [{"Name": "previo"}])
        self.assertEqual(tabla.filas, [("fila anterior",)])
        actualizar_graficas.assert_not_called()
        tabs.set.assert_not_called()
        estado.configure.assert_called_once_with(text="Error de red")
        boton.configure.assert_called_once_with(state="normal")


class EtiquetasApiTests(unittest.TestCase):
    @patch.object(app, "obtener_api_key")
    def test_muestra_limite_demo_sin_mostrar_la_clave(self, obtener_api_key):
        obtener_api_key.return_value = ("DEMO_KEY", True)
        etiqueta_clave = Mock()
        etiqueta_limite = Mock()

        app.actualizar_info_api(etiqueta_clave, etiqueta_limite)

        etiqueta_clave.configure.assert_called_once_with(text="API Key: DEMO_KEY")
        etiqueta_limite.configure.assert_called_once_with(
            text="Límite de peticiones: 30 por hora"
        )

    @patch.object(app, "obtener_api_key")
    def test_muestra_limite_personal_sin_mostrar_la_clave(self, obtener_api_key):
        obtener_api_key.return_value = ("clave-super-secreta", False)
        etiqueta_clave = Mock()
        etiqueta_limite = Mock()

        app.actualizar_info_api(etiqueta_clave, etiqueta_limite)

        etiqueta_clave.configure.assert_called_once_with(text="API Key: Personal")
        etiqueta_limite.configure.assert_called_once_with(
            text="Límite de peticiones: 1.000 por hora"
        )
        self.assertNotIn(
            "clave-super-secreta",
            etiqueta_clave.configure.call_args.kwargs["text"],
        )


class VentanaApiKeyTests(unittest.TestCase):
    def setUp(self):
        self.ventana = Mock()
        self.entrada = Mock()
        self.entrada.get.return_value = " clave-prueba "
        self.boton = Mock()
        self.actualizar_info = Mock()
        self.patches = (
            patch.object(app, "CTkToplevel", return_value=self.ventana),
            patch.object(app, "CTkLabel"),
            patch.object(app, "CTkEntry", return_value=self.entrada),
            patch.object(app, "CTkButton", return_value=self.boton),
            patch.object(app, "messagebox"),
        )
        for mocked in self.patches:
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_guardar_api_key_persiste_ajustes_y_cierra_ventana(self):
        ajustes = {"otro_ajuste": "se conserva", "NASA_API_KEY": ""}
        with (
            patch.object(app, "leer_ajustes", return_value=ajustes),
            patch.object(app, "guardar_ajustes") as guardar,
        ):
            app.ventana_api_key(Mock(), self.actualizar_info)
            accion_guardar = app.CTkButton.call_args.kwargs["command"]
            accion_guardar()

        guardar.assert_called_once_with(
            {"otro_ajuste": "se conserva", "NASA_API_KEY": "clave-prueba"}
        )
        self.actualizar_info.assert_called_once_with()
        self.ventana.destroy.assert_called_once_with()
        app.messagebox.showinfo.assert_called_once()
        app.messagebox.showerror.assert_not_called()

    def test_error_al_guardar_no_muestra_exito_ni_cierra_ventana(self):
        with (
            patch.object(app, "leer_ajustes", return_value={"NASA_API_KEY": ""}),
            patch.object(
                app,
                "guardar_ajustes",
                side_effect=OSError("permiso denegado"),
            ),
        ):
            app.ventana_api_key(Mock(), self.actualizar_info)
            accion_guardar = app.CTkButton.call_args.kwargs["command"]
            accion_guardar()

        app.messagebox.showerror.assert_called_once()
        app.messagebox.showinfo.assert_not_called()
        self.actualizar_info.assert_not_called()
        self.ventana.destroy.assert_not_called()

    def test_ajustes_invalidos_muestran_error_y_no_intentan_guardar(self):
        with (
            patch.object(
                app,
                "leer_ajustes",
                side_effect=ValueError("JSON de ajustes inválido"),
            ),
            patch.object(app, "guardar_ajustes") as guardar,
        ):
            app.ventana_api_key(Mock(), self.actualizar_info)
            accion_guardar = app.CTkButton.call_args.kwargs["command"]
            accion_guardar()

        guardar.assert_not_called()
        app.messagebox.showerror.assert_called_once()
        app.messagebox.showinfo.assert_not_called()
        self.actualizar_info.assert_not_called()
        self.ventana.destroy.assert_not_called()
