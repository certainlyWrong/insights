"""Local DuckDB storage and raw-response snapshots."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


def data_dir() -> Path:
    return Path(os.environ.get("INSIGHTS_HOME", ".insights")).expanduser().resolve()


def database_path() -> Path:
    return data_dir() / "insights.duckdb"


def connect() -> duckdb.DuckDBPyConnection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(path))
    connection.execute(
        """CREATE TABLE IF NOT EXISTS records (
            dataset_id VARCHAR NOT NULL,
            record_hash VARCHAR NOT NULL,
            payload JSON NOT NULL,
            source_url VARCHAR NOT NULL,
            first_seen_at VARCHAR NOT NULL,
            last_seen_at VARCHAR NOT NULL,
            PRIMARY KEY (dataset_id, record_hash)
        )"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS fetch_runs (
            run_id VARCHAR PRIMARY KEY,
            dataset_id VARCHAR NOT NULL,
            started_at VARCHAR NOT NULL,
            finished_at VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            record_count BIGINT NOT NULL,
            page_count BIGINT NOT NULL,
            source_url VARCHAR NOT NULL,
            raw_path VARCHAR,
            period_start VARCHAR,
            period_end VARCHAR,
            query_params JSON,
            source_version VARCHAR,
            error VARCHAR
        )"""
    )
    connection.execute("ALTER TABLE fetch_runs ADD COLUMN IF NOT EXISTS query_params JSON")
    connection.execute("ALTER TABLE fetch_runs ADD COLUMN IF NOT EXISTS source_version VARCHAR")
    return connection


def persist_run(
    dataset_id: str,
    source_url: str,
    records: list[dict[str, Any]],
    pages: int,
    started_at: datetime,
    period_start: str | None = None,
    period_end: str | None = None,
    raw_payload: Any | None = None,
    query_params: dict[str, Any] | None = None,
    source_version: str | None = None,
) -> tuple[str, Path, int]:
    finished_at = datetime.now(timezone.utc)
    run_id = finished_at.strftime("%Y%m%dT%H%M%S%fZ")
    raw_dir = data_dir() / "raw" / dataset_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / f"{run_id}.json"
    raw_file.write_text(
        json.dumps(records if raw_payload is None else raw_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    connection = connect()
    try:
        for record in records:
            canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            record_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            connection.execute(
                """INSERT INTO records
                   (dataset_id, record_hash, payload, source_url, first_seen_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT (dataset_id, record_hash) DO UPDATE SET
                     last_seen_at = excluded.last_seen_at,
                     source_url = excluded.source_url""",
                [dataset_id, record_hash, canonical, source_url, started_at.isoformat(), finished_at.isoformat()],
            )
        connection.execute(
            """INSERT INTO fetch_runs
               (run_id, dataset_id, started_at, finished_at, status, record_count, page_count,
                source_url, raw_path, period_start, period_end, query_params, source_version, error)
               VALUES (?, ?, ?, ?, 'success', ?, ?, ?, ?, ?, ?, CAST(? AS JSON), ?, NULL)""",
            [run_id, dataset_id, started_at.isoformat(), finished_at.isoformat(), len(records), pages, source_url,
             str(raw_file), period_start, period_end, json.dumps(query_params or {}, ensure_ascii=False),
             source_version],
        )
    finally:
        connection.close()
    return run_id, raw_file, len(records)


def persist_failure(
    dataset_id: str,
    source_url: str,
    started_at: datetime,
    error: str,
    pages: int = 0,
    query_params: dict[str, Any] | None = None,
    source_version: str | None = None,
) -> None:
    finished_at = datetime.now(timezone.utc)
    run_id = finished_at.strftime("%Y%m%dT%H%M%S%fZ")
    connection = connect()
    try:
        connection.execute(
            """INSERT INTO fetch_runs
               (run_id, dataset_id, started_at, finished_at, status, record_count, page_count,
                source_url, raw_path, period_start, period_end, query_params, source_version, error)
               VALUES (?, ?, ?, ?, 'failed', 0, ?, ?, NULL, NULL, NULL, CAST(? AS JSON), ?, ?)""",
            [run_id, dataset_id, started_at.isoformat(), finished_at.isoformat(), pages, source_url,
             json.dumps(query_params or {}, ensure_ascii=False), source_version, error[:2000]],
        )
    finally:
        connection.close()


def latest_runs() -> list[tuple[Any, ...]]:
    connection = connect()
    try:
        return connection.execute(
            """SELECT dataset_id, finished_at, status, record_count, page_count,
                      raw_path, period_start, period_end, query_params, source_version, error
               FROM fetch_runs
               QUALIFY row_number() OVER (PARTITION BY dataset_id ORDER BY finished_at DESC) = 1
               ORDER BY dataset_id"""
        ).fetchall()
    finally:
        connection.close()
