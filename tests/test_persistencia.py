"""Tests de persistencia del Módulo B (temporizador y alerta)."""

import unittest
from datetime import datetime, timedelta

from helpers import crear_base_local, sembrar_operacion
from src.modulo_b_termico import EvaluadorTermico


class NotificadorEspia:
    def __init__(self):
        self.correos = []

    def alerta_visual(self, mensaje):
        return mensaje

    def alerta_sonora(self):
        return "\a"

    def enviar_correo_emergencia(self, *, asunto, cuerpo):
        self.correos.append((asunto, cuerpo))
        return {"modo": "dry-run"}


class TestPersistenciaTermico(unittest.TestCase):
    def test_inicio_anomalia_sobrevive_reinicio(self):
        base = crear_base_local()
        id_despacho = sembrar_operacion(base)["id_despacho"]
        espia = NotificadorEspia()
        t0 = datetime(2026, 11, 14, 10, 0, 0)

        evaluador = EvaluadorTermico(
            notificador=espia, repositorio=base, id_despacho=id_despacho
        )
        self.assertEqual(evaluador.evaluar(-14.0, t0), "ANOMALIA")

        # Reinicio simulado: nuevo evaluador sobre el mismo repositorio.
        evaluador2 = EvaluadorTermico(
            notificador=espia, repositorio=base, id_despacho=id_despacho
        )
        self.assertEqual(
            evaluador2.evaluar(-14.0, t0 + timedelta(minutes=16)), "ALERTA"
        )
        self.assertEqual(len(espia.correos), 1)

    def test_notificacion_persistida_al_disparar(self):
        base = crear_base_local()
        id_despacho = sembrar_operacion(base)["id_despacho"]
        espia = NotificadorEspia()
        t0 = datetime(2026, 11, 14, 10, 0, 0)

        id_registro = base.insertar_lectura(
            id_despacho=id_despacho,
            temperatura=-14.0,
            latitud=-41.0,
            longitud=-72.0,
            estado="Pendiente de sincronizar",
        )

        evaluador = EvaluadorTermico(
            notificador=espia, repositorio=base, id_despacho=id_despacho
        )
        evaluador.evaluar(-14.0, t0, id_registro=id_registro)
        evaluador.evaluar(-14.0, t0 + timedelta(minutes=16), id_registro=id_registro)

        fila = base.conexion.execute(
            "SELECT * FROM NotificacionAlerta WHERE id_registro = ?", (id_registro,)
        ).fetchone()
        self.assertIsNotNone(fila)
        self.assertEqual(fila["tipo"], "Umbral de -15C persistente")

    def test_estado_anomalia_se_limpia_al_normalizar(self):
        base = crear_base_local()
        id_despacho = sembrar_operacion(base)["id_despacho"]
        espia = NotificadorEspia()
        t0 = datetime(2026, 11, 14, 10, 0, 0)

        evaluador = EvaluadorTermico(
            notificador=espia, repositorio=base, id_despacho=id_despacho
        )
        evaluador.evaluar(-14.0, t0)
        self.assertIsNotNone(base.obtener_inicio_anomalia(id_despacho))

        evaluador.evaluar(-18.0, t0 + timedelta(minutes=5))
        self.assertIsNone(base.obtener_inicio_anomalia(id_despacho))


if __name__ == "__main__":
    unittest.main()
