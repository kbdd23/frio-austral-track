"""Demo interactiva de la Actividad 3 — Frío-Austral Track.

Menú para recorrer por separado cada flujo del prototipo. La lógica de los
escenarios vive en src/escenarios.py (compartida con los tests).

Ejecutar desde la raíz del prototipo:
    python3 -m src.demo
    python3 src/demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    # Permite ejecutar el archivo directamente: python3 src/demo.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "src"

from . import escenarios
from .crypto import Cifrador

MENU = """
=====================================================
 Frío-Austral Track — Demo interactiva (Actividad 3)
=====================================================
 1) Flujo completo (Módulo A + B + RBAC)
 2) Módulo A — corte de red y sincronización diferida
 3) Módulo B — anomalía persistente y alerta
 4) Módulo B — persistencia tras "reinicio" del proceso
 5) Seguridad OWASP (A01/A02/A03)
 6) Ver flota
 0) Salir
"""

SUBMENU_SEGURIDAD = """
  --- Seguridad OWASP ---
  1) A01 — RBAC: conductor vs gerente
  2) A02 — Cifrado AES-256-GCM + hash PBKDF2
  3) A03 — Injection: payload bloqueado
  0) Volver
"""


def _imprimir_log(resultado: dict) -> None:
    for linea in resultado["log"]:
        print(linea)


def _opcion_1() -> None:
    base_local, base_cloud = escenarios.crear_bases(Cifrador(Cifrador.generar_clave()))
    datos = escenarios.sembrar_operacion(base_local)
    escenarios.sembrar_operacion(base_cloud)
    resultado = escenarios.ejecutar_flujo_completo(base_local, base_cloud, datos)
    _imprimir_log(resultado)
    print()
    print(f"  Lecturas en cloud: {resultado['lecturas_cloud']}")
    print(f"  Pendientes en local: {resultado['pendientes']}")
    print(f"  Alertas persistidas: {resultado['alertas']}")


def _opcion_2() -> None:
    base_local, base_cloud = escenarios.crear_bases()
    datos = escenarios.sembrar_operacion(base_local)
    escenarios.sembrar_operacion(base_cloud)
    resultado = escenarios.ejecutar_modulo_a(base_local, base_cloud, datos)
    _imprimir_log(resultado)
    print()
    print(f"  Lecturas en cloud: {resultado['lecturas_cloud']}")
    print(f"  Pendientes en local: {resultado['pendientes']}")


def _opcion_3() -> None:
    base_local, _base_cloud = escenarios.crear_bases()
    datos = escenarios.sembrar_operacion(base_local)
    resultado = escenarios.ejecutar_modulo_b(base_local, datos)
    _imprimir_log(resultado)
    print()
    print(f"  Alertas persistidas: {resultado['alertas']}")


def _opcion_4() -> None:
    base_local, _base_cloud = escenarios.crear_bases()
    datos = escenarios.sembrar_operacion(base_local)
    resultado = escenarios.ejecutar_persistencia(base_local, datos)
    _imprimir_log(resultado)


def _opcion_5() -> None:
    """Submenú de seguridad OWASP (A01, A02, A03)."""
    print(SUBMENU_SEGURIDAD)
    while True:
        try:
            subopcion = input("  Subopción: ").strip()
        except EOFError:
            print()
            return
        if subopcion == "0":
            return

        base_local, _base_cloud = escenarios.crear_bases()
        datos = escenarios.sembrar_operacion(base_local)

        if subopcion == "1":
            _imprimir_log(escenarios.ejecutar_rbac(base_local, datos))
        elif subopcion == "2":
            _imprimir_log(escenarios.ejecutar_a02_cifrado(base_local, datos))
        elif subopcion == "3":
            _imprimir_log(escenarios.ejecutar_a03_injection(base_local, datos))
        else:
            print("  Subopción inválida.")
        print()
        print(SUBMENU_SEGURIDAD)


def _opcion_6() -> None:
    base_local, _base_cloud = escenarios.crear_bases()
    escenarios.sembrar_operacion(base_local)
    escenarios.sembrar_flota(base_local, total=35)
    filas = escenarios.ver_flota(base_local)
    print(f"  {'Patente':<10} {'Estado':<18} {'En ruta'}")
    print("  " + "-" * 40)
    for fila in filas:
        print(f"  {fila['patente']:<10} {fila['estado']:<18} {'sí' if fila['en_ruta'] else 'no'}")
    print()
    print(f"  Total camiones: {len(filas)}")


OPCIONES = {
    "1": _opcion_1,
    "2": _opcion_2,
    "3": _opcion_3,
    "4": _opcion_4,
    "5": _opcion_5,
    "6": _opcion_6,
}


def main() -> None:
    print(MENU)
    while True:
        try:
            opcion = input("Selecciona una opción: ").strip()
        except EOFError:
            print()
            break
        if opcion == "0":
            print("Hasta luego.")
            break
        accion = OPCIONES.get(opcion)
        if accion is None:
            print("Opción inválida.")
            continue
        print()
        accion()
        print()
        print(MENU)


if __name__ == "__main__":
    main()
