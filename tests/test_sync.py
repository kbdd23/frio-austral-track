"""Tests del Módulo A: Sincronización Offline-Online (idempotente)."""

import unittest

from helpers import RUTA_SCHEMA_LOCAL, crear_base_local, sembrar_operacion
from src.db_cloud import BaseDatosCloud
from src.modulo_a_sync import CloudGateway, Red, Sincronizador


def _armar_sincronizador():
    base_local = crear_base_local()
    id_despacho = sembrar_operacion(base_local)["id_despacho"]

    base_cloud = BaseDatosCloud(":memory:")
    base_cloud.crear_esquema(RUTA_SCHEMA_LOCAL)
    sembrar_operacion(base_cloud)

    red = Red(conectado=True)
    gateway = CloudGateway(base_cloud)
    sincronizador = Sincronizador(base_local, red, gateway)
    return base_local, base_cloud, red, sincronizador, id_despacho


class TestSincronizador(unittest.TestCase):
    def test_offline_almacena_pendiente(self):
        base_local, base_cloud, red, sincronizador, id_despacho = _armar_sincronizador()
        red.conectado = False

        estado, _, _ = sincronizador.registrar_lectura(
            id_despacho=id_despacho, temperatura=-19.0, latitud=-41.0, longitud=-72.0
        )
        self.assertEqual(estado, "Pendiente de sincronizar")
        self.assertEqual(base_cloud.total_lecturas(), 0)
        self.assertEqual(len(base_local.lecturas_pendientes()), 1)

    def test_online_publica_directo(self):
        base_local, base_cloud, red, sincronizador, id_despacho = _armar_sincronizador()
        red.conectado = True

        estado, _, _ = sincronizador.registrar_lectura(
            id_despacho=id_despacho, temperatura=-19.0, latitud=-41.0, longitud=-72.0
        )
        self.assertEqual(estado, "Sincronizado")
        self.assertEqual(base_cloud.total_lecturas(), 1)
        self.assertEqual(len(base_local.lecturas_pendientes()), 0)

    def test_sincronizacion_marca_sincronizado(self):
        base_local, base_cloud, red, sincronizador, id_despacho = _armar_sincronizador()
        red.conectado = False
        sincronizador.registrar_lectura(
            id_despacho=id_despacho, temperatura=-19.0, latitud=-41.0, longitud=-72.0
        )
        sincronizador.registrar_lectura(
            id_despacho=id_despacho, temperatura=-19.5, latitud=-41.0, longitud=-72.0
        )

        red.conectado = True
        subidos = sincronizador.sincronizar_pendientes()

        self.assertEqual(subidos, 2)
        self.assertEqual(base_cloud.total_lecturas(), 2)
        self.assertEqual(len(base_local.lecturas_pendientes()), 0)

    def test_reesincronizacion_no_duplica(self):
        base_local, base_cloud, red, sincronizador, id_despacho = _armar_sincronizador()
        red.conectado = False
        sincronizador.registrar_lectura(
            id_despacho=id_despacho, temperatura=-19.0, latitud=-41.0, longitud=-72.0
        )
        red.conectado = True
        sincronizador.sincronizar_pendientes()
        self.assertEqual(base_cloud.total_lecturas(), 1)

        # Re-publicar manualmente la misma lectura no debe duplicarla.
        fila = base_local.conexion.execute(
            "SELECT * FROM RegistroTemperatura"
        ).fetchone()
        base_cloud.insertar_lectura(
            {
                "id_despacho": fila["id_despacho"],
                "fecha_hora": fila["fecha_hora"],
                "temperatura": fila["temperatura"],
                "id_evento_local": fila["id_evento_local"],
                "latitud": fila["latitud"],
                "longitud": fila["longitud"],
            }
        )
        self.assertEqual(base_cloud.total_lecturas(), 1)


if __name__ == "__main__":
    unittest.main()
