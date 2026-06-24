CREATE DATABASE IF NOT EXISTS vehicle_data_hub CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE vehicle_data_hub;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  display_name VARCHAR(64),
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'admin',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vendor_accounts (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  vendor_type VARCHAR(32) NOT NULL,
  environment VARCHAR(32) NOT NULL DEFAULT 'test',
  base_url VARCHAR(255),
  config JSON NOT NULL,
  secret_config JSON NOT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_vendor_type (vendor_type),
  INDEX idx_vendor_enabled (is_enabled)
);

CREATE TABLE IF NOT EXISTS regulatory_platforms (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  city_code VARCHAR(32) NOT NULL,
  platform_type VARCHAR(32) NOT NULL,
  host VARCHAR(255) NOT NULL,
  port INT NOT NULL,
  coordinate_system VARCHAR(16) NOT NULL DEFAULT 'WGS84',
  report_frequency_hz INT NOT NULL DEFAULT 10,
  fault_frequency_hz INT NOT NULL DEFAULT 1,
  config JSON NOT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_platform_city (city_code),
  INDEX idx_platform_enabled (is_enabled)
);

CREATE TABLE IF NOT EXISTS vehicles (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  vin VARCHAR(64) UNIQUE,
  plate_no VARCHAR(32),
  model VARCHAR(64),
  brand VARCHAR(64),
  vehicle_category VARCHAR(32),
  power_type VARCHAR(32),
  project_code VARCHAR(64),
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_vehicle_status (status),
  INDEX idx_vehicle_project (project_code)
);

CREATE TABLE IF NOT EXISTS vehicle_vendor_bindings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id BIGINT NOT NULL,
  vendor_id BIGINT NOT NULL,
  vendor_vehicle_id VARCHAR(128) NOT NULL,
  vendor_vehicle_name VARCHAR(128),
  vendor_vin VARCHAR(64),
  is_primary BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_vvb_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  CONSTRAINT fk_vvb_vendor FOREIGN KEY (vendor_id) REFERENCES vendor_accounts(id),
  UNIQUE KEY uk_vendor_vehicle (vendor_id, vendor_vehicle_id),
  INDEX idx_vvb_vehicle (vehicle_id)
);

CREATE TABLE IF NOT EXISTS vehicle_certificates (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  vehicle_id BIGINT,
  certificate_path VARCHAR(512) NOT NULL,
  private_key_path VARCHAR(512),
  ca_certificate_path VARCHAR(512),
  expires_at DATETIME,
  fingerprint VARCHAR(128),
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_cert_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  INDEX idx_cert_vehicle (vehicle_id),
  INDEX idx_cert_enabled (is_enabled)
);

CREATE TABLE IF NOT EXISTS vehicle_regulatory_bindings (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id BIGINT NOT NULL,
  platform_id BIGINT NOT NULL,
  regulatory_vehicle_no VARCHAR(8) NOT NULL,
  certificate_id BIGINT,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  reporting_strategy VARCHAR(32) NOT NULL DEFAULT 'strict',
  config JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_vrb_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  CONSTRAINT fk_vrb_platform FOREIGN KEY (platform_id) REFERENCES regulatory_platforms(id),
  CONSTRAINT fk_vrb_certificate FOREIGN KEY (certificate_id) REFERENCES vehicle_certificates(id),
  UNIQUE KEY uk_platform_vehicle_no (platform_id, regulatory_vehicle_no),
  INDEX idx_vrb_vehicle (vehicle_id),
  INDEX idx_vrb_enabled (is_enabled)
);

CREATE TABLE IF NOT EXISTS vehicle_latest_states (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id BIGINT NOT NULL UNIQUE,
  source_vendor_id BIGINT,
  source_timestamp DATETIME,
  received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  longitude DOUBLE,
  latitude DOUBLE,
  altitude DOUBLE,
  coordinate_system VARCHAR(16) NOT NULL DEFAULT 'GCJ02',
  speed_mps DOUBLE,
  heading_deg DOUBLE,
  battery_soc DOUBLE,
  drive_mode VARCHAR(64),
  gear VARCHAR(32),
  fault_level VARCHAR(32),
  quality JSON NOT NULL,
  payload JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_state_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  CONSTRAINT fk_state_vendor FOREIGN KEY (source_vendor_id) REFERENCES vendor_accounts(id),
  INDEX idx_state_received (received_at)
);

CREATE TABLE IF NOT EXISTS vehicle_raw_messages (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  vendor_id BIGINT,
  vehicle_id BIGINT,
  message_type VARCHAR(64) NOT NULL,
  source_topic VARCHAR(255),
  source_timestamp DATETIME,
  payload JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_raw_vendor FOREIGN KEY (vendor_id) REFERENCES vendor_accounts(id),
  CONSTRAINT fk_raw_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  INDEX idx_raw_vehicle_time (vehicle_id, created_at),
  INDEX idx_raw_vendor_time (vendor_id, created_at)
);

CREATE TABLE IF NOT EXISTS vehicle_normalized_messages (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  raw_message_id BIGINT,
  vehicle_id BIGINT NOT NULL,
  message_type VARCHAR(64) NOT NULL,
  payload JSON NOT NULL,
  quality JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_norm_raw FOREIGN KEY (raw_message_id) REFERENCES vehicle_raw_messages(id),
  CONSTRAINT fk_norm_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  INDEX idx_norm_vehicle_time (vehicle_id, created_at)
);

CREATE TABLE IF NOT EXISTS regulatory_report_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  platform_id BIGINT NOT NULL,
  vehicle_id BIGINT NOT NULL,
  binding_id BIGINT,
  message_type VARCHAR(32) NOT NULL,
  message_no BIGINT,
  status VARCHAR(32) NOT NULL,
  error_message TEXT,
  payload_hex MEDIUMTEXT,
  sent_at DATETIME,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_report_platform FOREIGN KEY (platform_id) REFERENCES regulatory_platforms(id),
  CONSTRAINT fk_report_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  CONSTRAINT fk_report_binding FOREIGN KEY (binding_id) REFERENCES vehicle_regulatory_bindings(id),
  INDEX idx_report_vehicle_time (vehicle_id, created_at),
  INDEX idx_report_platform_time (platform_id, created_at)
);

CREATE TABLE IF NOT EXISTS connection_status (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  kind VARCHAR(32) NOT NULL,
  ref_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  last_seen_at DATETIME,
  last_error TEXT,
  metrics JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_connection_ref (kind, ref_id)
);

CREATE TABLE IF NOT EXISTS field_mapping_rules (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_type VARCHAR(64) NOT NULL,
  target_type VARCHAR(64) NOT NULL,
  source_field VARCHAR(128) NOT NULL,
  target_field VARCHAR(128) NOT NULL,
  transform VARCHAR(128),
  default_value VARCHAR(255),
  is_required BOOLEAN NOT NULL DEFAULT FALSE,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_field_mapping (source_type, target_type)
);

CREATE TABLE IF NOT EXISTS enum_mapping_rules (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_type VARCHAR(64) NOT NULL,
  target_type VARCHAR(64) NOT NULL,
  field_name VARCHAR(128) NOT NULL,
  source_value VARCHAR(128) NOT NULL,
  target_value VARCHAR(128) NOT NULL,
  description VARCHAR(255),
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_enum_mapping (source_type, target_type, field_name, source_value)
);

CREATE TABLE IF NOT EXISTS alert_events (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  severity VARCHAR(32) NOT NULL,
  source VARCHAR(64) NOT NULL,
  ref_id BIGINT,
  title VARCHAR(128) NOT NULL,
  message TEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'open',
  resolved_at DATETIME,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_alert_status (status),
  INDEX idx_alert_source (source)
);

CREATE TABLE IF NOT EXISTS operation_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  actor VARCHAR(64),
  action VARCHAR(128) NOT NULL,
  target_type VARCHAR(64),
  target_id BIGINT,
  detail JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_operation_target (target_type, target_id),
  INDEX idx_operation_actor (actor)
);

INSERT INTO regulatory_platforms
  (name, city_code, platform_type, host, port, coordinate_system, report_frequency_hz, fault_frequency_hz, config, is_enabled)
VALUES
  ('成都市智能网联汽车监管平台', '510100', 'chengdu', '171.221.218.40', 38090, 'WGS84', 10, 1, JSON_OBJECT(), TRUE)
ON DUPLICATE KEY UPDATE name = VALUES(name);

