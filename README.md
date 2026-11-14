# Frío-Austral Track — Prototipo Actividad 3

Prototipo en **Python puro** (sin framework web) para la Evaluación Sumativa N°3 de
Ingeniería de Software. Implementa los dos módulos críticos de la Fase 3 del caso
de estudio "Frío-Austral Track" y tres controles del OWASP Top 10.

- **Módulo A** — Sincronización Offline-Online y Almacenamiento Local.
- **Módulo B** — Evaluación Térmica y Alerta Crítica.

El enunciado pide "programar/simular" la lógica; por eso no hay interfaz web ni
app móvil, sino módulos de lógica pura más una demo de consola que reproduce el
flujo completo de telemetría.

## Estructura del proyecto

```
prototipo/
├── README.md
├── requirements.txt
├── sql/
│   ├── schema_local.sql    # SQLite del dispositivo móvil (offline)
│   └── schema_cloud.sql    # MySQL/PostgreSQL del servidor central
├── src/
│   ├── config.py           # umbrales, rutas y configuración SMTP
│   ├── auth.py             # A02 — hash PBKDF2 de credenciales
│   ├── crypto.py           # A02 — AES-256-GCM (geolocalización)
│   ├── db_local.py         # acceso SQLite local (A03 — parametrizado)
│   ├── db_cloud.py         # acceso cloud simulado (A03 — parametrizado)
│   ├── rbac.py             # A01 — control de acceso por roles
│   ├── modulo_a_sync.py    # Módulo A — sincronización offline-online
│   ├── modulo_b_termico.py # Módulo B — umbral crítico y alerta
│   ├── escenarios.py       # lógica de los flujos (demo y tests)
│   └── demo.py             # menú interactivo de escenarios
└── tests/
    ├── helpers.py
    ├── test_auth.py
    ├── test_crypto.py
    ├── test_flujo_completo.py
    ├── test_pentest.py
    ├── test_persistencia.py
    ├── test_rbac.py
    ├── test_schema_cloud.py
    ├── test_sync.py
    └── test_termico.py
```

## Requisitos

- Python 3.10 o superior.
- `cryptography` (única dependencia externa).

```bash
pip install -r requirements.txt
```

## Cómo ejecutar

```bash
# Ejecutar la suite de tests (46 casos)
python3 -m unittest discover -s tests -v

# Abrir la demo interactiva (ambas formas son válidas)
python3 -m src.demo
python3 src/demo.py
```

La demo es un menú de 6 opciones: flujo completo, Módulo A aislado, Módulo B
aislado, persistencia del temporizador, seguridad OWASP (A01/A02/A03) y
visualización de la flota. Cada opción recrea sus bases, así que se pueden
recorrer en cualquier orden.

## Módulo A — Sincronización Offline-Online

`src/modulo_a_sync.py`

- `Red` simula la señal 3G/4G/5G (`hay_conexion()`).
- `Sincronizador.registrar_lectura()` decide: con red publica y marca
  `Sincronizado`; sin red almacena `Pendiente de sincronizar` en SQLite local.
- `Sincronizador.sincronizar_pendientes()` sube la cola al detectar
  conectividad.
- **Idempotencia:** cada lectura nace con un `id_evento_local` único generado en
  origen. El cloud usa `INSERT OR IGNORE` sobre esa clave, de modo que una
  re-sincronización jamás duplica lecturas.

## Módulo B — Evaluación Térmica y Alerta Crítica

`src/modulo_b_termico.py`

- `EvaluadorTermico.evaluar()` compara contra el umbral crítico (-15°C).
- Si la anomalía persiste más de 15 minutos, `_disparar_alerta()` gatilla la
  alerta visual/sonora y el correo de emergencia a Gerencia de Operaciones.
- **Persistencia del temporizador:** el instante en que comienza la anomalía se
  guarda en la tabla `EstadoTermico`; si la app se reinicia, el conteo se
  recupera y no se pierde la ventana de 15 minutos.
- **Trazabilidad de la alerta:** al disparar se registra una fila en
  `NotificacionAlerta` (con el `id_registro` que la gatilló y el
  `inicio_temporizador`).
- El temporizador se reinicia solo al volver al rango, y no re-dispara mientras
  la anomalía continúa.

## Mapeo de controles OWASP Top 10

| OWASP 2021 | Control implementado | Dónde |
|---|---|---|
| A01 — Broken Access Control | RBAC: conductor ve solo su ruta del día; gerente ve el dashboard. El `id_conductor` se obtiene de la sesión, no del cliente. | `src/rbac.py` |
| A02 — Cryptographic Failures | Cifrado en reposo de geolocalización con AES-256-GCM; hash salado PBKDF2-HMAC-SHA256 para credenciales. TLS 1.3 declarado para el tránsito. | `src/crypto.py`, `src/auth.py`, `src/db_local.py` |
| A03 — Injection | Consultas SQL 100% parametrizadas (`?`), sin concatenación de cadenas. | `src/db_local.py`, `src/db_cloud.py` |

## Pruebas con mentalidad adversaria

`tests/test_pentest.py` intenta violar los controles y documenta que fracasan:
login con contraseña incorrecta, ataque de diccionario, hash no reversible,
escalada de privilegios (conductor → dashboard), acceso horizontal (gerente →
ruta de conductor), rol inexistente e inyección SQL vía `id_evento_local`.

## Notas de producción

- En producción, `BaseDatosCloud` apuntaría a **PostgreSQL** vía driver con
  conexión **TLS 1.3**; aquí se simula con otra base SQLite en memoria para que
  la demo corra sin infraestructura externa.
- La geolocalización se cifra en reposo con **AES-256-GCM**; como alternativa
  móvil se menciona **SQLCipher** en el enunciado. Las credenciales se protegen
  con **hash salado PBKDF2** (no cifrado reversible).
- El correo de emergencia funciona con **SMTP + STARTTLS**. Si no se configuran
  variables `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` y `SMTP_TO`, el envío se
  hace en modo *dry-run* (se imprime en consola).
- La clave de cifrado se inyecta vía variable de entorno `AES_KEY` (base64 de 32
  bytes); si no existe, se genera una aleatoria en tiempo de ejecución.
