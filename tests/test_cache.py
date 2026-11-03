import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from neo_app.cache import (
    CacheFormatError,
    esta_vencida,
    cargar_cache,
    guardar_cache,
    respaldar_cache_invalido,
)


class EstaVencidaTests(unittest.TestCase):
    def test_entrada_de_menos_de_doce_horas_no_esta_vencida(self):
        guardado_en = datetime.now().astimezone() - timedelta(hours=2)
        entrada = {"guardado_en": guardado_en.isoformat()}

        self.assertFalse(esta_vencida(entrada, guardado_en.date().isoformat()))

    def test_entrada_vieja_guardada_en_la_fecha_final_esta_vencida(self):
        guardado_en = datetime.now().astimezone() - timedelta(hours=13)
        entrada = {"guardado_en": guardado_en.isoformat()}

        fecha_final_utc = guardado_en.astimezone(timezone.utc).date().isoformat()

        self.assertTrue(esta_vencida(entrada, fecha_final_utc))

    def test_entrada_guardada_despues_de_la_fecha_final_es_permanente(self):
        guardado_en = datetime.now().astimezone() - timedelta(days=2)
        fecha_final = (guardado_en.date() - timedelta(days=1)).isoformat()
        entrada = {"guardado_en": guardado_en.isoformat()}

        self.assertFalse(esta_vencida(entrada, fecha_final))

    def test_compara_fecha_de_guardado_convertida_a_utc(self):
        ahora_utc = datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc)
        guardado_en = (
            ahora_utc - timedelta(hours=13)
        ).astimezone(timezone(timedelta(hours=14)))
        entrada = {"guardado_en": guardado_en.isoformat()}

        class RelojCongelado(datetime):
            @classmethod
            def now(cls, tz=None):
                return ahora_utc

        with patch("neo_app.cache.datetime", RelojCongelado):
            vencida = esta_vencida(entrada, "2024-01-01")

        self.assertTrue(vencida)


class CargarCacheTests(unittest.TestCase):
    def test_respaldo_de_cache_invalido_usa_nombre_unico(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo_cache = Path(directorio) / "cache_neows.json"
            respaldo_existente = Path(f"{archivo_cache}.bak")
            contenido_danado = '{"incompleto": '
            archivo_cache.write_text(contenido_danado, encoding="utf-8")
            respaldo_existente.write_text("respaldo anterior", encoding="utf-8")

            ruta_respaldo = respaldar_cache_invalido(archivo_cache)

            self.assertEqual(ruta_respaldo.name, "cache_neows.json.bak.1")
            self.assertFalse(archivo_cache.exists())
            self.assertEqual(
                ruta_respaldo.read_text(encoding="utf-8"),
                contenido_danado,
            )
            self.assertEqual(
                respaldo_existente.read_text(encoding="utf-8"),
                "respaldo anterior",
            )

    def test_rechaza_json_valido_con_estructura_incorrecta(self):
        contenidos_invalidos = [
            {"fecha": "2026-01-01"},
            [{"fecha": "2026-01-01"}],
            [
                {
                    "fecha": "fecha-invalida",
                    "fecha_final": "2026-01-01",
                    "respuesta": {},
                    "guardado_en": datetime.now().astimezone().isoformat(),
                }
            ],
        ]

        with tempfile.TemporaryDirectory() as directorio:
            for indice, contenido in enumerate(contenidos_invalidos):
                with self.subTest(contenido=contenido):
                    archivo_cache = Path(directorio) / f"cache-{indice}.json"
                    texto_original = json.dumps(contenido)
                    archivo_cache.write_text(texto_original, encoding="utf-8")

                    with self.assertRaises(CacheFormatError):
                        cargar_cache(archivo_cache)

                    self.assertEqual(
                        archivo_cache.read_text(encoding="utf-8"),
                        texto_original,
                    )

    def test_elimina_api_key_de_enlaces_en_cache_existente(self):
        fecha = datetime.now().date().isoformat()
        api_key = "clave-secreta-antigua"
        registros = [
            {
                "fecha": fecha,
                "fecha_final": fecha,
                "respuesta": {
                    "links": {
                        "self": (
                            "https://api.nasa.gov/neo/rest/v1/feed"
                            f"?start_date={fecha}&api_key={api_key}"
                        )
                    }
                },
                "guardado_en": datetime.now().astimezone().isoformat(),
            }
        ]

        with tempfile.TemporaryDirectory() as directorio:
            archivo_cache = Path(directorio) / "cache.json"
            archivo_cache.write_text(json.dumps(registros), encoding="utf-8")

            cache = cargar_cache(archivo_cache)

            contenido_guardado = archivo_cache.read_text(encoding="utf-8")

        self.assertNotIn(api_key, contenido_guardado)
        self.assertIn("api_key=REDACTED", contenido_guardado)
        self.assertIn(
            "api_key=REDACTED",
            cache[(fecha, fecha)]["respuesta"]["links"]["self"],
        )

    def test_elimina_entradas_temporales_vencidas_y_conserva_permanentes(self):
        guardado_vencido = datetime.now().astimezone() - timedelta(hours=13)
        guardado_permanente = datetime.now().astimezone() - timedelta(days=2)
        registros = [
            {
                "fecha": "2024-01-01",
                "fecha_final": (
                    guardado_vencido.astimezone(timezone.utc).date().isoformat()
                ),
                "respuesta": {"dato": "vencido"},
                "guardado_en": guardado_vencido.isoformat(),
            },
            {
                "fecha": "2024-01-02",
                "fecha_final": (
                    guardado_permanente.astimezone(timezone.utc).date()
                    - timedelta(days=1)
                ).isoformat(),
                "respuesta": {"dato": "permanente"},
                "guardado_en": guardado_permanente.isoformat(),
            },
        ]

        with tempfile.TemporaryDirectory() as directorio:
            archivo_cache = Path(directorio) / "cache.json"
            archivo_cache.write_text(
                json.dumps(registros),
                encoding="utf-8",
            )

            cache = cargar_cache(archivo_cache)

            self.assertEqual(len(cache), 1)
            self.assertIn(
                (registros[1]["fecha"], registros[1]["fecha_final"]),
                cache,
            )
            contenido_guardado = json.loads(
                archivo_cache.read_text(encoding="utf-8")
            )
            self.assertEqual(len(contenido_guardado), 1)
            self.assertEqual(contenido_guardado[0]["respuesta"]["dato"], "permanente")

    def test_guardar_cache_conserva_original_y_limpia_temporal_si_falla(self):
        contenido_original = '[{"respuesta": "cache anterior"}]'
        entrada_cache = {
            ("2024-01-01", "2024-01-01"): {
                "respuesta": {"dato": "nuevo"},
                "guardado_en": datetime.now().astimezone().isoformat(),
            }
        }

        with tempfile.TemporaryDirectory() as directorio:
            archivo_cache = Path(directorio) / "cache.json"
            archivo_temporal = archivo_cache.with_name("cache.json.tmp")
            archivo_cache.write_text(contenido_original, encoding="utf-8")

            with patch("neo_app.cache.json.dump", side_effect=OSError("fallo simulado")):
                with self.assertRaisesRegex(OSError, "fallo simulado"):
                    guardar_cache(entrada_cache, archivo_cache)

            self.assertEqual(
                archivo_cache.read_text(encoding="utf-8"),
                contenido_original,
            )
            self.assertFalse(archivo_temporal.exists())

if __name__ == "__main__":
    unittest.main()
