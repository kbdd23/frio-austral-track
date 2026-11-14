"""Validación estática del DDL de producción (schema_cloud.sql).

El esquema cloud es MySQL/PostgreSQL y no se ejecuta en el prototipo, que
simula el cloud con SQLite. Este test verifica que el DDL de producción
contiene las tablas y columnas críticas, para que no quede sin validar.
"""

import unittest
from pathlib import Path

RUTA_CLOUD = Path(__file__).resolve().parent.parent / "sql" / "schema_cloud.sql"

TABLAS_ESPERADAS = (
    "Usuario",
    "Conductor",
    "Camion",
    "Despacho",
    "RegistroTemperatura",
    "NotificacionAlerta",
    "EstadoTermico",
)


class TestSchemaCloud(unittest.TestCase):
    def setUp(self):
        self.ddl = RUTA_CLOUD.read_text(encoding="utf-8")

    def test_contiene_todas_las_tablas_esperadas(self):
        for tabla in TABLAS_ESPERADAS:
            self.assertIn(f"CREATE TABLE {tabla}", self.ddl)

    def test_id_evento_local_es_unico(self):
        self.assertIn("id_evento_local VARCHAR(80) UNIQUE NOT NULL", self.ddl)

    def test_registro_temperatura_tiene_estado_sincronizacion(self):
        self.assertIn("estado_sincronizacion", self.ddl)

    def test_estado_termico_tiene_inicio_anomalia(self):
        self.assertIn("inicio_anomalia", self.ddl)

    def test_no_hay_columnas_de_geolocalizacion_en_claro(self):
        # A02: latitud/longitud deben declararse cifradas (VARBINARY), no como
        # tipos numéricos en claro.
        self.assertIn("latitud VARBINARY(512)", self.ddl)
        self.assertIn("longitud VARBINARY(512)", self.ddl)


if __name__ == "__main__":
    unittest.main()
