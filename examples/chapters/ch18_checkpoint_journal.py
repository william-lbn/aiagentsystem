from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario


def main() -> int:
    p = argparse.ArgumentParser(description="Checkpoint、Journal 与可恢复执行")
    p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
    args = p.parse_args()
    result = run_scenario("checkpoint", fault=args.fault)
    print(result.as_json())
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
