trajectory = [
    {"role": "user", "content": "find bug"},
    {"role": "assistant", "tool": "read", "args": {"path": "a.py"}},
    {"role": "tool", "value": "return a-b"},
    {"role": "assistant", "content": "patch add"},
]
sft = {"messages": trajectory, "label": "successful_trajectory"}
preference = {"chosen": "read->test->patch->test", "rejected": "blind patch", "reason": "verifiable workflow"}
print(sft)
print(preference)
