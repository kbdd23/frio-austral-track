"""Test del flujo end-to-end que antes vivía en demo.py.

Verifica las métricas de cada escenario definido en src/escenarios.py.
"""

import unittest

from helpers import ITERACIONES_PRUEBA
from src import escenarios
from src.crypto import Cifrador


class TestFlujoCompleto(unittest.TestCase):
    def test_flujo_completo_produce_metricas_esperadas(self):
        base_local, base_cloud = escenarios.crear_bases(
            Cifrador(Cifrador.generar_clave())
        )
        datos = escenarios.sembrar_operacion(
            base_local, iteraciones=ITERACIONES_PRUEBA
        )
        escenarios.sembrar_operacion(base_cloud, iteraciones=ITERACIONES_PRUEBA)

        resultado = escenarios.ejecutar_flujo_completo(base_local, base_cloud, datos)

        self.assertEqual(resultado["lecturas_cloud"], 10)
        self.assertEqual(resultado["pendientes"], 0)
        self.assertEqual(resultado["alertas"], 1)
        self.assertTrue(any("ALERTA" in linea for linea in resultado["log"]))

    def test_modulo_a_sincroniza_pendientes(self):
        base_local, base_cloud = escenarios.crear_bases()
        datos = escenarios.sembrar_operacion(
            base_local, iteraciones=ITERACIONES_PRUEBA
        )
        escenarios.sembrar_operacion(base_cloud, iteraciones=ITERACIONES_PRUEBA)

        resultado = escenarios.ejecutar_modulo_a(base_local, base_cloud, datos)

        self.assertEqual(resultado["pendientes"], 0)
        self.assertEqual(resultado["lecturas_cloud"], 6)

    def test_modulo_b_dispara_alerta(self):
        base_local, _base_cloud = escenarios.crear_bases()
        datos = escenarios.sembrar_operacion(
            base_local, iteraciones=ITERACIONES_PRUEBA
        )

        resultado = escenarios.ejecutar_modulo_b(base_local, datos)

        self.assertEqual(resultado["alertas"], 1)
        self.assertTrue(any("ALERTA" in linea for linea in resultado["log"]))

    def test_persistencia_recupera_tras_reinicio(self):
        base_local, _base_cloud = escenarios.crear_bases()
        datos = escenarios.sembrar_operacion(
            base_local, iteraciones=ITERACIONES_PRUEBA
        )

        resultado = escenarios.ejecutar_persistencia(base_local, datos)

        self.assertEqual(resultado["veredicto"], "ALERTA")

    def test_rbac_bloquea_conductor(self):
        base_local, _base_cloud = escenarios.crear_bases()
        datos = escenarios.sembrar_operacion(
            base_local, iteraciones=ITERACIONES_PRUEBA
        )

        resultado = escenarios.ejecutar_rbac(base_local, datos)

        self.assertTrue(any("BLOQUEADO" in linea for linea in resultado["log"]))

    def test_ver_flota_retorna_35_camiones(self):
        base_local, _base_cloud = escenarios.crear_bases()
        escenarios.sembrar_operacion(base_local, iteraciones=ITERACIONES_PRUEBA)
        escenarios.sembrar_flota(base_local, total=35)

        filas = escenarios.ver_flota(base_local)

        self.assertEqual(len(filas), 35)

    def test_a02_cifra_geolocalizacion(self):
        base_local, _base_cloud = escenarios.crear_bases()
        datos = escenarios.sembrar_operacion(
            base_local, iteraciones=ITERACIONES_PRUEBA
        )

        resultado = escenarios.ejecutar_a02_cifrado(base_local, datos)

        self.assertTrue(resultado["cifrado_ok"])

    def test_a03_injection_se_trata_como_dato(self):
        base_local, _base_cloud = escenarios.crear_bases()
        datos = escenarios.sembrar_operacion(
            base_local, iteraciones=ITERACIONES_PRUEBA
        )

        resultado = escenarios.ejecutar_a03_injection(base_local, datos)

        self.assertTrue(resultado["payload_literal"])
        self.assertTrue(resultado["tabla_intacta"])


if __name__ == "__main__":
    unittest.main()
