from __future__ import annotations
import json
import re
from urllib.parse import urlsplit, urlunsplit
from common import ROOT, chapter_paths

URL_RE = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&\'()*+,;=%-]+")
TRIM = ".,;:!?，。；：！？)]}>*"


def norm(url: str) -> str:
    url = url.rstrip(TRIM)
    parts = urlsplit(url)
    # Fragments are navigation, not a distinct evidence source. Query strings are
    # retained because some primary sources use them to identify a document.
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def covered(url: str, locked: set[str]) -> bool:
    u = norm(url)
    for raw in locked:
        locked_url = norm(raw)
        if u == locked_url:
            return True
        # A repository/site root lock covers a stable sub-page on that same
        # source.  Do not reverse this relation: a deep-page lock does not cover
        # an unrelated parent page.
        base = locked_url.rstrip("/")
        if u.startswith(base + "/"):
            return True
    return False


locks = json.loads((ROOT / "integrations/SOURCE_LOCK.json").read_text(encoding="utf-8"))
allow = json.loads((ROOT / "integrations/SOURCE_ALLOWLIST.json").read_text(encoding="utf-8"))
locked = {v["url"] for v in locks.values() if isinstance(v, dict) and isinstance(v.get("url"), str)}
allowed = {norm(u) for u in allow}

files = [*chapter_paths(), *sorted((ROOT / "book/zh/appendices").glob("*.md"))]
refs = []
for p in files:
    text = p.read_text(encoding="utf-8")
    for m in URL_RE.finditer(text):
        u = norm(m.group(0))
        refs.append((p.relative_to(ROOT).as_posix(), u))

unmatched = []
for path, u in sorted(set(refs)):
    if u in allowed:
        continue
    if not covered(u, locked):
        unmatched.append((path, u))

# An allowlist itself is auditable: every entry needs a reason, and .invalid is
# the only fixture hostname currently permitted without a source lock.
allow_errors = []
for u, meta in allow.items():
    if not isinstance(meta, dict) or not str(meta.get("reason", "")).strip():
        allow_errors.append(f"{u}: missing reason")
    if urlsplit(u).hostname and not urlsplit(u).hostname.endswith(".invalid"):
        allow_errors.append(f"{u}: non-.invalid URL must be SOURCE_LOCKed, not allowlisted")

if unmatched or allow_errors:
    print("SOURCE_LOCK_COVERAGE_FAILED")
    for e in allow_errors:
        print("-", e)
    for p, u in unmatched:
        print("-", p, u)
    raise SystemExit(1)
print(
    f"SOURCE_LOCK_COVERAGE_OK refs={len(set(refs))} unique_urls={len({u for _, u in refs})} locks={len(locks)} allowlist={len(allow)}"
)
