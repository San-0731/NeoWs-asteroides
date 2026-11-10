import csv
import io
import unittest

from neo_app.exportacion import crear_csv_bytes


class ExportacionFletTests(unittest.TestCase):
    def test_crea_csv_descargable_con_los_resultados_de_la_consulta(self):
        resultados = [
            {
                "Fecha": "2024-05-20",
                "Name": "Asteroide de prueba",
                "Estimated_Diameter_(Km)": 0.42,
                "Threat_Level": True,
                "Close_Approach_Distance_(km)": 1234.5,
                "Close_Approach_Velocity_(km/h)": 9000,
            }
        ]

        contenido = crear_csv_bytes(resultados)
        filas = list(
            csv.DictReader(
                io.StringIO(contenido.decode("utf-8"), newline="")
            )
        )

        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["Fecha Asteroide"], "2024-05-20")
        self.assertEqual(filas[0]["Name"], "Asteroide de prueba")
        self.assertEqual(filas[0]["Estimated_Diameter_(Km)"], "0.42")
        self.assertEqual(filas[0]["Threat_Level"], "True")
        self.assertTrue(filas[0]["Fecha Importación"])

    def test_no_crea_csv_si_no_hay_resultados(self):
        self.assertIsNone(crear_csv_bytes([]))


if __name__ == "__main__":
    unittest.main()
