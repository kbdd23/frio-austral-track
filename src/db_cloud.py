"""Capa de acceso a la base cloud (PostgreSQL en producción).

En el prototipo, PostgreSQL se simula con otra base SQLite (`cloud.db`) para
que la demo sea ejecutable sin infraestructura externa. En producción, este
módulo apuntaría a PostgreSQL vía un driver con conexión TLS 1.3.

A03:2021 — Injection: consultas preparadas. Idempotencia: `INSERT OR IGNORE`
sobre `id_evento_local UNIQUE` evita duplicados al re-sincronizar.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class BaseDatosCloud:
    """Acceso a la base central (simulada con SQLite en el prototipo)."""

    def __init__(self, ruta: str = ":memory:"):
        self.conexion = sqlite3.connect(ruta)
        self.conexion.row_factory = sqlite3.Row
        self.conexion.execute("PRAGMA foreign_keys = ON")

    def crear_esquema(self, ruta_sql: str | Path) -> None:
        script = Path(ruta_sql).read_text(encoding="utf-8")
        self.conexion.executescript(script)
        self.conexion.commit()

    def insertar_lectura(self, lectura: dict[str, Any]) -> bool:
        """Inserta una lectura sincronizada. Devuelve True si se insertó.

        `INSERT OR IGNORE` garantiza idempotencia: si el id_evento_local ya
        existe (por una re-sincronización), no se duplica la lectura.
        """
        cursor = self.conexion.execute(
            "INSERT OR IGNORE INTO RegistroTemperatura "
            "(id_despacho, fecha_hora, temperatura, estado_sincronizacion, "
            " id_evento_local, latitud, longitud) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                lectura["id_despacho"],
                lectura["fecha_hora"],
                lectura["temperatura"],
                "Sincronizado",
                lectura["id_evento_local"],
                lectura["latitud"],
                lectura["longitud"],
            ),
        )
        self.conexion.commit()
        return cursor.rowcount > 0

    def total_lecturas(self) -> int:
        fila = self.conexion.execute(
            "SELECT COUNT(*) AS n FROM RegistroTemperatura"
        ).fetchone()
        return fila["n"]
