"""Tests del cifrado en reposo (A02:2021 — Cryptographic Failures)."""

import unittest

from cryptography.exceptions import InvalidTag

from src.crypto import Cifrador


class TestCifrador(unittest.TestCase):
    def test_roundtrip(self):
        cifrador = Cifrador(Cifrador.generar_clave())
        token = cifrador.cifrar("-41.4700")
        self.assertEqual(cifrador.descifrar(token), "-41.4700")

    def test_tokens_distintos_para_mismo_plano(self):
        cifrador = Cifrador(Cifrador.generar_clave())
        self.assertNotEqual(cifrador.cifrar("x"), cifrador.cifrar("x"))

    def test_clave_invalida(self):
        with self.assertRaises(ValueError):
            Cifrador(b"corta")

    def test_clave_distinta_rechaza(self):
        cifrador_a = Cifrador(Cifrador.generar_clave())
        cifrador_b = Cifrador(Cifrador.generar_clave())
        token = cifrador_a.cifrar("secreto")
        with self.assertRaises(InvalidTag):
            cifrador_b.descifrar(token)


if __name__ == "__main__":
    unittest.main()
