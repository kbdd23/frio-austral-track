-- Frío-Austral Track — Esquema CLOUD (MySQL 8 / PostgreSQL) del servidor central.
-- Deriva del modelo relacional de la Evaluación 2 (E2U2/artefactos/schema.sql).
--
-- A02: latitud/longitud se almacenan CIFRADAS en reposo (AES-256-GCM, base64).
-- A03: la capa de acceso usa consultas preparadas; este DDL no incluye datos.
-- La sincronización idempotente se apoya en `id_evento_local UNIQUE`.

CREATE TABLE Usuario (
  id_usuario INT PRIMARY KEY AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  email VARCHAR(120) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  rol VARCHAR(20) NOT NULL CHECK (rol IN ('Conductor','Operaciones','Cliente','Administrador')),
  activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE Conductor (
  id_conductor INT PRIMARY KEY AUTO_INCREMENT,
  id_usuario INT NOT NULL UNIQUE,
  licencia VARCHAR(30) NOT NULL,
  FOREIGN KEY (id_usuario) REFERENCES Usuario(id_usuario)
);

CREATE TABLE Camion (
  id_camion INT PRIMARY KEY AUTO_INCREMENT,
  patente VARCHAR(10) UNIQUE NOT NULL,
  estado VARCHAR(20) NOT NULL DEFAULT 'Disponible'
    CHECK (estado IN ('Disponible','En Ruta','Mantencion','Fuera de Servicio')),
  sensor_bt_mac VARCHAR(50) UNIQUE
);

CREATE TABLE Despacho (
  id_despacho INT PRIMARY KEY AUTO_INCREMENT,
  id_camion INT NOT NULL,
  id_conductor INT NOT NULL,
  fecha_programada DATE,
  estado VARCHAR(30) NOT NULL DEFAULT 'En Ruta'
    CHECK (estado IN ('En Bodega','En Ruta','Entregado conforme','Rechazado')),
  latitud_entrega VARBINARY(512),   -- cifrado en reposo (A02)
  longitud_entrega VARBINARY(512),  -- cifrado en reposo (A02)
  FOREIGN KEY (id_camion) REFERENCES Camion(id_camion),
  FOREIGN KEY (id_conductor) REFERENCES Conductor(id_conductor)
);

CREATE TABLE RegistroTemperatura (
  id_registro INT PRIMARY KEY AUTO_INCREMENT,
  id_despacho INT NOT NULL,
  fecha_hora DATETIME NOT NULL,
  temperatura DECIMAL(5,2) NOT NULL,
  estado_sincronizacion VARCHAR(30) NOT NULL DEFAULT 'Pendiente de sincronizar'
    CHECK (estado_sincronizacion IN ('Sincronizado','Pendiente de sincronizar')),
  id_evento_local VARCHAR(80) UNIQUE NOT NULL,
  latitud VARBINARY(512),           -- cifrado en reposo (A02)
  longitud VARBINARY(512),          -- cifrado en reposo (A02)
  FOREIGN KEY (id_despacho) REFERENCES Despacho(id_despacho),
  INDEX idx_registro_despacho_fecha (id_despacho, fecha_hora)
);

CREATE TABLE NotificacionAlerta (
  id_notificacion INT PRIMARY KEY AUTO_INCREMENT,
  id_registro INT NOT NULL,
  tipo VARCHAR(30) NOT NULL
    CHECK (tipo IN ('Umbral de -15C persistente','Ruptura de cadena de frio')),
  inicio_temporizador DATETIME,
  fecha_envio DATETIME NOT NULL,
  FOREIGN KEY (id_registro) REFERENCES RegistroTemperatura(id_registro)
);

-- Persistencia del temporizador del Módulo B (idéntico al esquema local).
CREATE TABLE EstadoTermico (
  id_despacho INT PRIMARY KEY,
  inicio_anomalia DATETIME NOT NULL,
  FOREIGN KEY (id_despacho) REFERENCES Despacho(id_despacho)
);
