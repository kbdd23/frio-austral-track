"""Escenarios de demostración de la Actividad 3 — Frío-Austral Track.

La lógica de cada flujo vive aquí para poder ser reutilizada tanto por el menú
interactivo (src/demo.py) como por los tests automatizados
(tests/test_flujo_completo.py).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .auth import ITERACIONES, crear_hash_contrasena
from .config import DIR_SQL
from .crypto import Cifrador
from .db_cloud import BaseDatosCloud
from .db_local import BaseDatosLocal
from .modulo_a_sync import CloudGateway, Red, Sincronizador
from .modulo_b_termico import EvaluadorTermico
from .rbac import AccesoDenegado, Sesion, obtener_dashboard, obtener_ruta_conductor

T0 = datetime(2026, 11, 14, 8, 0, 0)


def crear_bases(cifrador=None) -> tuple[BaseDatosLocal, BaseDatosCloud]:
    """Crea las bases local y cloud en memoria con sus esquemas.

    Si no se entrega un cifrador, se genera uno por defecto para que toda la
    geolocalización quede cifrada en reposo (A02) en todos los escenarios.
    """
    if cifrador is None:
        cifrador = Cifrador(Cifrador.generar_clave())
    base_local = BaseDatosLocal(":memory:", cifrador=cifrador)
    base_local.crear_esquema(DIR_SQL / "schema_local.sql")
    base_cloud = BaseDatosCloud(":memory:")
    base_cloud.crear_esquema(DIR_SQL / "schema_local.sql")
    return base_local, base_cloud


def sembrar_operacion(base, iteraciones: int = ITERACIONES) -> dict:
    """Crea conductor, gerente, camión en ruta y despacho. Retorna ids."""
    conexion = base.conexion
    conexion.execute(
        "INSERT INTO Usuario (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)",
        ("Conductor Demo", "conductor@frio-austral.cl",
         crear_hash_contrasena("contrasena123", iteraciones=iteraciones), "Conductor"),
    )
    id_usuario = conexion.execute(
        "SELECT id_usuario FROM Usuario WHERE email = ?",
        ("conductor@frio-austral.cl",),
    ).fetchone()["id_usuario"]

    conexion.execute(
        "INSERT INTO Conductor (id_usuario, licencia) VALUES (?, ?)",
        (id_usuario, "LIC-12345"),
    )
    id_conductor = conexion.execute(
        "SELECT id_conductor FROM Conductor WHERE id_usuario = ?", (id_usuario,)
    ).fetchone()["id_conductor"]

    conexion.execute(
        "INSERT INTO Usuario (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)",
        ("Gerente Demo", "gerente@frio-austral.cl",
         crear_hash_contrasena("gerente123", iteraciones=iteraciones), "Operaciones"),
    )
    id_gerente = conexion.execute(
        "SELECT id_usuario FROM Usuario WHERE email = ?", ("gerente@frio-austral.cl",)
    ).fetchone()["id_usuario"]

    conexion.execute(
        "INSERT INTO Camion (patente, estado) VALUES (?, ?)", ("BB-22-33", "En Ruta")
    )
    id_camion = conexion.execute(
        "SELECT id_camion FROM Camion WHERE patente = ?", ("BB-22-33",)
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
        "id_usuario": id_usuario,
        "id_conductor": id_conductor,
        "id_gerente": id_gerente,
        "id_despacho": id_despacho,
    }


def sembrar_flota(base, total: int = 35) -> None:
    """Agrega camiones con estados variados hasta completar `total`."""
    estados = ["Disponible", "En Ruta", "Mantencion", "Fuera de Servicio"]
    existentes = base.conexion.execute(
        "SELECT COUNT(*) AS n FROM Camion"
    ).fetchone()["n"]
    for numero in range(existentes, total):
        patente = f"FL-{numero + 1:02d}"
        estado = estados[numero % len(estados)]
        base.conexion.execute(
            "INSERT INTO Camion (patente, estado) VALUES (?, ?)", (patente, estado)
        )
    base.conexion.commit()


def ejecutar_flujo_completo(base_local, base_cloud, datos) -> dict:
    """Módulo A + B + RBAC en una sola corrida de telemetría."""
    log = []
    red = Red(conectado=True)
    gateway = CloudGateway(base_cloud)
    sincronizador = Sincronizador(base_local, red, gateway)
    evaluador = EvaluadorTermico(
        repositorio=base_local, id_despacho=datos["id_despacho"]
    )
    id_despacho = datos["id_despacho"]

    escenario = [
        (0, -19.0, True),
        (5, -19.5, True),
        (10, -19.0, True),
        (15, -14.0, False),
        (20, -14.5, False),
        (25, -14.0, False),
        (30, -14.5, False),
        (35, -14.0, True),
        (40, -14.0, True),
        (45, -18.0, True),
    ]

    for minuto, temperatura, conectado in escenario:
        ahora = T0 + timedelta(minutes=minuto)
        red.conectado = conectado
        estado, _id_evento, id_registro = sincronizador.registrar_lectura(
            id_despacho=id_despacho,
            temperatura=temperatura,
            latitud=-41.47,
            longitud=-72.93,
        )
        if minuto == 35:
            subidos = sincronizador.sincronizar_pendientes()
            log.append(f"  [reconexión] sincronizados {subidos} registros pendientes.")
        veredicto = evaluador.evaluar(temperatura, ahora, id_registro=id_registro)
        senal = "ONLINE " if conectado else "OFFLINE"
        log.append(
            f"  {minuto:>3} min | {senal} | {temperatura:>5}°C | "
            f"estado={estado} | térmico={veredicto}"
        )

    alertas = base_local.conexion.execute(
        "SELECT COUNT(*) AS n FROM NotificacionAlerta"
    ).fetchone()["n"]

    return {
        "log": log,
        "lecturas_cloud": base_cloud.total_lecturas(),
        "pendientes": len(base_local.lecturas_pendientes()),
        "alertas": alertas,
    }


def ejecutar_modulo_a(base_local, base_cloud, datos) -> dict:
    """Corte de red con acumulación de pendientes y reconexión."""
    log = []
    red = Red(conectado=True)
    gateway = CloudGateway(base_cloud)
    sincronizador = Sincronizador(base_local, red, gateway)
    id_despacho = datos["id_despacho"]

    pasos = [
        (0, -19.0, True),
        (5, -19.2, True),
        (10, -19.1, False),
        (15, -19.3, False),
        (20, -19.0, False),
        (25, -19.4, True),
    ]
    for minuto, temperatura, conectado in pasos:
        red.conectado = conectado
        estado, _id_evento, _id_registro = sincronizador.registrar_lectura(
            id_despacho=id_despacho,
            temperatura=temperatura,
            latitud=-41.47,
            longitud=-72.93,
        )
        if minuto == 25:
            subidos = sincronizador.sincronizar_pendientes()
            log.append(f"  [reconexión] sincronizados {subidos} registros pendientes.")
        senal = "ONLINE " if conectado else "OFFLINE"
        log.append(f"  {minuto:>3} min | {senal} | {temperatura:>5}°C | estado={estado}")

    return {
        "log": log,
        "lecturas_cloud": base_cloud.total_lecturas(),
        "pendientes": len(base_local.lecturas_pendientes()),
    }


def ejecutar_modulo_b(base_local, datos) -> dict:
    """Anomalía térmica que alcanza los 15 minutos y dispara la alerta."""
    log = []
    evaluador = EvaluadorTermico(
        repositorio=base_local, id_despacho=datos["id_despacho"]
    )
    id_despacho = datos["id_despacho"]

    escenario = [
        (0, -19.0),
        (5, -16.0),
        (10, -14.0),
        (15, -14.0),
        (20, -14.0),
        (25, -14.0),
        (30, -18.0),
    ]
    for minuto, temperatura in escenario:
        ahora = T0 + timedelta(minutes=minuto)
        id_registro = base_local.insertar_lectura(
            id_despacho=id_despacho,
            temperatura=temperatura,
            latitud=-41.47,
            longitud=-72.93,
            estado="Pendiente de sincronizar",
            fecha_hora=ahora.isoformat(),
        )
        veredicto = evaluador.evaluar(temperatura, ahora, id_registro=id_registro)
        log.append(f"  {minuto:>3} min | {temperatura:>5}°C | térmico={veredicto}")

    alertas = base_local.conexion.execute(
        "SELECT COUNT(*) AS n FROM NotificacionAlerta"
    ).fetchone()["n"]
    return {"log": log, "alertas": alertas}


def ejecutar_persistencia(base_local, datos) -> dict:
    """El temporizador sobrevive al reinicio simulado del evaluador."""
    log = []
    id_despacho = datos["id_despacho"]

    evaluador = EvaluadorTermico(repositorio=base_local, id_despacho=id_despacho)
    id_registro = base_local.insertar_lectura(
        id_despacho=id_despacho,
        temperatura=-14.0,
        latitud=-41.47,
        longitud=-72.93,
        estado="Pendiente de sincronizar",
        fecha_hora=T0.isoformat(),
    )
    evaluador.evaluar(-14.0, T0, id_registro=id_registro)
    inicio = base_local.obtener_inicio_anomalia(id_despacho)
    log.append(
        "  inicio de anomalía persistido: "
        + (inicio.isoformat() if inicio else "ninguno")
    )

    # Reinicio simulado: nuevo evaluador sobre el mismo repositorio.
    evaluador2 = EvaluadorTermico(repositorio=base_local, id_despacho=id_despacho)
    veredicto = evaluador2.evaluar(
        -14.0, T0 + timedelta(minutes=16), id_registro=id_registro
    )
    log.append(f"  tras reinicio (16 min): térmico={veredicto}")
    return {"log": log, "veredicto": veredicto}


def ejecutar_rbac(base_local, datos) -> dict:
    """Conductor limitado a su ruta; gerente con dashboard completo."""
    log = []
    sesion_conductor = Sesion(
        id_usuario=datos["id_usuario"],
        rol="Conductor",
        id_conductor=datos["id_conductor"],
    )
    ruta = obtener_ruta_conductor(base_local.conexion, sesion_conductor)
    log.append(
        "  Conductor ve su despacho: " + ("En Ruta" if ruta else "ninguno")
    )

    try:
        obtener_dashboard(base_local.conexion, sesion_conductor)
        log.append("  ERROR: el conductor accedió al dashboard (fallo de control)")
    except AccesoDenegado:
        log.append("  Conductor BLOQUEADO en dashboard (AccesoDenegado)")

    sesion_gerente = Sesion(id_usuario=datos["id_gerente"], rol="Operaciones")
    dashboard = obtener_dashboard(base_local.conexion, sesion_gerente)
    log.append(
        f"  Gerente ve dashboard: {dashboard['total_despachos']} despachos, "
        f"{dashboard['en_ruta']} en ruta"
    )
    return {"log": log}


def ejecutar_a02_cifrado(base_local, datos) -> dict:
    """Demuestra A02: cifrado en reposo (AES-256-GCM) y hash de credenciales."""
    log = []
    if base_local.cifrador is None:
        log.append("  (la base no tiene cifrador configurado)")
        return {"log": log, "cifrado_ok": False}

    latitud_claro = -41.47
    longitud_claro = -72.93
    id_registro = base_local.insertar_lectura(
        id_despacho=datos["id_despacho"],
        temperatura=-19.0,
        latitud=latitud_claro,
        longitud=longitud_claro,
        estado="Pendiente de sincronizar",
    )
    fila = base_local.conexion.execute(
        "SELECT latitud, longitud FROM RegistroTemperatura WHERE id_registro = ?",
        (id_registro,),
    ).fetchone()
    latitud_cifrada = fila["latitud"]
    latitud_descifrada = base_local.cifrador.descifrar(latitud_cifrada)

    log.append(f"  latitud en claro:       {latitud_claro}")
    log.append(f"  latitud almacenada:     {latitud_cifrada[:28]}...")
    log.append(f"  latitud descifrada:     {latitud_descifrada}")
    cifrado_ok = float(latitud_descifrada) == latitud_claro
    log.append(f"  ¿descifrado coincide?:  {cifrado_ok}")

    hash_contrasena = crear_hash_contrasena("contrasena123", iteraciones=1000)
    log.append(f"  hash de credencial:     {hash_contrasena[:34]}...")
    log.append("  ¿reversible?:           no (PBKDF2 salado, unidireccional)")
    return {"log": log, "cifrado_ok": cifrado_ok}


def ejecutar_a03_injection(base_local, datos) -> dict:
    """Demuestra A03: un payload de inyección SQL se trata como dato literal."""
    log = []
    payload = "x'; DROP TABLE RegistroTemperatura; --"
    base_local.insertar_lectura(
        id_despacho=datos["id_despacho"],
        temperatura=-19.0,
        latitud=-41.0,
        longitud=-72.0,
        estado="Pendiente de sincronizar",
        id_evento_local=payload,
    )
    fila = base_local.conexion.execute(
        "SELECT id_evento_local FROM RegistroTemperatura WHERE id_evento_local = ?",
        (payload,),
    ).fetchone()
    tabla = base_local.conexion.execute(
        "SELECT name FROM sqlite_master WHERE name = 'RegistroTemperatura'"
    ).fetchone()

    payload_literal = fila is not None and fila["id_evento_local"] == payload
    tabla_intacta = tabla is not None
    log.append(f"  payload enviado:        {payload}")
    log.append(f"  guardado literal:       {payload_literal}")
    log.append(f"  tabla intacta:          {tabla_intacta}")
    return {
        "log": log,
        "payload_literal": payload_literal,
        "tabla_intacta": tabla_intacta,
    }


def ver_flota(base_local):
    """Retorna los camiones con su estado y si tienen despacho en ruta."""
    return base_local.conexion.execute(
        "SELECT c.patente, c.estado, "
        "(SELECT COUNT(*) FROM Despacho d "
        " WHERE d.id_camion = c.id_camion AND d.estado = 'En Ruta') AS en_ruta "
        "FROM Camion c ORDER BY c.patente"
    ).fetchall()
