import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from neo_app.api import LimiteApiError, obtener_api_key, peticion


class ObtenerApiKeyTests(unittest.TestCase):
    def test_prefiere_clave_del_archivo_de_ajustes(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo = Path(directorio) / "settings.json"
            archivo.write_text(
                json.dumps({"NASA_API_KEY": "clave_de_ajustes"}),
                encoding="utf-8",
            )

            with (
                patch("neo_app.api.ARCHIVO_AJUSTES", archivo),
                patch.dict(os.environ, {"NASA_API_KEY": "clave_del_entorno"}, clear=True),
            ):
                resultado = obtener_api_key()

        self.assertEqual(resultado, ("clave_de_ajustes", False))

    def test_usa_variable_de_entorno_si_no_hay_archivo(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo_ausente = Path(directorio) / "no_existe.json"

            with (
                patch("neo_app.api.ARCHIVO_AJUSTES", archivo_ausente),
                patch.dict(os.environ, {"NASA_API_KEY": "clave_del_entorno"}, clear=True),
            ):
                resultado = obtener_api_key()

        self.assertEqual(resultado, ("clave_del_entorno", False))

    def test_usa_demo_key_si_no_hay_clave(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo_ausente = Path(directorio) / "no_existe.json"

            with (
                patch("neo_app.api.ARCHIVO_AJUSTES", archivo_ausente),
                patch.dict(os.environ, {}, clear=True),
            ):
                resultado = obtener_api_key()

        self.assertEqual(resultado, ("DEMO_KEY", True))


class PeticionTests(unittest.TestCase):
    def test_envia_clave_y_devuelve_si_es_demo(self):
        respuesta = Mock()
        respuesta.json.return_value = {"dato": "respuesta"}

        with (
            patch(
                "neo_app.api.obtener_api_key",
                return_value=("DEMO_KEY", True),
            ),
            patch("neo_app.api.requests.get", return_value=respuesta) as get,
        ):
            resultado = peticion("2024-05-20", "2024-05-20")

        self.assertEqual(resultado, ({"dato": "respuesta"}, True))
        self.assertEqual(
            get.call_args.kwargs["params"]["api_key"],
            "DEMO_KEY",
        )
        respuesta.raise_for_status.assert_called_once_with()

    def test_429_lanza_error_de_limite_en_espanol(self):
        respuesta = Mock()
        respuesta.status_code = 429

        with (
            patch(
                "neo_app.api.obtener_api_key",
                return_value=("DEMO_KEY", True),
            ),
            patch("neo_app.api.requests.get", return_value=respuesta),
        ):
            with self.assertRaisesRegex(
                LimiteApiError,
                "límite de solicitudes",
            ):
                peticion("2024-05-20", "2024-05-20")

        respuesta.raise_for_status.assert_not_called()

    def test_otro_error_http_se_propaga_sin_convertirse_en_error_de_limite(self):
        respuesta = Mock()
        respuesta.status_code = 500
        error_http = requests.exceptions.HTTPError("error del servidor")
        respuesta.raise_for_status.side_effect = error_http

        with (
            patch(
                "neo_app.api.obtener_api_key",
                return_value=("clave_de_prueba", False),
            ),
            patch("neo_app.api.requests.get", return_value=respuesta),
        ):
            with self.assertRaises(requests.exceptions.HTTPError) as contexto:
                peticion("2024-05-20", "2024-05-20")

        self.assertIs(contexto.exception, error_http)
        respuesta.raise_for_status.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()