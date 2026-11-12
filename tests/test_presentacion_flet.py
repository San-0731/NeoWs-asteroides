import unittest

from neo_app.presentacion_flet import (
    crear_grafica_data_uri,
    crear_tarjetas_resultados,
    crear_tabla_resultados,
)


class PresentacionTablaFletTests(unittest.TestCase):
    def test_crea_tabla_con_columnas_y_valores_de_resultados(self):
        resultados = [
            {
                "Fecha": "2024-05-20",
                "Name": "Asteroide de prueba",
                "Estimated_Diameter_(Km)": 0.42,
                "Threat_Level": True,
                "Close_Approach_Distance_(km)": 1234.5,
                "Close_Approach_Velocity_(km/h)": None,
            }
        ]

        tabla = crear_tabla_resultados(resultados)

        self.assertEqual(len(tabla.columns), 6)
        self.assertEqual(len(tabla.rows), 1)
        valores = [
            celda.content.value
            for celda in tabla.rows[0].cells
        ]
        self.assertEqual(
            valores,
            [
                "2024-05-20",
                "Asteroide de prueba",
                "0.42",
                "Sí",
                "1234.5",
                "—",
            ],
        )

    def test_crea_tabla_vacia_sin_filas(self):
        tabla = crear_tabla_resultados([])

        self.assertEqual(len(tabla.columns), 6)
        self.assertEqual(tabla.rows, [])

    def test_crea_tarjeta_movil_con_datos_de_cada_asteroide(self):
        tarjeta = crear_tarjetas_resultados(
            [
                {
                    "Fecha": "2024-05-20",
                    "Name": "Asteroide móvil",
                    "Estimated_Diameter_(Km)": 0.42,
                    "Threat_Level": False,
                    "Close_Approach_Distance_(km)": 1234.5,
                    "Close_Approach_Velocity_(km/h)": 9000,
                }
            ]
        )[0]

        textos = []
        por_revisar = [tarjeta]
        while por_revisar:
            control = por_revisar.pop()
            if getattr(control, "value", None) is not None:
                textos.append(control.value)
            por_revisar.extend(getattr(control, "controls", []))
            contenido = getattr(control, "content", None)
            if contenido is not None:
                por_revisar.append(contenido)

        self.assertIn("Asteroide móvil", textos)
        self.assertIn("2024-05-20", textos)
        self.assertIn("Diámetro máx. (km)", textos)
        self.assertIn("Peligroso", textos)
        self.assertIn("Distancia (km)", textos)
        self.assertIn("Velocidad (km/h)", textos)
        self.assertIn("No", textos)


class PresentacionGraficasFletTests(unittest.TestCase):
    def test_convierte_cada_grafica_a_imagen_png_incrustada(self):
        datos = {
            "fecha": (["2024-05-20"], [2], []),
            "distancia_tamano": ([], [], []),
            "peligrosidad": ([], [], []),
        }

        for tipo, (fechas, conteos, resultados) in datos.items():
            with self.subTest(tipo=tipo):
                uri = crear_grafica_data_uri(
                    tipo,
                    fechas,
                    conteos,
                    resultados,
                )
                self.assertTrue(uri.startswith("data:image/png;base64,"))
                self.assertGreater(len(uri), 100)

    def test_tipo_de_grafica_desconocido_lanza_error_claro(self):
        with self.assertRaisesRegex(ValueError, "tipo de gráfica"):
            crear_grafica_data_uri("desconocida", [], [], [])


if __name__ == "__main__":
    unittest.main()
