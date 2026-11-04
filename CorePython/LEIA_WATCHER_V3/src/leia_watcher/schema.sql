-- LEIA Watcher schema v1 — SQLite local (executar em conexão com foreign_keys=ON)
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, checksum TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS watched_roots (
  root_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  canonical_path TEXT NOT NULL UNIQUE,
  mode TEXT NOT NULL CHECK(mode IN ('ORGANIZE','TRACK_ONLY')),
  enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
  recursive INTEGER NOT NULL DEFAULT 1 CHECK(recursive IN (0,1)),
  output_path TEXT,
  health TEXT NOT NULL DEFAULT 'NEW',
  ruleset_id TEXT,
  ruleset_version INTEGER NOT NULL DEFAULT 0,
  config_json TEXT NOT NULL,
  last_scan_started_at TEXT,
  last_scan_finished_at TEXT,
  scan_cursor TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rule_sets (
  ruleset_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  root_id TEXT NOT NULL REFERENCES watched_roots(root_id) ON DELETE RESTRICT,
  definition_json TEXT NOT NULL,
  applied_at TEXT NOT NULL,
  PRIMARY KEY(ruleset_id,version)
);
CREATE TABLE IF NOT EXISTS file_entries (
  file_id TEXT PRIMARY KEY,
  root_id TEXT NOT NULL REFERENCES watched_roots(root_id),
  relative_path TEXT NOT NULL,
  canonical_path TEXT NOT NULL,
  identity_key TEXT,
  filename TEXT NOT NULL,
  extension TEXT,
  size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
  created_at_fs TEXT,
  modified_at_fs TEXT,
  seen_at TEXT NOT NULL,
  last_verified_at TEXT,
  status TEXT NOT NULL,
  origin_category TEXT NOT NULL DEFAULT 'UNKNOWN',
  origin_evidence_json TEXT,
  file_attrs_json TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE(root_id,relative_path)
);
CREATE INDEX IF NOT EXISTS ix_files_name ON file_entries(filename COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS ix_files_root_status ON file_entries(root_id,status);
CREATE INDEX IF NOT EXISTS ix_files_root_seen ON file_entries(root_id,seen_at DESC);
CREATE INDEX IF NOT EXISTS ix_files_ext ON file_entries(root_id,extension);
CREATE INDEX IF NOT EXISTS ix_files_identity ON file_entries(identity_key);
CREATE TABLE IF NOT EXISTS operations (
  operation_id TEXT PRIMARY KEY,
  root_id TEXT NOT NULL REFERENCES watched_roots(root_id),
  file_id TEXT REFERENCES file_entries(file_id) ON DELETE SET NULL,
  operation_kind TEXT NOT NULL CHECK(operation_kind IN ('MOVE','UNDO')),
  source_path TEXT NOT NULL,
  destination_path TEXT NOT NULL,
  stage TEXT NOT NULL,
  rule_set_id TEXT,
  rule_set_version INTEGER,
  reason_code TEXT NOT NULL,
  precondition_json TEXT NOT NULL,
  postcondition_json TEXT,
  replaced_backup_path TEXT,
  source_size_bytes INTEGER,
  source_identity TEXT,
  source_mtime_ns INTEGER,
  source_hash_sha256 TEXT,
  undo_of_operation_id TEXT REFERENCES operations(operation_id),
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  error_code TEXT,
  error_detail TEXT
);
CREATE INDEX IF NOT EXISTS ix_operations_root_date ON operations(root_id,created_at DESC);
CREATE INDEX IF NOT EXISTS ix_operations_stage ON operations(stage);
CREATE INDEX IF NOT EXISTS ix_operations_undo ON operations(undo_of_operation_id);
CREATE TABLE IF NOT EXISTS fs_events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  root_id TEXT NOT NULL REFERENCES watched_roots(root_id),
  observed_at TEXT NOT NULL,
  event_type TEXT NOT NULL,
  path TEXT,
  old_path TEXT,
  file_identity TEXT,
  source TEXT NOT NULL CHECK(source IN ('WATCHER','SCAN','RECOVERY')),
  fingerprint TEXT,
  processed INTEGER NOT NULL DEFAULT 0 CHECK(processed IN (0,1)),
  operation_id TEXT REFERENCES operations(operation_id)
);
CREATE INDEX IF NOT EXISTS ix_events_root_id ON fs_events(root_id,event_id);
CREATE INDEX IF NOT EXISTS ix_events_processed ON fs_events(processed);
CREATE TABLE IF NOT EXISTS audit_events (
  audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
  operation_id TEXT REFERENCES operations(operation_id),
  root_id TEXT REFERENCES watched_roots(root_id),
  occurred_at TEXT NOT NULL,
  action TEXT NOT NULL,
  outcome TEXT NOT NULL,
  reason_code TEXT,
  safe_details_json TEXT NOT NULL,
  actor TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_root ON audit_events(root_id,audit_id DESC);
CREATE TABLE IF NOT EXISTS legacy_download_events (
  event_id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  action TEXT NOT NULL,
  status TEXT NOT NULL,
  name TEXT NOT NULL,
  extension TEXT,
  category TEXT,
  original_path TEXT NOT NULL,
  current_path TEXT NOT NULL,
  source_url TEXT,
  referrer_url TEXT,
  source_domain TEXT,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  sha256 TEXT,
  reason TEXT,
  error TEXT,
  undone INTEGER NOT NULL DEFAULT 0,
  metadata_json TEXT,
  imported_at TEXT NOT NULL,
  source_database TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_legacy_download_ts ON legacy_download_events(ts DESC);
CREATE INDEX IF NOT EXISTS ix_legacy_download_category ON legacy_download_events(category);
CREATE TABLE IF NOT EXISTS api_tokens (
  token_id TEXT PRIMARY KEY,
  token_hash TEXT NOT NULL,
  scopes_json TEXT NOT NULL,
  root_allowlist_json TEXT,
  issued_at TEXT NOT NULL,
  expires_at TEXT,
  revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS checkpoints (
  root_id TEXT PRIMARY KEY REFERENCES watched_roots(root_id),
  last_successful_scan_at TEXT,
  scan_generation INTEGER NOT NULL DEFAULT 0,
  needs_rescan INTEGER NOT NULL DEFAULT 1 CHECK(needs_rescan IN (0,1)),
  reason TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_settings (
  setting_key TEXT PRIMARY KEY,
  setting_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
-- A aplicação deve implementar trilha append-only via usuário de escrita controlado,
-- sem API de DELETE/UPDATE de audit_events. DB local não é WORM à prova de administrador.
