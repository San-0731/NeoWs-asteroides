import asyncio
from threading import Event
import unittest
from pathlib import Path
from unittest.mock import patch

from neo_app.consulta_flet import (
    consultar_en_segundo_plano,
    consultar_y_procesar,
)


class ConsultaFletTests(unittest.TestCase):
    def test_consulta_y_procesa_datos_sin_interactuar_con_la_interfaz(self):
        fecha = "2024-05-20"
        fecha_final = "2024-05-21"
        cache = {}
        archivo_cache = Path("cache_neows.json")
        respuesta = {"near_earth_objects": {}}
        filas = [{"Fecha": fecha, "Name": "Asteroide de prueba"}]
        fechas = [fecha]
        conteos = [1]

        with (
            patch(
                "neo_app.consulta_flet.obtener_datos",
                return_value=(respuesta, True, False),
            ) as obtener,
            patch(
                "neo_app.consulta_flet.construir_datos",
                return_value=(filas, fechas, conteos),
            ) as construir,
        ):
            resultado = consultar_y_procesar(
                fecha,
                fecha_final,
                cache,
                archivo_cache,
            )

        obtener.assert_called_once_with(
            fecha,
            fecha_final,
            cache,
            archivo_cache,
        )
        construir.assert_called_once_with(respuesta)
        self.assertEqual(
            resultado,
            (filas, fechas, conteos, True, False),
        )


class ConsultaEnSegundoPlanoTests(unittest.IsolatedAsyncioTestCase):
    async def test_consulta_no_bloquea_el_ciclo_de_eventos(self):
        trabajo_iniciado = Event()
        liberar_trabajo = Event()

        def trabajo_lento(*_):
            trabajo_iniciado.set()
            liberar_trabajo.wait(timeout=2)
            return "resultado"

        try:
            with patch(
                "neo_app.consulta_flet.consultar_y_procesar",
                side_effect=trabajo_lento,
            ):
                tarea = asyncio.create_task(
                    consultar_en_segundo_plano(
                        "2024-05-20",
                        "2024-05-21",
                        {},
                        Path("cache_neows.json"),
                    )
                )
                inicio_confirmado = await asyncio.wait_for(
                    asyncio.to_thread(trabajo_iniciado.wait),
                    timeout=1,
                )
                self.assertTrue(inicio_confirmado)
                self.assertFalse(tarea.done())
                liberar_trabajo.set()
                resultado = await tarea

            self.assertEqual(resultado, "resultado")
        finally:
            liberar_trabajo.set()


if __name__ == "__main__":
    unittest.main()
