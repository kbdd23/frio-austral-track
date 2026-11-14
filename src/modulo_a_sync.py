"""Módulo A: Sincronización Offline-Online y Almacenamiento Local.

Recibe la lectura de temperatura desde la app móvil, verifica la señal de red
(3G/4G/5G) y:
  - Con red: publica directo al Cloud y marca 'Sincronizado'.
  - Sin red: almacena con estado 'Pendiente de sincronizar' en SQLite local.
  - Al reconectar: sincroniza automáticamente los pendientes (idempotente).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from .db_cloud import BaseDatosCloud
from .db_local import BaseDatosLocal


class Red:
    """Simula la conectividad 3G/4G/5G del dispositivo móvil."""

    def __init__(self, conectado: bool = True):
        self.conectado = conectado

    def hay_conexion(self) -> bool:
        return self.conectado


class CloudGateway:
    """Representa el API Gateway del proveedor cloud.

    En producción, `publicar` haría un POST HTTPS/REST (TLS 1.3). En el
    prototipo, escribe directo en la base cloud simulada.
    """

    def __init__(self, base_cloud: BaseDatosCloud):
        self.base_cloud = base_cloud

    def publicar(self, lectura: dict[str, Any]) -> bool:
        return self.base_cloud.insertar_lectura(lectura)


class Sincronizador:
    """Orquesta el registro local y la sincronización diferida con el cloud."""

    def __init__(
        self,
        base_local: BaseDatosLocal,
        red: Red,
        gateway: CloudGateway,
    ):
        self.base_local = base_local
        self.red = red
        self.gateway = gateway

    def registrar_lectura(
        self,
        *,
        id_despacho: int,
        temperatura: float,
        latitud: float,
        longitud: float,
    ) -> tuple[str, str, int]:
        """Registra la lectura y, si hay red, la publica.

        Retorna `(estado, id_evento_local, id_registro)`. El `id_evento_local`
        es el identificador idempotente generado una única vez en origen; el
        `id_registro` es la clave autogenerada local para trazabilidad.
        """
        fecha_hora = datetime.now().isoformat()
        id_evento_local = uuid.uuid4().hex
        lectura = {
            "id_despacho": id_despacho,
            "fecha_hora": fecha_hora,
            "temperatura": temperatura,
            "id_evento_local": id_evento_local,
            "latitud": self.base_local.cifrar_campo(latitud),
            "longitud": self.base_local.cifrar_campo(longitud),
        }

        estado = "Sincronizado" if self.red.hay_conexion() else "Pendiente de sincronizar"
        if estado == "Sincronizado" and not self.gateway.publicar(lectura):
            estado = "Pendiente de sincronizar"

        id_registro = self.base_local.insertar_lectura(
            id_despacho=id_despacho,
            temperatura=temperatura,
            latitud=latitud,
            longitud=longitud,
            estado=estado,
            id_evento_local=id_evento_local,
            fecha_hora=fecha_hora,
        )
        return estado, id_evento_local, id_registro

    def sincronizar_pendientes(self) -> int:
        """Sube los registros 'Pendiente' al cloud y los marca sincronizados.

        Retorna cuántos registros se sincronizaron. La operación es idempotente
        gracias al `INSERT OR IGNORE` del gateway.
        """
        pendientes = self.base_local.lecturas_pendientes()
        sincronizados = 0
        for lectura in pendientes:
            datos = {
                "id_despacho": lectura["id_despacho"],
                "fecha_hora": lectura["fecha_hora"],
                "temperatura": lectura["temperatura"],
                "id_evento_local": lectura["id_evento_local"],
                "latitud": lectura["latitud"],
                "longitud": lectura["longitud"],
            }
            if self.gateway.publicar(datos):
                self.base_local.marcar_sincronizado(lectura["id_registro"])
                sincronizados += 1
        return sincronizados
