from __future__ import annotations
import sys
from common import course

if len(sys.argv) != 2:
    raise SystemExit("usage: check_release_tag.py <git-tag>")
tag = sys.argv[1]
expected = course()["version"]
if tag != expected:
    raise SystemExit(f"RELEASE_TAG_MISMATCH tag={tag!r} course.toml version={expected!r}")
print("RELEASE_TAG_OK", tag)
