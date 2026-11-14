"""Tests del Módulo B: Evaluación Térmica y Alerta Crítica."""

import unittest
from datetime import datetime, timedelta

from src.modulo_b_termico import EvaluadorTermico


class NotificadorEspia:
    def __init__(self):
        self.correos = []
        self.alertas_visuales = []

    def alerta_visual(self, mensaje):
        self.alertas_visuales.append(mensaje)
        return mensaje

    def alerta_sonora(self):
        return "\a"

    def enviar_correo_emergencia(self, *, asunto, cuerpo):
        self.correos.append((asunto, cuerpo))
        return {"modo": "dry-run", "asunto": asunto, "cuerpo": cuerpo}


class TestEvaluadorTermico(unittest.TestCase):
    def test_alerta_tras_15_minutos(self):
        espia = NotificadorEspia()
        evaluador = EvaluadorTermico(notificador=espia)
        t0 = datetime(2026, 11, 14, 10, 0, 0)

        self.assertEqual(evaluador.evaluar(-14.0, t0), "ANOMALIA")
        self.assertEqual(
            evaluador.evaluar(-14.0, t0 + timedelta(minutes=14, seconds=59)),
            "ANOMALIA",
        )
        self.assertEqual(
            evaluador.evaluar(-14.0, t0 + timedelta(minutes=15, seconds=1)),
            "ALERTA",
        )
        self.assertEqual(len(espia.correos), 1)

    def test_lectura_aislada_no_alerta(self):
        espia = NotificadorEspia()
        evaluador = EvaluadorTermico(notificador=espia)
        t0 = datetime(2026, 11, 14, 10, 0, 0)

        self.assertEqual(evaluador.evaluar(-14.0, t0), "ANOMALIA")
        self.assertEqual(evaluador.evaluar(-18.0, t0 + timedelta(minutes=5)), "OK")
        self.assertEqual(evaluador.evaluar(-18.0, t0 + timedelta(minutes=20)), "OK")
        self.assertEqual(len(espia.correos), 0)

    def test_anomalia_se_resetea_al_normalizar(self):
        espia = NotificadorEspia()
        evaluador = EvaluadorTermico(notificador=espia)
        t0 = datetime(2026, 11, 14, 10, 0, 0)

        evaluador.evaluar(-14.0, t0)                            # inicia anomalía
        evaluador.evaluar(-18.0, t0 + timedelta(minutes=10))    # normaliza -> reset
        evaluador.evaluar(-14.0, t0 + timedelta(minutes=15))    # nueva anomalía
        self.assertEqual(
            evaluador.evaluar(-14.0, t0 + timedelta(minutes=20)), "ANOMALIA"
        )
        self.assertEqual(len(espia.correos), 0)

    def test_no_redispara_mientras_continua(self):
        espia = NotificadorEspia()
        evaluador = EvaluadorTermico(notificador=espia)
        t0 = datetime(2026, 11, 14, 10, 0, 0)

        evaluador.evaluar(-14.0, t0)
        evaluador.evaluar(-14.0, t0 + timedelta(minutes=16))    # ALERTA
        self.assertEqual(
            evaluador.evaluar(-14.0, t0 + timedelta(minutes=21)), "ANOMALIA"
        )
        self.assertEqual(len(espia.correos), 1)


if __name__ == "__main__":
    unittest.main()
