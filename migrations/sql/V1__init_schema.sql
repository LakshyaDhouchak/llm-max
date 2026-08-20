-- V1__init_schema.sql
-- Initial schema for MySqlStore, matching the Storage interface contract
-- (the same one SqliteStore implements). Deliberately minimal — scoped to
-- what MySqlStore actually needs today, not the full aspirational schema
-- from docs/ARCHITECTURE.md section 3 (hardware_profiles, benchmark_runs,
-- autopilot_events land in later migrations once Phase 3 needs them).

CREATE TABLE run_records (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_id            VARCHAR(255)    NOT NULL,
    runtime             VARCHAR(64)     NOT NULL DEFAULT 'ollama',
    prompt              TEXT            NOT NULL,
    tokens_generated    INT             NOT NULL,
    total_duration_s    DECIMAL(10, 3)  NOT NULL,
    tokens_per_sec      DECIMAL(10, 2)  NULL,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_run_records_model_id (model_id),
    INDEX idx_run_records_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tuned_configs (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_id            VARCHAR(255)    NOT NULL,
    runtime             VARCHAR(64)     NOT NULL DEFAULT 'ollama',
    config_json         JSON            NOT NULL,
    is_locked           BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_tuned_configs_model_id (model_id),
    INDEX idx_tuned_configs_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;