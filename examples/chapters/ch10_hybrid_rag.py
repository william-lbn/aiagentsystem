from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario


def main() -> int:
    p = argparse.ArgumentParser(description="Hybrid / Agentic RAG：让检索成为决策过程")
    p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
    args = p.parse_args()
    result = run_scenario("hybrid-rag", fault=args.fault)
    print(result.as_json())
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
