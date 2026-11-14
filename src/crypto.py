"""A02:2021 — Cryptographic Failures.

Cifrado en reposo de datos sensibles (geolocalización) mediante AES-256-GCM,
un algoritmo autenticado que provee confidencialidad e integridad. El cifrado
en tránsito (TLS 1.3) se declara en el README; este prototipo no levanta
servidor, por lo que no hay canal de red que cifrar aquí.
"""

from __future__ import annotations

import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

LONGITUD_NONCE = 12  # bytes recomendados por el estándar para GCM.


class Cifrador:
    """Cifra y descifra campos sensibles con AES-256-GCM (autenticado)."""

    def __init__(self, clave: bytes):
        if len(clave) != 32:
            raise ValueError("La clave AES-256 debe tener exactamente 32 bytes.")
        self._aesgcm = AESGCM(clave)

    @classmethod
    def generar_clave(cls) -> bytes:
        """Genera una clave aleatoria de 256 bits."""
        return secrets.token_bytes(32)

    @classmethod
    def desde_entorno(cls) -> "Cifrador":
        """Construye el cifrador desde AES_KEY (base64) o genera una nueva."""
        clave_b64 = os.getenv("AES_KEY", "")
        if clave_b64:
            return cls(base64.b64decode(clave_b64))
        return cls(cls.generar_clave())

    def cifrar(self, texto_plano: str) -> str:
        """Devuelve nonce + ciphertext(+tag) codificados en base64."""
        nonce = secrets.token_bytes(LONGITUD_NONCE)
        datos = texto_plano.encode("utf-8")
        cifrado = self._aesgcm.encrypt(nonce, datos, None)
        return base64.b64encode(nonce + cifrado).decode("ascii")

    def descifrar(self, token: str) -> str:
        """Revierte `cifrar`. Lanza InvalidTag si el token fue alterado."""
        bruto = base64.b64decode(token.encode("ascii"))
        nonce = bruto[:LONGITUD_NONCE]
        cifrado = bruto[LONGITUD_NONCE:]
        plano = self._aesgcm.decrypt(nonce, cifrado, None)
        return plano.decode("utf-8")
