failures = ["missed citation", "wrong tool", "timeout"]
policy = {"citation_required": False, "tool_budget": 6}
for f in failures:
    if f == "missed citation":
        policy["citation_required"] = True
    if f == "wrong tool":
        policy["tool_budget"] = 5
print({"candidate_policy": policy, "gate": "must pass regression eval before promotion"})
