import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from neo_app.config import (
    AjustesInvalidosError,
    guardar_ajustes,
    leer_ajustes,
    prepara_directorios_datos,
)


class ConfiguracionTests(unittest.TestCase):
    def test_prepara_settings_vacio_cuando_no_existe(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta_datos = Path(directorio) / "datos"
            archivo_ajustes = ruta_datos / "settings.json"

            with (
                patch("neo_app.config.DIRECTORIO_DATOS", ruta_datos),
                patch("neo_app.config.ARCHIVO_AJUSTES", archivo_ajustes),
            ):
                prepara_directorios_datos()

            self.assertTrue(archivo_ajustes.exists())
            self.assertEqual(
                json.loads(archivo_ajustes.read_text(encoding="utf-8")),
                {"NASA_API_KEY": ""},
            )

    def test_leer_ajustes_ausentes_devuelve_valores_por_defecto(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo_ajustes = Path(directorio) / "no_existe.json"

            with patch("neo_app.config.ARCHIVO_AJUSTES", archivo_ajustes):
                ajustes = leer_ajustes()

        self.assertEqual(ajustes, {"NASA_API_KEY": ""})

    def test_archivo_danado_lanza_error_claro_y_se_conserva(self):
        contenido_danado = '{"NASA_API_KEY": '
        with tempfile.TemporaryDirectory() as directorio:
            archivo_ajustes = Path(directorio) / "settings.json"
            archivo_ajustes.write_text(contenido_danado, encoding="utf-8")

            with patch("neo_app.config.ARCHIVO_AJUSTES", archivo_ajustes):
                with self.assertRaisesRegex(ValueError, "JSON inválido"):
                    leer_ajustes()

            self.assertEqual(
                archivo_ajustes.read_text(encoding="utf-8"),
                contenido_danado,
            )

    def test_errores_de_contenido_de_ajustes_tienen_tipo_especifico(self):
        contenidos_invalidos = [
            '{"NASA_API_KEY": ',
            '[]',
            '{"NASA_API_KEY": 42}',
        ]

        with tempfile.TemporaryDirectory() as directorio:
            for indice, contenido in enumerate(contenidos_invalidos):
                with self.subTest(contenido=contenido):
                    archivo_ajustes = Path(directorio) / f"settings-{indice}.json"
                    archivo_ajustes.write_text(contenido, encoding="utf-8")

                    with patch("neo_app.config.ARCHIVO_AJUSTES", archivo_ajustes):
                        with self.assertRaises(AjustesInvalidosError):
                            leer_ajustes()

    def test_guardado_interrumpido_conserva_archivo_y_limpia_temporal(self):
        contenido_original = '{"NASA_API_KEY": "clave-anterior"}'

        def interrumpir_guardado(ajustes, archivo, **opciones):
            self.assertEqual(ajustes, {"NASA_API_KEY": "clave-nueva"})
            self.assertEqual(opciones["indent"], 2)
            archivo.write('{"NASA_API_KEY": "incompleta"')
            raise OSError("guardado interrumpido")

        with tempfile.TemporaryDirectory() as directorio:
            ruta_datos = Path(directorio)
            archivo_ajustes = ruta_datos / "settings.json"
            archivo_ajustes.write_text(contenido_original, encoding="utf-8")

            with (
                patch("neo_app.config.DIRECTORIO_DATOS", ruta_datos),
                patch("neo_app.config.ARCHIVO_AJUSTES", archivo_ajustes),
                patch("neo_app.config.json.dump", side_effect=interrumpir_guardado),
            ):
                with self.assertRaisesRegex(OSError, "guardado interrumpido"):
                    guardar_ajustes({"NASA_API_KEY": "clave-nueva"})

            self.assertEqual(
                archivo_ajustes.read_text(encoding="utf-8"),
                contenido_original,
            )
            self.assertEqual(
                list(ruta_datos.glob(".settings.json.*.tmp")),
                [],
            )

    def test_guardar_ajustes_reemplaza_archivo_con_json_valido(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta_datos = Path(directorio)
            archivo_ajustes = ruta_datos / "settings.json"
            archivo_ajustes.write_text(
                '{"NASA_API_KEY": "anterior"}',
                encoding="utf-8",
            )

            with (
                patch("neo_app.config.DIRECTORIO_DATOS", ruta_datos),
                patch("neo_app.config.ARCHIVO_AJUSTES", archivo_ajustes),
            ):
                guardar_ajustes({"NASA_API_KEY": "nueva"})
                ajustes = leer_ajustes()

            self.assertEqual(ajustes, {"NASA_API_KEY": "nueva"})
            self.assertEqual(
                [ruta.name for ruta in ruta_datos.iterdir()],
                ["settings.json"],
            )


if __name__ == "__main__":
    unittest.main()
