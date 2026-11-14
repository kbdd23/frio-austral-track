"""Capa de acceso a la base local (SQLite) del dispositivo móvil del conductor.

A03:2021 — Injection: todas las consultas usan parámetros (`?`) y nunca
concatenación de cadenas. A02:2021 — Cryptographic Failures: los campos
sensibles (latitud/longitud) se cifran antes de persistirlos.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .crypto import Cifrador


class BaseDatosLocal:
    """Acceso tipado y seguro a la base SQLite local del dispositivo."""

    def __init__(self, ruta: str = ":memory:", cifrador: Cifrador | None = None):
        self.conexion = sqlite3.connect(ruta)
        self.conexion.row_factory = sqlite3.Row
        self.conexion.execute("PRAGMA foreign_keys = ON")
        self.cifrador = cifrador

    def crear_esquema(self, ruta_sql: str | Path) -> None:
        script = Path(ruta_sql).read_text(encoding="utf-8")
        self.conexion.executescript(script)
        self.conexion.commit()

    def cifrar_campo(self, valor: Any) -> str | None:
        """Cifra un valor sensible si hay cifrador configurado (A02)."""
        if valor is None or self.cifrador is None:
            return valor
        return self.cifrador.cifrar(str(valor))

    def insertar_lectura(
        self,
        *,
        id_despacho: int,
        temperatura: float,
        latitud: float | None,
        longitud: float | None,
        estado: str,
        id_evento_local: str | None = None,
        fecha_hora: str | None = None,
    ) -> int:
        """Inserta una lectura con consulta preparada. Retorna el id_registro."""
        fecha_hora = fecha_hora or datetime.now().isoformat()
        id_evento_local = id_evento_local or uuid.uuid4().hex
        cursor = self.conexion.execute(
            "INSERT INTO RegistroTemperatura "
            "(id_despacho, fecha_hora, temperatura, estado_sincronizacion, "
            " id_evento_local, latitud, longitud) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                id_despacho,
                fecha_hora,
                temperatura,
                estado,
                id_evento_local,
                self.cifrar_campo(latitud),
                self.cifrar_campo(longitud),
            ),
        )
        self.conexion.commit()
        return cursor.lastrowid

    def lecturas_pendientes(self) -> list[sqlite3.Row]:
        return self.conexion.execute(
            "SELECT * FROM RegistroTemperatura "
            "WHERE estado_sincronizacion = ? ORDER BY id_registro",
            ("Pendiente de sincronizar",),
        ).fetchall()

    def marcar_sincronizado(self, id_registro: int) -> None:
        self.conexion.execute(
            "UPDATE RegistroTemperatura SET estado_sincronizacion = ? "
            "WHERE id_registro = ?",
            ("Sincronizado", id_registro),
        )
        self.conexion.commit()

    def guardar_notificacion(
        self,
        *,
        id_registro: int,
        tipo: str,
        inicio_temporizador: str | None,
        fecha_envio: str | None = None,
    ) -> int:
        fecha_envio = fecha_envio or datetime.now().isoformat()
        cursor = self.conexion.execute(
            "INSERT INTO NotificacionAlerta "
            "(id_registro, tipo, inicio_temporizador, fecha_envio) "
            "VALUES (?, ?, ?, ?)",
            (id_registro, tipo, inicio_temporizador, fecha_envio),
        )
        self.conexion.commit()
        return cursor.lastrowid

    def guardar_inicio_anomalia(self, id_despacho: int, inicio) -> None:
        """Persiste (UPSERT) el instante en que comienza una anomalía térmica."""
        inicio_iso = inicio.isoformat() if isinstance(inicio, datetime) else str(inicio)
        self.conexion.execute(
            "INSERT INTO EstadoTermico (id_despacho, inicio_anomalia) VALUES (?, ?) "
            "ON CONFLICT(id_despacho) DO UPDATE SET inicio_anomalia = excluded.inicio_anomalia",
            (id_despacho, inicio_iso),
        )
        self.conexion.commit()

    def obtener_inicio_anomalia(self, id_despacho: int) -> datetime | None:
        """Recupera el inicio de anomalía persistido, o None si no existe."""
        fila = self.conexion.execute(
            "SELECT inicio_anomalia FROM EstadoTermico WHERE id_despacho = ?",
            (id_despacho,),
        ).fetchone()
        if fila is None:
            return None
        return datetime.fromisoformat(fila["inicio_anomalia"])

    def limpiar_inicio_anomalia(self, id_despacho: int) -> None:
        """Elimina el estado de anomalía persistido al normalizar o disparar."""
        self.conexion.execute(
            "DELETE FROM EstadoTermico WHERE id_despacho = ?", (id_despacho,)
        )
        self.conexion.commit()

    def cerrar(self) -> None:
        self.conexion.close()
