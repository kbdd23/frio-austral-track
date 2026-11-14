"""A02:2021 — Protección de credenciales en reposo.

Las contraseñas NO se cifran (el cifrado es reversible y por tanto un
antipatrón para este fin): se almacenan como HASH salado derivado con
PBKDF2-HMAC-SHA256 (RFC 2898). La verificación se hace en tiempo constante
para no filtrar información por diferencia de tiempos (timing attack).
"""

from __future__ import annotations

import hashlib
import secrets

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 600_000
LONGITUD_SALT_BYTES = 16


def crear_hash_contrasena(contrasena: str, iteraciones: int = ITERACIONES) -> str:
    """Retorna un hash salado con formato 'algo$iteraciones$salt$digesto'.

    `iteraciones` es inyectable para poder usar un valor bajo en tests; el
    valor por defecto (600 000) es el recomendado por OWASP para PBKDF2-SHA256.
    """
    salt = secrets.token_bytes(LONGITUD_SALT_BYTES)
    digesto = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), salt, iteraciones
    )
    return f"{ALGORITMO}${iteraciones}${salt.hex()}${digesto.hex()}"


def verificar_contrasena(contrasena: str, hash_almacenado: str) -> bool:
    """Verifica una contraseña contra su hash, en tiempo constante."""
    try:
        algoritmo, iteraciones, salt_hex, digesto_hex = hash_almacenado.split("$")
    except (ValueError, AttributeError):
        return False

    if algoritmo != ALGORITMO:
        return False

    try:
        salt = bytes.fromhex(salt_hex)
        digesto_esperado = bytes.fromhex(digesto_hex)
    except ValueError:
        return False

    digesto_calculado = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), salt, int(iteraciones)
    )
    return secrets.compare_digest(digesto_calculado, digesto_esperado)
