import csv
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import Neows

from neo_app.procesamiento import construir_datos
from neo_app.graficas import grafica_peligrosos_no_peligrosos
from neo_app.fechas import solicitar_fechas, validar_rango

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from neo_app.exportacion import exportar_a_csv


class FlujoCacheTests(unittest.TestCase):
    def test_main_crea_directorio_datos_si_no_existe(self):
        with tempfile.TemporaryDirectory() as directorio_temporal:
            directorio_datos = Path(directorio_temporal) / "datos"
            self.assertFalse(directorio_datos.exists())

            with (
                patch("builtins.input", return_value="5"),
                patch.object(Neows, "DIRECTORIO_DATOS", directorio_datos),
                patch.object(Neows, "cargar_cache", return_value={}),
            ):
                Neows.main()

            self.assertTrue(directorio_datos.is_dir())

    def test_consulta_exitosa_deja_respuesta_disponible_para_opcion_dos(self):
        respuesta_cruda = {"near_earth_objects": {"2024-05-20": []}}

        with (
            patch("builtins.input", side_effect=["1", "2", "5"]),
            patch.object(Neows, "cargar_cache", return_value={}),
            patch.object(
                Neows, "solicitar_fechas",
                return_value=("2024-05-20", "2024-05-20"),
            ),
            patch.object(Neows, "peticion", return_value=respuesta_cruda),
            patch.object(Neows, "guardar_cache"),
            patch.object(Neows, "construir_datos", return_value=([], [], [])) as construir,
            patch.object(Neows, "mostrar_resultados"),
        ):
            Neows.main()

        construir.assert_called_once_with(respuesta_cruda)

    def test_consulta_rango_vencido_durante_sesion_actualiza_cache(self):
        fecha_futura = (date.today() + timedelta(days=1)).isoformat()
        clave = (fecha_futura, fecha_futura)
        cache_vencido = {
            clave: {
                "respuesta": {"dato": "antiguo"},
                "guardado_en": (
                    datetime.now().astimezone() - timedelta(hours=13)
                ).isoformat(),
            }
        }
        respuesta_nueva = {"dato": "nuevo"}

        with (
            patch("builtins.input", side_effect=["1", "5"]),
            patch.object(Neows, "cargar_cache", return_value=cache_vencido),
            patch.object(
                Neows, "solicitar_fechas",
                return_value=(fecha_futura, fecha_futura),
            ),
            patch.object(Neows, "peticion", return_value=respuesta_nueva) as peticion,
            patch.object(Neows, "guardar_cache") as guardar,
        ):
            Neows.main()

        peticion.assert_called_once_with(fecha_futura, fecha_futura)
        self.assertEqual(guardar.call_count, 2)
        cache_guardado = guardar.call_args.args[0]
        self.assertEqual(cache_guardado[clave]["respuesta"], respuesta_nueva)


class ObtenerDatosTests(unittest.TestCase):
    def test_usa_entrada_vigente_del_cache(self):
        fecha = date.today().isoformat()
        respuesta = {"dato": "cache"}
        cache = {
            (fecha, fecha): {
                "respuesta": respuesta,
                "guardado_en": datetime.now().astimezone().isoformat(),
            }
        }

        with (
            patch.object(Neows, "peticion") as peticion,
            patch.object(Neows, "guardar_cache") as guardar_cache,
            patch("builtins.print") as imprimir,
            patch("builtins.input") as leer_entrada,
        ):
            datos, desde_cache = Neows.obtener_datos(fecha, fecha, cache)

        self.assertIs(datos, respuesta)
        self.assertTrue(desde_cache)
        peticion.assert_not_called()
        guardar_cache.assert_not_called()
        imprimir.assert_not_called()
        leer_entrada.assert_not_called()

    def test_consulta_api_y_guarda_rango_ausente_en_cache(self):
        fecha = date.today().isoformat()
        respuesta = {"dato": "api"}
        cache = {}

        with (
            patch.object(Neows, "peticion", return_value=respuesta) as peticion,
            patch.object(Neows, "guardar_cache") as guardar_cache,
        ):
            datos, desde_cache = Neows.obtener_datos(fecha, fecha, cache)

        self.assertIs(datos, respuesta)
        self.assertFalse(desde_cache)
        peticion.assert_called_once_with(fecha, fecha)
        guardar_cache.assert_called_once_with(
            cache,
            Neows.DIRECTORIO_DATOS / "cache_neows.json",
        )
        self.assertEqual(cache[(fecha, fecha)]["respuesta"], respuesta)

    def test_consulta_api_y_actualiza_entrada_vencida(self):
        fecha = date.today().isoformat()
        respuesta = {"dato": "nuevo"}
        cache = {
            (fecha, fecha): {
                "respuesta": {"dato": "antiguo"},
                "guardado_en": (
                    datetime.now().astimezone() - timedelta(hours=13)
                ).isoformat(),
            }
        }

        with (
            patch.object(Neows, "peticion", return_value=respuesta) as peticion,
            patch.object(Neows, "guardar_cache") as guardar_cache,
        ):
            datos, desde_cache = Neows.obtener_datos(fecha, fecha, cache)

        self.assertIs(datos, respuesta)
        self.assertFalse(desde_cache)
        peticion.assert_called_once_with(fecha, fecha)
        self.assertEqual(guardar_cache.call_count, 2)
        self.assertEqual(cache[(fecha, fecha)]["respuesta"], respuesta)

    def test_propaga_error_de_red_sin_guardar_cache(self):
        fecha = date.today().isoformat()
        cache = {}

        with (
            patch.object(
                Neows,
                "peticion",
                side_effect=Neows.requests.exceptions.ConnectionError("sin conexión"),
            ),
            patch.object(Neows, "guardar_cache") as guardar_cache,
        ):
            with self.assertRaises(Neows.requests.exceptions.ConnectionError):
                Neows.obtener_datos(fecha, fecha, cache)

        guardar_cache.assert_not_called()
        self.assertNotIn((fecha, fecha), cache)

    def test_fallo_al_guardar_avisa_y_devuelve_datos_de_api(self):
        fecha = date.today().isoformat()
        respuesta = {"dato": "api"}
        cache = {}

        with (
            patch.object(Neows, "peticion", return_value=respuesta),
            patch.object(Neows, "guardar_cache", side_effect=OSError("disco lleno")),
            self.assertLogs("Neows", level="WARNING") as avisos,
        ):
            datos, desde_cache = Neows.obtener_datos(fecha, fecha, cache)

        self.assertIs(datos, respuesta)
        self.assertFalse(desde_cache)
        self.assertEqual(cache[(fecha, fecha)]["respuesta"], respuesta)
        self.assertTrue(any("disco lleno" in aviso for aviso in avisos.output))


class SolicitarFechasTests(unittest.TestCase):
    def test_fecha_final_vacia_consulta_solo_la_fecha_inicial(self):
        with patch("builtins.input", side_effect=["2024-05-20", ""]):
            fecha, fecha_final = solicitar_fechas()

        self.assertEqual(fecha, "2024-05-20")
        self.assertEqual(fecha_final, "2024-05-20")
        self.assertIsInstance(fecha_final, str)

    def test_recorte_a_siete_dias_devuelve_fecha_final_como_texto(self):
        with patch("builtins.input", side_effect=["2024-05-20", "2024-06-20"]):
            fecha, fecha_final = solicitar_fechas()

        self.assertEqual(fecha, "2024-05-20")
        self.assertEqual(fecha_final, "2024-05-27")
        self.assertIsInstance(fecha_final, str)


class ValidarRangoTests(unittest.TestCase):
    def test_formato_de_fecha_invalido_lanza_value_error(self):
        with self.assertRaises(ValueError):
            validar_rango("2024-5-20", "2024-05-21")

    def test_fecha_final_anterior_al_inicio_lanza_value_error(self):
        with self.assertRaises(ValueError):
            validar_rango("2024-05-20", "2024-05-19")

    def test_recorta_rango_mayor_a_siete_dias(self):
        resultado = validar_rango("2024-05-20", "2024-06-20")

        self.assertEqual(resultado, ("2024-05-20", "2024-05-27", True))


class ConstruirDatosTests(unittest.TestCase):
    def test_maneja_campos_faltantes_y_datos_de_aproximacion_vacios(self):
        data = {
            "near_earth_objects": {
                "2024-01-01": [
                    {
                        "name": "Asteroide completo",
                        "estimated_diameter": {
                            "kilometers": {"estimated_diameter_max": 0.2}
                        },
                        "is_potentially_hazardous_asteroid": True,
                        "close_approach_data": [
                            {
                                "miss_distance": {"kilometers": "1000"},
                                "relative_velocity": {
                                    "kilometers_per_hour": "20000"
                                },
                            }
                        ],
                    },
                    {"name": "Asteroide incompleto"},
                ]
            }
        }

        resultados, fechas, conteos = construir_datos(data)

        self.assertEqual(fechas, ["2024-01-01"])
        self.assertEqual(conteos, [2])
        self.assertEqual(resultados[0]["Estimated_Diameter_(Km)"], 0.2)
        self.assertIs(resultados[0]["Threat_Level"], True)
        self.assertEqual(resultados[0]["Close_Approach_Distance_(km)"], 1000.0)
        self.assertIsNone(resultados[1]["Estimated_Diameter_(Km)"])
        self.assertIsNone(resultados[1]["Threat_Level"])
        self.assertIsNone(resultados[1]["Close_Approach_Distance_(km)"])
        self.assertIsNone(resultados[1]["Close_Approach_Velocity_(km/h)"])


class ConstruccionGraficaTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_grafica_peligrosos_y_no_peligrosos_devuelve_barras_conteo(self):
        resultados = [
            {"Threat_Level": True},
            {"Threat_Level": True},
            {"Threat_Level": False},
            {"Threat_Level": None},
        ]

        figura = grafica_peligrosos_no_peligrosos(resultados)
        ejes = figura.axes[0]

        self.assertEqual(
            [barra.get_height() for barra in ejes.patches],
            [2, 1],
        )
        self.assertEqual(
            [etiqueta.get_text() for etiqueta in ejes.get_xticklabels()],
            ["Peligrosos", "No Peligrosos"],
        )

    def test_mostrar_figura_conecta_la_figura_al_backend_de_pyplot(self):
        figura = Figure()

        with patch.object(Neows.plt, "show") as mostrar:
            Neows.mostrar_figura(figura)

        self.assertIs(plt.gcf(), figura)
        mostrar.assert_called_once_with()

    def test_submenu_invoca_cada_grafica_y_muestra_su_figura(self):
        figura = plt.figure()
        fechas = ["2024-01-01"]
        conteos = [1]
        resultados = [{"Threat_Level": True}]

        with (
            patch("builtins.input", side_effect=["1", "2", "3", "4"]),
            patch.object(
                Neows,
                "grafica_por_fecha",
                return_value=figura,
            ) as grafica_fecha,
            patch.object(
                Neows,
                "grafica_distancia_vs_tamaño",
                return_value=figura,
            ) as grafica_distancia,
            patch.object(
                Neows,
                "grafica_peligrosos_no_peligrosos",
                return_value=figura,
            ) as grafica_peligrosos,
            patch.object(Neows.plt, "show") as mostrar,
        ):
            Neows.menu_graficas(fechas, conteos, resultados)

        grafica_fecha.assert_called_once_with(fechas, conteos)
        grafica_distancia.assert_called_once_with(resultados)
        grafica_peligrosos.assert_called_once_with(resultados)
        self.assertEqual(mostrar.call_count, 3)


class ExportacionCsvTests(unittest.TestCase):
    def test_exporta_resultados_con_encabezados_y_datos(self):
        resultados = [
            {
                "Fecha": "2024-01-01",
                "Name": "Asteroide de prueba",
                "Estimated_Diameter_(Km)": 0.25,
                "Threat_Level": True,
                "Close_Approach_Distance_(km)": 1250.0,
                "Close_Approach_Velocity_(km/h)": 18000.0,
            }
        ]

        with tempfile.TemporaryDirectory() as directorio:
            archivo_csv = Path(directorio) / "resultados.csv"
            exportar_a_csv(resultados, str(archivo_csv))

            with archivo_csv.open(newline="", encoding="utf-8") as archivo:
                filas = list(csv.DictReader(archivo))

        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["Fecha Asteroide"], "2024-01-01")
        self.assertEqual(filas[0]["Name"], "Asteroide de prueba")
        self.assertEqual(filas[0]["Estimated_Diameter_(Km)"], "0.25")
        self.assertEqual(filas[0]["Threat_Level"], "True")
        self.assertTrue(filas[0]["Fecha Importación"])


if __name__ == "__main__":
    unittest.main()
