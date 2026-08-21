-- V5__autopilot_audit_trail.sql
-- Audit trail for autotune decisions (adjust/rollback/lock events).
-- Matches SqliteStore's autopilot_events table.

CREATE TABLE autopilot_events (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_id            VARCHAR(255)    NOT NULL,
    event_type          VARCHAR(32)     NOT NULL,
    details_json        JSON            NOT NULL,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_autopilot_events_model_id (model_id),
    INDEX idx_autopilot_events_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;