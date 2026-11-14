"""Módulo B: Evaluación Térmica y Alerta Crítica.

Evalúa si la temperatura reportada supera el umbral crítico (-15°C). Si la
anomalía persiste por más de 15 minutos, gatilla la alerta visual/sonora en la
app del conductor y dispara el correo de emergencia a Gerencia de Operaciones.
"""

from __future__ import annotations

import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from .config import SMTP, UMBRAL_CRITICO_C, VENTANA_PERSISTENCIA_MINUTOS


class Notificador:
    """Alertas visual/sonora y correo de emergencia (con dry-run si no hay SMTP)."""

    def __init__(self, config_smtp: dict | None = None):
        self.config_smtp = config_smtp or SMTP

    def alerta_visual(self, mensaje: str) -> str:
        # En la app móvil, esto se renderiza como banner/diálogo en pantalla.
        return mensaje

    def alerta_sonora(self) -> str:
        # Bell de terminal; en la app sería un tono/sonido del sistema.
        return "\a"

    def enviar_correo_emergencia(self, *, asunto: str, cuerpo: str) -> dict:
        """Envía el correo por SMTP; si no hay host configurado, hace dry-run.

        Un fallo de red/SMTP no propaga excepción: se retorna un estado de
        error para no interrumpir la evaluación térmica ni el bucle de
        telemetría. La alerta visual/sonora ya se emitió antes del correo.
        """
        host = self.config_smtp.get("host", "")
        if not host:
            return {"modo": "dry-run", "asunto": asunto, "cuerpo": cuerpo}

        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = self.config_smtp.get("user", "")
        mensaje["To"] = self.config_smtp.get("destinatario", "")
        mensaje.set_content(cuerpo)

        try:
            with smtplib.SMTP(host, int(self.config_smtp.get("port", 587))) as servidor:
                servidor.starttls()  # TLS en tránsito para el correo.
                usuario = self.config_smtp.get("user", "")
                clave = self.config_smtp.get("password", "")
                if usuario:
                    servidor.login(usuario, clave)
                servidor.send_message(mensaje)
        except (OSError, smtplib.SMTPException) as error:
            return {"modo": "error", "detalle": str(error), "asunto": asunto}

        return {"modo": "enviado", "asunto": asunto}


class EvaluadorTermico:
    """Aplica la regla de negocio del umbral crítico persistente.

    `repositorio` (opcional) permite persistir el temporizador y la alerta.
    Si se omite, el evaluador opera solo en memoria (útil para pruebas puras).
    """

    def __init__(
        self,
        *,
        notificador: Notificador | None = None,
        umbral_critico: float = UMBRAL_CRITICO_C,
        ventana_minutos: int = VENTANA_PERSISTENCIA_MINUTOS,
        repositorio=None,
        id_despacho: int | None = None,
    ):
        self.umbral = umbral_critico
        self.ventana_minutos = ventana_minutos
        self.ventana = timedelta(minutes=ventana_minutos)
        self.notificador = notificador or Notificador()
        self.repositorio = repositorio
        self.id_despacho = id_despacho
        self._inicio_anomalia: datetime | None = None
        self._alerta_activa = False

    def evaluar(
        self,
        temperatura: float,
        ahora: datetime | None = None,
        id_registro: int | None = None,
    ) -> str:
        """Devuelve 'OK', 'ANOMALIA' o 'ALERTA' según la regla de negocio.

        El temporizador se persiste para sobrevivir a reinicios y se reinicia
        solo cuando la temperatura vuelve al rango; no re-dispara mientras la
        anomalía continúa.
        """
        ahora = ahora or datetime.now()
        if temperatura > self.umbral:
            if self._inicio_anomalia is None:
                self._inicio_anomalia = self._recuperar_inicio() or ahora
                self._persistir_inicio(self._inicio_anomalia)
            if not self._alerta_activa and (ahora - self._inicio_anomalia) >= self.ventana:
                self._disparar_alerta(temperatura, ahora, id_registro)
                return "ALERTA"
            return "ANOMALIA"

        self._inicio_anomalia = None
        self._alerta_activa = False
        self._limpiar_inicio()
        return "OK"

    def _recuperar_inicio(self) -> datetime | None:
        if self.repositorio is not None and self.id_despacho is not None:
            return self.repositorio.obtener_inicio_anomalia(self.id_despacho)
        return None

    def _persistir_inicio(self, inicio: datetime) -> None:
        if self.repositorio is not None and self.id_despacho is not None:
            self.repositorio.guardar_inicio_anomalia(self.id_despacho, inicio)

    def _limpiar_inicio(self) -> None:
        if self.repositorio is not None and self.id_despacho is not None:
            self.repositorio.limpiar_inicio_anomalia(self.id_despacho)

    def _disparar_alerta(
        self, temperatura: float, ahora: datetime, id_registro: int | None
    ) -> None:
        inicio = self._inicio_anomalia
        mensaje = (
            f"ALERTA CRÍTICA: temperatura {temperatura:.1f}°C superó el umbral "
            f"de {self.umbral}°C durante más de {self.ventana_minutos} minutos."
        )
        self.notificador.alerta_visual(mensaje)
        self.notificador.alerta_sonora()
        self.notificador.enviar_correo_emergencia(
            asunto="[Frío-Austral Track] Ruptura de cadena de frío",
            cuerpo=mensaje,
        )
        if self.repositorio is not None and id_registro is not None:
            self.repositorio.guardar_notificacion(
                id_registro=id_registro,
                tipo="Umbral de -15C persistente",
                inicio_temporizador=inicio.isoformat() if inicio else None,
                fecha_envio=ahora.isoformat(),
            )
        self._alerta_activa = True
        self._inicio_anomalia = None
        self._limpiar_inicio()
