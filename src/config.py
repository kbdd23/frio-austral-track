"""Configuración central del prototipo Frío-Austral Track (Actividad 3)."""

from __future__ import annotations

import os
from pathlib import Path

# Umbrales del dominio (Caso de Estudio Frío-Austral).
UMBRAL_CRITICO_C = -15.0            # Sobre este valor se considera anomalía térmica.
VENTANA_PERSISTENCIA_MINUTOS = 15   # Tiempo que la anomalía debe persistir para alertar.
RANGO_CADENA_FRIO_C = (-22.0, -18.0)

# Rutas de las bases de datos de demostración.
DIR_PROYECTO = Path(__file__).resolve().parent.parent
DIR_SQL = DIR_PROYECTO / "sql"
RUTA_DB_LOCAL = DIR_PROYECTO / "local.db"
RUTA_DB_CLOUD = DIR_PROYECTO / "cloud.db"

# Configuración SMTP (correo de emergencia). Si el host está vacío, el envío
# se simula en consola (dry-run) para no depender de credenciales reales.
SMTP = {
    "host": os.getenv("SMTP_HOST", ""),
    "port": int(os.getenv("SMTP_PORT", "587")),
    "user": os.getenv("SMTP_USER", ""),
    "password": os.getenv("SMTP_PASSWORD", ""),
    "destinatario": os.getenv("SMTP_TO", ""),
}
