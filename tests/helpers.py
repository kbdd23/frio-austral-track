"""Helpers compartidos para los tests (schema y datos de ejemplo)."""

from __future__ import annotations

from pathlib import Path

from src.auth import crear_hash_contrasena
from src.db_local import BaseDatosLocal

RUTA_SCHEMA_LOCAL = Path(__file__).resolve().parent.parent / "sql" / "schema_local.sql"

# Valor bajo de iteraciones solo para tests: acelera la suite sin debilitar el
# default de producción (600 000, en src/auth.py).
ITERACIONES_PRUEBA = 1000


def crear_base_local() -> BaseDatosLocal:
    base = BaseDatosLocal(":memory:")
    base.crear_esquema(RUTA_SCHEMA_LOCAL)
    return base


def sembrar_operacion(base) -> dict:
    """Crea Usuario/Conductor/Camion/Despacho y retorna sus ids.

    Funciona con cualquier base que exponga `conexion` (local o cloud).
    """
    conexion = base.conexion

    conexion.execute(
        "INSERT INTO Usuario (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)",
        ("Conductor", "conductor@x.cl",
         crear_hash_contrasena("contrasena", iteraciones=ITERACIONES_PRUEBA),
         "Conductor"),
    )
    id_usuario_conductor = conexion.execute(
        "SELECT id_usuario FROM Usuario WHERE email = ?", ("conductor@x.cl",)
    ).fetchone()["id_usuario"]

    conexion.execute(
        "INSERT INTO Conductor (id_usuario, licencia) VALUES (?, ?)",
        (id_usuario_conductor, "LIC-1"),
    )
    id_conductor = conexion.execute(
        "SELECT id_conductor FROM Conductor WHERE id_usuario = ?",
        (id_usuario_conductor,),
    ).fetchone()["id_conductor"]

    conexion.execute(
        "INSERT INTO Usuario (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)",
        ("Gerente", "gerente@x.cl",
         crear_hash_contrasena("gerente", iteraciones=ITERACIONES_PRUEBA),
         "Operaciones"),
    )
    id_usuario_gerente = conexion.execute(
        "SELECT id_usuario FROM Usuario WHERE email = ?", ("gerente@x.cl",)
    ).fetchone()["id_usuario"]

    conexion.execute(
        "INSERT INTO Camion (patente, estado) VALUES (?, ?)", ("AA-11", "En Ruta")
    )
    id_camion = conexion.execute(
        "SELECT id_camion FROM Camion WHERE patente = ?", ("AA-11",)
    ).fetchone()["id_camion"]

    conexion.execute(
        "INSERT INTO Despacho (id_camion, id_conductor, fecha_programada, estado) "
        "VALUES (?, ?, ?, ?)",
        (id_camion, id_conductor, "2026-11-14", "En Ruta"),
    )
    id_despacho = conexion.execute(
        "SELECT id_despacho FROM Despacho"
    ).fetchone()["id_despacho"]

    conexion.commit()
    return {
        "id_despacho": id_despacho,
        "id_conductor": id_conductor,
        "id_usuario_conductor": id_usuario_conductor,
        "id_usuario_gerente": id_usuario_gerente,
    }
