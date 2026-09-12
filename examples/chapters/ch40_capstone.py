from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario


def main() -> int:
    p = argparse.ArgumentParser(description="综合案例：AgentOps 平台的端到端闭环")
    p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
    args = p.parse_args()
    result = run_scenario("capstone", fault=args.fault)
    print(result.as_json())
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
