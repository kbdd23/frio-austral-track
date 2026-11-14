-- Frío-Austral Track — Esquema LOCAL (SQLite) del dispositivo móvil del conductor.
-- Módulo A: operación offline con sincronización diferida.
--
-- A02: los campos latitud/longitud se almacenan CIFRADOS (nonce+tag+datos en
-- base64), producidos por src/crypto.py. El `id_evento_local` es el
-- identificador idempotente generado en origen para evitar duplicados al
-- re-sincronizar contra el cloud.

PRAGMA foreign_keys = ON;

CREATE TABLE Usuario (
  id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  rol TEXT NOT NULL CHECK (rol IN ('Conductor','Operaciones','Cliente','Administrador')),
  activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE Conductor (
  id_conductor INTEGER PRIMARY KEY AUTOINCREMENT,
  id_usuario INTEGER NOT NULL UNIQUE,
  licencia TEXT NOT NULL,
  FOREIGN KEY (id_usuario) REFERENCES Usuario(id_usuario)
);

CREATE TABLE Camion (
  id_camion INTEGER PRIMARY KEY AUTOINCREMENT,
  patente TEXT UNIQUE NOT NULL,
  estado TEXT NOT NULL DEFAULT 'Disponible'
    CHECK (estado IN ('Disponible','En Ruta','Mantencion','Fuera de Servicio')),
  sensor_bt_mac TEXT UNIQUE
);

CREATE TABLE Despacho (
  id_despacho INTEGER PRIMARY KEY AUTOINCREMENT,
  id_camion INTEGER NOT NULL,
  id_conductor INTEGER NOT NULL,
  fecha_programada TEXT,
  estado TEXT NOT NULL DEFAULT 'En Ruta'
    CHECK (estado IN ('En Bodega','En Ruta','Entregado conforme','Rechazado')),
  latitud_entrega TEXT,   -- cifrado en reposo (A02)
  longitud_entrega TEXT,  -- cifrado en reposo (A02)
  FOREIGN KEY (id_camion) REFERENCES Camion(id_camion),
  FOREIGN KEY (id_conductor) REFERENCES Conductor(id_conductor)
);

CREATE TABLE RegistroTemperatura (
  id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
  id_despacho INTEGER NOT NULL,
  fecha_hora TEXT NOT NULL,
  temperatura REAL NOT NULL,
  estado_sincronizacion TEXT NOT NULL DEFAULT 'Pendiente de sincronizar'
    CHECK (estado_sincronizacion IN ('Sincronizado','Pendiente de sincronizar')),
  id_evento_local TEXT UNIQUE NOT NULL,
  latitud TEXT,           -- cifrado en reposo (A02)
  longitud TEXT,          -- cifrado en reposo (A02)
  FOREIGN KEY (id_despacho) REFERENCES Despacho(id_despacho)
);

CREATE TABLE NotificacionAlerta (
  id_notificacion INTEGER PRIMARY KEY AUTOINCREMENT,
  id_registro INTEGER NOT NULL,
  tipo TEXT NOT NULL
    CHECK (tipo IN ('Umbral de -15C persistente','Ruptura de cadena de frio')),
  inicio_temporizador TEXT,
  fecha_envio TEXT NOT NULL,
  FOREIGN KEY (id_registro) REFERENCES RegistroTemperatura(id_registro)
);

-- Persistencia del temporizador del Módulo B. Guarda el instante en que
-- comienza la anomalía térmica para que el conteo sobreviva a reinicios.
CREATE TABLE EstadoTermico (
  id_despacho INTEGER PRIMARY KEY,
  inicio_anomalia TEXT NOT NULL,
  FOREIGN KEY (id_despacho) REFERENCES Despacho(id_despacho)
);
