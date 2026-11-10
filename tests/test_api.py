import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote
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
                patch("neo_app.config.ARCHIVO_AJUSTES", archivo),
                patch.dict(os.environ, {"NASA_API_KEY": "clave_del_entorno"}, clear=True),
            ):
                resultado = obtener_api_key()

        self.assertEqual(resultado, ("clave_de_ajustes", False))

    def test_usa_demo_key_si_no_hay_ajustes_aunque_exista_variable_entorno(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo_ausente = Path(directorio) / "no_existe.json"

            with (
                patch("neo_app.config.ARCHIVO_AJUSTES", archivo_ausente),
                patch.dict(os.environ, {"NASA_API_KEY": "clave_del_entorno"}, clear=True),
            ):
                resultado = obtener_api_key()

        self.assertEqual(resultado, ("DEMO_KEY", True))

    def test_usa_demo_key_si_ajustes_no_tienen_clave_aunque_exista_variable_entorno(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo = Path(directorio) / "settings.json"
            archivo.write_text(json.dumps({"NASA_API_KEY": ""}), encoding="utf-8")

            with (
                patch("neo_app.config.ARCHIVO_AJUSTES", archivo),
                patch.dict(os.environ, {"NASA_API_KEY": "clave_del_entorno"}, clear=True),
            ):
                resultado = obtener_api_key()

        self.assertEqual(resultado, ("DEMO_KEY", True))

    def test_usa_demo_key_si_no_hay_clave(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo_ausente = Path(directorio) / "no_existe.json"

            with (
                patch("neo_app.config.ARCHIVO_AJUSTES", archivo_ausente),
                patch.dict(os.environ, {}, clear=True),
            ):
                resultado = obtener_api_key()

        self.assertEqual(resultado, ("DEMO_KEY", True))


class PeticionTests(unittest.TestCase):
    def test_usa_clave_recibida_sin_leer_ajustes_globales(self):
        api_key = "clave_de_sesion_web"
        respuesta = Mock()
        respuesta.json.return_value = {"dato": "respuesta"}

        with (
            patch("neo_app.api.obtener_api_key") as obtener,
            patch("neo_app.api.requests.get", return_value=respuesta) as get,
        ):
            resultado = peticion(
                "2024-05-20",
                "2024-05-20",
                api_key=api_key,
            )

        self.assertEqual(resultado, ({"dato": "respuesta"}, False))
        self.assertEqual(
            get.call_args.kwargs["params"]["api_key"],
            api_key,
        )
        obtener.assert_not_called()
        respuesta.raise_for_status.assert_called_once_with()

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

    def test_error_http_no_expone_la_api_key_en_la_url(self):
        api_key = "clave/secreta+prueba"
        respuesta = Mock()
        respuesta.status_code = 500
        error_http = requests.exceptions.HTTPError(
            "500 Server Error for url: "
            f"https://api.nasa.gov/neo/rest/v1/feed?api_key={quote(api_key, safe='')}"
        )
        respuesta.raise_for_status.side_effect = error_http

        with (
            patch(
                "neo_app.api.obtener_api_key",
                return_value=(api_key, False),
            ),
            patch("neo_app.api.requests.get", return_value=respuesta),
        ):
            with self.assertRaises(requests.exceptions.RequestException) as contexto:
                peticion("2024-05-20", "2024-05-20")

        self.assertNotIn(api_key, str(contexto.exception))
        self.assertNotIn(quote(api_key, safe=""), str(contexto.exception))
        self.assertIn("api_key=[REDACTED]", str(contexto.exception))
        self.assertIn("500 Server Error", str(contexto.exception))
        respuesta.raise_for_status.assert_called_once_with()

    def test_error_de_conexion_no_expone_api_key_ni_en_formato_codificado(self):
        api_key = "clave/secreta+prueba"
        error_red = requests.exceptions.ConnectionError(
            "Connection failed for "
            f"https://api.nasa.gov/feed?api_key={quote(api_key, safe='')}"
        )

        with (
            patch(
                "neo_app.api.obtener_api_key",
                return_value=(api_key, False),
            ),
            patch("neo_app.api.requests.get", side_effect=error_red),
        ):
            with self.assertRaises(requests.exceptions.RequestException) as contexto:
                peticion("2024-05-20", "2024-05-20")

        self.assertNotIn(api_key, str(contexto.exception))
        self.assertNotIn(quote(api_key, safe=""), str(contexto.exception))
        self.assertIn("api_key=[REDACTED]", str(contexto.exception))


if __name__ == "__main__":
    unittest.main()