from agentlab.eval import EvalCase, EvalHarness


def fn(value: str) -> dict[str, object]:
    return {"answer": value.upper(), "steps": 1}


cases = [
    EvalCase("upper", "agent", lambda o: o["answer"] == "AGENT"),
    EvalCase("budget", "x", lambda o: o["steps"] <= 2),
]
print(EvalHarness().run(fn, cases))
