"""Tests del control de acceso por roles (A01:2021 — Broken Access Control)."""

import unittest

from helpers import crear_base_local, sembrar_operacion
from src.rbac import (
    AccesoDenegado,
    Sesion,
    obtener_dashboard,
    obtener_ruta_conductor,
)


class TestRbac(unittest.TestCase):
    def setUp(self):
        self.base = crear_base_local()
        self.datos = sembrar_operacion(self.base)

    def test_conductor_ve_su_ruta(self):
        sesion = Sesion(
            id_usuario=self.datos["id_usuario_conductor"],
            rol="Conductor",
            id_conductor=self.datos["id_conductor"],
        )
        fila = obtener_ruta_conductor(self.base.conexion, sesion)
        self.assertIsNotNone(fila)
        self.assertEqual(fila["estado"], "En Ruta")

    def test_gerente_ve_dashboard(self):
        sesion = Sesion(id_usuario=self.datos["id_usuario_gerente"], rol="Operaciones")
        fila = obtener_dashboard(self.base.conexion, sesion)
        self.assertEqual(fila["total_despachos"], 1)
        self.assertEqual(fila["en_ruta"], 1)

    def test_conductor_no_ve_dashboard(self):
        sesion = Sesion(
            id_usuario=self.datos["id_usuario_conductor"],
            rol="Conductor",
            id_conductor=self.datos["id_conductor"],
        )
        with self.assertRaises(AccesoDenegado):
            obtener_dashboard(self.base.conexion, sesion)

    def test_gerente_no_ve_ruta_de_conductor(self):
        sesion = Sesion(id_usuario=self.datos["id_usuario_gerente"], rol="Operaciones")
        with self.assertRaises(AccesoDenegado):
            obtener_ruta_conductor(self.base.conexion, sesion)

    def test_conductor_sin_id_conductor_denegado(self):
        sesion = Sesion(id_usuario=self.datos["id_usuario_conductor"], rol="Conductor")
        with self.assertRaises(AccesoDenegado):
            obtener_ruta_conductor(self.base.conexion, sesion)

    def test_rol_invalido_rechazado(self):
        with self.assertRaises(ValueError):
            Sesion(id_usuario=1, rol="Hacker")


if __name__ == "__main__":
    unittest.main()
