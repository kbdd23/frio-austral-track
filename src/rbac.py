"""A01:2021 — Broken Access Control.

Control de acceso basado en roles (RBAC). El control se aplica en la capa de
datos, no en la interfaz: un conductor solo puede leer SU ruta del día; los
gerentes acceden al dashboard completo. El `id_conductor` se obtiene siempre
de la sesión autenticada, nunca de parámetros controlados por el cliente.
"""

from __future__ import annotations

from dataclasses import dataclass

ROLES = ("Conductor", "Operaciones", "Cliente", "Administrador")


class AccesoDenegado(PermissionError):
    """Se lanza cuando una sesión intenta acceder a un recurso no autorizado."""


@dataclass(frozen=True)
class Sesion:
    id_usuario: int
    rol: str
    id_conductor: int | None = None

    def __post_init__(self) -> None:
        if self.rol not in ROLES:
            raise ValueError(f"Rol inválido: {self.rol}")


def _exigir_rol(sesion: Sesion, roles_permitidos: tuple[str, ...]) -> None:
    if sesion.rol not in roles_permitidos:
        raise AccesoDenegado(
            f"Acceso denegado: el rol '{sesion.rol}' no está autorizado."
        )


def obtener_ruta_conductor(conexion, sesion: Sesion):
    """Retorna el despacho activo del conductor autenticado.

    Regla de negocio: el conductor SOLO ve su propia ruta del día. El
    `id_conductor` proviene de la sesión, jamás del argumento de la consulta.
    """
    _exigir_rol(sesion, ("Conductor",))
    if sesion.id_conductor is None:
        raise AccesoDenegado("La sesión de conductor no tiene id_conductor asociado.")
    return conexion.execute(
        "SELECT id_despacho, id_camion, estado, fecha_programada "
        "FROM Despacho WHERE id_conductor = ? AND estado = 'En Ruta' "
        "ORDER BY fecha_programada LIMIT 1",
        (sesion.id_conductor,),
    ).fetchone()


def obtener_dashboard(conexion, sesion: Sesion):
    """Retorna el resumen operacional. Solo gerencia/administración."""
    _exigir_rol(sesion, ("Operaciones", "Administrador"))
    return conexion.execute(
        "SELECT COUNT(*) AS total_despachos, "
        "SUM(CASE WHEN estado = 'En Ruta' THEN 1 ELSE 0 END) AS en_ruta "
        "FROM Despacho"
    ).fetchone()
