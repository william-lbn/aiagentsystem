"""Executable mechanisms for the specialized agents in Part IV.

The implementations deliberately use small, deterministic fixtures, but they
exercise real SQLite durability, loopback HTTP, database authorization,
byte-exact evidence binding, and graph-signature validation.  They do not claim
model quality, browser-renderer fidelity, or external benchmark results.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, Iterable
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import hashlib
import json
import sqlite3


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


class SessionIntegrityError(ValueError):
    """Raised when a session branch or compacted snapshot loses lineage."""


@dataclass(frozen=True, slots=True)
class CompactSnapshot:
    session_id: str
    ancestry: tuple[str, ...]
    facts: tuple[dict[str, Any], ...]
    digest: str


class SessionLedger:
    """SQLite-backed session tree whose compaction preserves typed facts."""

    CRITICAL_KINDS = frozenset({"constraint", "decision", "evidence", "failure", "artifact"})

    def __init__(self, path: Path):
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            create table if not exists sessions(
              session_id text primary key,
              parent_id text references sessions(session_id),
              goal text not null,
              baseline text not null,
              workspace text not null
            );
            create table if not exists facts(
              event_id integer primary key autoincrement,
              session_id text not null references sessions(session_id),
              kind text not null,
              fact_key text not null,
              value_json text not null
            );
            """
        )

    def close(self) -> None:
        self.connection.close()

    def create(self, session_id: str, *, goal: str, baseline: str, workspace: str, parent_id: str | None = None) -> None:
        if parent_id is not None:
            row = self.connection.execute(
                "select 1 from sessions where session_id=?", (parent_id,)
            ).fetchone()
            if row is None:
                raise SessionIntegrityError("parent_session_missing")
        self.connection.execute(
            "insert into sessions values(?,?,?,?,?)",
            (session_id, parent_id, goal, baseline, workspace),
        )
        self.connection.commit()

    def record(self, session_id: str, kind: str, key: str, value: Any) -> int:
        if kind not in self.CRITICAL_KINDS:
            raise SessionIntegrityError(f"unsupported_fact_kind:{kind}")
        cursor = self.connection.execute(
            "insert into facts(session_id,kind,fact_key,value_json) values(?,?,?,?)",
            (session_id, kind, key, _json(value)),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def ancestry(self, session_id: str) -> tuple[str, ...]:
        chain: list[str] = []
        seen: set[str] = set()
        current: str | None = session_id
        while current is not None:
            if current in seen:
                raise SessionIntegrityError("session_cycle")
            seen.add(current)
            row = self.connection.execute(
                "select parent_id from sessions where session_id=?", (current,)
            ).fetchone()
            if row is None:
                raise SessionIntegrityError("session_missing")
            chain.append(current)
            current = row["parent_id"]
        return tuple(reversed(chain))

    def compact(self, session_id: str) -> CompactSnapshot:
        ancestry = self.ancestry(session_id)
        placeholders = ",".join("?" for _ in ancestry)
        rows = self.connection.execute(
            f"select event_id,session_id,kind,fact_key,value_json from facts "
            f"where session_id in ({placeholders}) order by event_id",
            ancestry,
        ).fetchall()
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            item = {
                "event_id": row["event_id"],
                "session_id": row["session_id"],
                "kind": row["kind"],
                "key": row["fact_key"],
                "value": json.loads(row["value_json"]),
            }
            latest[(row["kind"], row["fact_key"])] = item
        facts = tuple(sorted(latest.values(), key=lambda item: item["event_id"]))
        payload = {"session_id": session_id, "ancestry": ancestry, "facts": facts}
        return CompactSnapshot(session_id, ancestry, facts, _digest(payload))


class BoundaryViolation(ValueError):
    """Raised when an event crosses conversation/workspace boundaries."""


class AgentEventStore:
    """Durable event boundary suitable for a remote agent-server core."""

    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            create table if not exists conversations(
              conversation_id text primary key,
              workspace_id text not null
            );
            create table if not exists events(
              conversation_id text not null,
              sequence integer not null,
              workspace_id text not null,
              request_id text not null unique,
              event_type text not null,
              payload_json text not null,
              primary key(conversation_id, sequence)
            );
            """
        )

    def close(self) -> None:
        self.connection.close()

    def create_conversation(self, conversation_id: str, workspace_id: str) -> None:
        self.connection.execute("insert into conversations values(?,?)", (conversation_id, workspace_id))
        self.connection.commit()

    def append(
        self,
        conversation_id: str,
        workspace_id: str,
        request_id: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        expected_sequence: int,
    ) -> int:
        row = self.connection.execute(
            "select workspace_id from conversations where conversation_id=?", (conversation_id,)
        ).fetchone()
        if row is None:
            raise BoundaryViolation("conversation_missing")
        if row["workspace_id"] != workspace_id:
            raise BoundaryViolation("workspace_binding_mismatch")
        next_sequence = int(
            self.connection.execute(
                "select coalesce(max(sequence),0)+1 from events where conversation_id=?",
                (conversation_id,),
            ).fetchone()[0]
        )
        if next_sequence != expected_sequence:
            raise BoundaryViolation("event_sequence_conflict")
        self.connection.execute(
            "insert into events values(?,?,?,?,?,?)",
            (conversation_id, next_sequence, workspace_id, request_id, event_type, _json(payload)),
        )
        self.connection.commit()
        return next_sequence

    def events(self, conversation_id: str) -> tuple[dict[str, Any], ...]:
        rows = self.connection.execute(
            "select * from events where conversation_id=? order by sequence", (conversation_id,)
        ).fetchall()
        return tuple(
            {
                "sequence": row["sequence"],
                "workspace_id": row["workspace_id"],
                "request_id": row["request_id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        )


@dataclass(frozen=True, slots=True)
class BrowserObservation:
    revision: int
    status: str
    targets: tuple[str, ...]


class BrowserActionRejected(ValueError):
    pass


class _TaskPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.revision: int | None = None
        self.status = ""
        self.targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "main" and values.get("data-revision"):
            self.revision = int(values["data-revision"] or "0")
            self.status = values.get("data-status") or ""
        if tag == "button" and values.get("data-action"):
            self.targets.append(values["data-action"] or "")


class LocalBrowserTask:
    """A real loopback HTTP task with observation-bound state changes.

    This exercises network, HTML parsing, target grounding and stale-state
    rejection.  It is intentionally not a JavaScript renderer or a claim of
    WebArena/BrowserGym performance.
    """

    def __init__(self):
        self.status = "WAITING"
        self.revision = 1
        self.effect_count = 0
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format: str, *_args: Any) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
                if self.path != "/task":
                    self.send_error(404)
                    return
                body = (
                    f'<main data-revision="{owner.revision}" data-status="{owner.status}">'
                    '<button data-action="approve">Approve</button></main>'
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
                if self.path != "/action":
                    self.send_error(404)
                    return
                size = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(size))
                if payload.get("revision") != owner.revision:
                    self.send_error(409, "stale_observation")
                    return
                if payload.get("target") != "approve" or owner.status != "WAITING":
                    self.send_error(422, "invalid_action")
                    return
                owner.status = "APPROVED"
                owner.revision += 1
                owner.effect_count += 1
                body = _json({"status": owner.status, "revision": owner.revision}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self) -> LocalBrowserTask:
        self.thread.start()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def observe(self) -> BrowserObservation:
        with urlopen(f"{self.base_url}/task", timeout=2) as response:  # noqa: S310 - fixed loopback URL
            parser = _TaskPageParser()
            parser.feed(response.read().decode())
        if parser.revision is None:
            raise BrowserActionRejected("observation_missing_revision")
        return BrowserObservation(parser.revision, parser.status, tuple(parser.targets))

    def mutate_environment(self, status: str) -> None:
        self.status = status
        self.revision += 1

    def act(self, observation: BrowserObservation, target: str) -> dict[str, Any]:
        if target not in observation.targets:
            raise BrowserActionRejected("target_not_observed")
        request = Request(
            f"{self.base_url}/action",
            data=_json({"target": target, "revision": observation.revision}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=2) as response:  # noqa: S310 - fixed loopback URL
                return json.loads(response.read())
        except HTTPError as exc:
            if exc.code == 409:
                raise BrowserActionRejected("stale_observation") from exc
            raise BrowserActionRejected(f"http_action_rejected:{exc.code}") from exc


class QueryRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    plan: tuple[str, ...]
    truncated: bool
    digest: str


class ReadOnlyDataAgent:
    """SQLite analysis boundary enforced by query-only mode and authorizer."""

    _DENIED = {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_INDEX,
        sqlite3.SQLITE_DROP_TEMP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_TRIGGER,
        sqlite3.SQLITE_DROP_TEMP_VIEW,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
    }

    def __init__(self, path: Path, *, max_rows: int = 100):
        self.connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self.connection.execute("pragma query_only=on")
        self.connection.set_authorizer(self._authorize)
        self.max_rows = max_rows

    @classmethod
    def _authorize(cls, action: int, _arg1: str, _arg2: str, _db: str, _trigger: str) -> int:
        return sqlite3.SQLITE_DENY if action in cls._DENIED else sqlite3.SQLITE_OK

    def close(self) -> None:
        self.connection.close()

    def execute(self, sql: str, parameters: Iterable[Any] = ()) -> QueryResult:
        try:
            plan_rows = self.connection.execute(f"explain query plan {sql}", tuple(parameters)).fetchall()
            cursor = self.connection.execute(sql, tuple(parameters))
        except sqlite3.DatabaseError as exc:
            raise QueryRejected(str(exc)) from exc
        columns = tuple(item[0] for item in cursor.description or ())
        materialized = cursor.fetchmany(self.max_rows + 1)
        truncated = len(materialized) > self.max_rows
        rows = tuple(tuple(row) for row in materialized[: self.max_rows])
        plan = tuple(str(row[3]) for row in plan_rows)
        return QueryResult(columns, rows, plan, truncated, _digest({"columns": columns, "rows": rows}))


class EvidenceViolation(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    source_id: str
    uri: str
    content: str
    sha256: str


@dataclass(frozen=True, slots=True)
class VerifiedClaim:
    claim: str
    source_id: str
    start: int
    end: int
    quote: str
    source_sha256: str


class EvidenceBinder:
    """Binds claims to exact source spans and immutable source digests."""

    def __init__(self):
        self.sources: dict[str, SourceArtifact] = {}

    def ingest_file(self, source_id: str, path: Path) -> SourceArtifact:
        content = path.read_text(encoding="utf-8")
        source = SourceArtifact(source_id, path.resolve().as_uri(), content, hashlib.sha256(content.encode()).hexdigest())
        self.sources[source_id] = source
        return source

    def bind(self, claim: str, source_id: str, start: int, end: int, expected_quote: str) -> VerifiedClaim:
        source = self.sources.get(source_id)
        if source is None:
            raise EvidenceViolation("source_missing")
        if not (0 <= start < end <= len(source.content)):
            raise EvidenceViolation("span_out_of_range")
        quote = source.content[start:end]
        if quote != expected_quote:
            raise EvidenceViolation("quote_mismatch")
        return VerifiedClaim(claim, source_id, start, end, quote, source.sha256)


class GraphRecoveryError(ValueError):
    pass


class DurableGraph:
    """Small SQLite-checkpointed graph with topology identity and effect keys."""

    def __init__(self, path: Path, nodes: tuple[str, ...]):
        if not nodes or nodes[-1] != "verify":
            raise ValueError("graph_must_end_in_verify")
        self.nodes = nodes
        self.signature = _digest(nodes)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            create table if not exists runs(
              run_id text primary key,
              graph_signature text not null,
              node_index integer not null,
              version integer not null,
              state_json text not null
            );
            create table if not exists effects(
              effect_key text primary key,
              run_id text not null,
              payload_json text not null
            );
            """
        )

    def close(self) -> None:
        self.connection.close()

    def start(self, run_id: str, state: dict[str, Any]) -> None:
        self.connection.execute(
            "insert into runs values(?,?,?,?,?)", (run_id, self.signature, 0, 1, _json(state))
        )
        self.connection.commit()

    def resume(self, run_id: str) -> dict[str, Any]:
        row = self.connection.execute("select * from runs where run_id=?", (run_id,)).fetchone()
        if row is None:
            raise GraphRecoveryError("run_missing")
        if row["graph_signature"] != self.signature:
            raise GraphRecoveryError("graph_signature_mismatch")
        return {
            "run_id": run_id,
            "node": self.nodes[row["node_index"]] if row["node_index"] < len(self.nodes) else "FINISHED",
            "node_index": row["node_index"],
            "version": row["version"],
            "state": json.loads(row["state_json"]),
        }

    def step(self, run_id: str, *, expected_version: int) -> dict[str, Any]:
        current = self.resume(run_id)
        if current["version"] != expected_version:
            raise GraphRecoveryError("checkpoint_version_conflict")
        if current["node"] == "FINISHED":
            return current
        node = current["node"]
        state = current["state"]
        history = list(state.get("history", []))
        history.append(node)
        state["history"] = history
        if node == "apply":
            self.connection.execute(
                "insert or ignore into effects values(?,?,?)",
                (f"{run_id}:apply", run_id, _json({"applied": True})),
            )
        cursor = self.connection.execute(
            "update runs set node_index=node_index+1,version=version+1,state_json=? "
            "where run_id=? and version=?",
            (_json(state), run_id, expected_version),
        )
        if cursor.rowcount != 1:
            raise GraphRecoveryError("checkpoint_version_conflict")
        self.connection.commit()
        return self.resume(run_id)

    def effect_count(self, run_id: str) -> int:
        return int(self.connection.execute("select count(*) from effects where run_id=?", (run_id,)).fetchone()[0])
