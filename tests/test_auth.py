"""Tests del hash de credenciales (A02:2021 — Cryptographic Failures)."""

import unittest

from src.auth import crear_hash_contrasena, verificar_contrasena

ITERACIONES_PRUEBA = 1000


def _hash(contrasena: str) -> str:
    return crear_hash_contrasena(contrasena, iteraciones=ITERACIONES_PRUEBA)


class TestAuth(unittest.TestCase):
    def test_hash_y_verificar_ok(self):
        hash_almacenado = _hash("s3creta")
        self.assertTrue(verificar_contrasena("s3creta", hash_almacenado))

    def test_contrasena_incorrecta_rechazada(self):
        hash_almacenado = _hash("s3creta")
        self.assertFalse(verificar_contrasena("incorrecta", hash_almacenado))

    def test_hashes_distintos_para_misma_contrasena(self):
        self.assertNotEqual(_hash("x"), _hash("x"))

    def test_formato_invalido_rechazado(self):
        self.assertFalse(verificar_contrasena("x", "malformado"))

    def test_hash_no_contiene_texto_plano(self):
        hash_almacenado = _hash("s3creta")
        self.assertNotIn("s3creta", hash_almacenado)


if __name__ == "__main__":
    unittest.main()
