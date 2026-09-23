"""SQLite transactions, revisions and request-bound idempotency."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from .common import DomainError, canonical, digest, now


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as con:
            con.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                    kind TEXT NOT NULL, at TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requests (
                    key TEXT PRIMARY KEY, request_hash TEXT NOT NULL, response TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS decisions (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                    at TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS judgment_cache (
                    key TEXT PRIMARY KEY, task_id TEXT NOT NULL,
                    created_at REAL NOT NULL, expires_at REAL NOT NULL,
                    data TEXT NOT NULL, data_hash TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS cache_expiry ON judgment_cache(expires_at);
                CREATE TABLE IF NOT EXISTS rules (
                    id TEXT PRIMARY KEY, data TEXT NOT NULL);
            ''')
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            yield con
        finally:
            con.close()

    @contextmanager
    def transaction(self):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                yield con
                con.commit()
            except BaseException:
                con.rollback()
                raise

    @staticmethod
    def load(con, task_id: str) -> dict:
        row = con.execute("SELECT data FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise DomainError("TASK_NOT_FOUND", "Unknown task id")
        return json.loads(row["data"])

    def get(self, task_id: str) -> dict:
        with self.connect() as con:
            return self.load(con, task_id)

    def all_tasks(self) -> list[dict]:
        with self.connect() as con:
            return [json.loads(x[0]) for x in con.execute("SELECT data FROM tasks ORDER BY rowid")]

    @staticmethod
    def event(con, task_id: str, kind: str, data: dict):
        con.execute("INSERT INTO events(task_id,kind,at,data) VALUES(?,?,?,?)",
                    (task_id, kind, now(), canonical(data)))

    @staticmethod
    def replay(con, key: str, request: dict):
        if not key or len(key) > 200:
            raise DomainError("INVALID_IDEMPOTENCY_KEY", "Use a nonempty key of at most 200 characters")
        row = con.execute("SELECT request_hash,response FROM requests WHERE key=?", (key,)).fetchone()
        if row:
            if row["request_hash"] != digest(request):
                raise DomainError("IDEMPOTENCY_CONFLICT", "Key was already used for another request")
            return json.loads(row["response"])
        return None

    @staticmethod
    def remember(con, key: str, request: dict, response: dict):
        con.execute("INSERT INTO requests VALUES(?,?,?)", (key, digest(request), canonical(response)))

    def create(self, task: dict, key: str, request: dict) -> dict:
        with self.transaction() as con:
            replay = self.replay(con, key, request)
            if replay is not None:
                return replay
            con.execute("INSERT INTO tasks VALUES(?,?,?)", (task["id"], task["revision"], canonical(task)))
            self.event(con, task["id"], "task_created", {"request": task["request"]})
            result = {"task_id": task["id"], "revision": task["revision"], "state": task["state"]}
            self.remember(con, key, request, result)
            return result

    def mutate(self, task_id: str, revision: int, key: str, operation: str,
               payload: dict, action: Callable) -> dict:
        request = {"task_id": task_id, "revision": revision, "operation": operation, "payload": payload}
        with self.transaction() as con:
            replay = self.replay(con, key, request)
            if replay is not None:
                return replay
            task = self.load(con, task_id)
            if task["revision"] != revision:
                raise DomainError("REVISION_CONFLICT", "Read the current revision before retrying", retryable=True)
            result = action(task, con) or {}
            task["revision"] += 1
            task["updated_at"] = now()
            con.execute("UPDATE tasks SET revision=?,data=? WHERE id=?",
                        (task["revision"], canonical(task), task_id))
            self.event(con, task_id, operation, result)
            response = {"task_id": task_id, "revision": task["revision"], "state": task["state"], **result}
            self.remember(con, key, request, response)
            return response

    def events(self, task_id: str) -> list[dict]:
        with self.connect() as con:
            return [dict(row) | {"data": json.loads(row["data"])} for row in con.execute(
                "SELECT * FROM events WHERE task_id=? ORDER BY seq", (task_id,))]

    def record_decision(self, task_id: str, result: dict):
        with self.connect() as con:
            con.execute("INSERT INTO decisions(task_id,at,data) VALUES(?,?,?)", (task_id, now(), canonical(result)))

    def decisions(self, task_id: str) -> list[dict]:
        with self.connect() as con:
            return [json.loads(row[0]) for row in con.execute(
                "SELECT data FROM decisions WHERE task_id=? ORDER BY seq", (task_id,))]


    def cached_judgment(self, key: str, task_id: str) -> dict | None:
        """Validated, non-expired advisory result; corrupt entries become misses."""
        with self.transaction() as con:
            con.execute("DELETE FROM judgment_cache WHERE expires_at<=?", (time.time(),))
            row = con.execute("SELECT * FROM judgment_cache WHERE key=? AND task_id=?",
                              (key, task_id)).fetchone()
            if not row:
                return None
            try:
                result = json.loads(row["data"])
                if (not isinstance(result, dict) or digest(result) != row["data_hash"]
                        or result.get("cache_key") != key
                        or result.get("status") != "available"
                        or result.get("is_advisory") is not True
                        or not isinstance(result.get("answers"), dict)):
                    raise ValueError("Invalid cached result")
            except (ValueError, TypeError):
                con.execute("DELETE FROM judgment_cache WHERE key=?", (key,))
                return None
            return result

    def cache_judgment(self, key: str, task_id: str, result: dict,
                      ttl_seconds: int, max_entries: int) -> None:
        if ttl_seconds <= 0 or max_entries <= 0 or result.get("status") != "available":
            return
        clock = time.time()
        with self.transaction() as con:
            con.execute("DELETE FROM judgment_cache WHERE expires_at<=?", (clock,))
            con.execute("INSERT OR REPLACE INTO judgment_cache VALUES(?,?,?,?,?,?)",
                        (key, task_id, clock, clock + ttl_seconds, canonical(result), digest(result)))
            # Bound disk use across all tasks in this workspace; no prompts are stored.
            con.execute("DELETE FROM judgment_cache WHERE key IN "
                        "(SELECT key FROM judgment_cache ORDER BY created_at DESC, key LIMIT -1 OFFSET ?)",
                        (max_entries,))

    def cache_stats(self) -> dict:
        with self.connect() as con:
            row = con.execute("SELECT count(*), coalesce(sum(expires_at>?),0) "
                              "FROM judgment_cache", (time.time(),)).fetchone()
        return {"entries": row[0], "valid_entries": row[1], "expired_entries": row[0] - row[1],
                "scope": "workspace and task", "raw_inputs_stored": False}

    def clear_judgment_cache(self) -> dict:
        with self.transaction() as con:
            count = con.execute("SELECT count(*) FROM judgment_cache").fetchone()[0]
            con.execute("DELETE FROM judgment_cache")
        return {"deleted_entries": count, "decisions_and_evidence_preserved": True}
