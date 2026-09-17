from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario


def main() -> int:
    p = argparse.ArgumentParser(description="Planning 与 Hybrid Control：从候选步骤到可执行计划")
    p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
    args = p.parse_args()
    result = run_scenario("planning", fault=args.fault)
    print(result.as_json())
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
