def pack(messages, max_chars=120):
    kept = []
    used = 0
    for m in reversed(messages):
        n = len(m["content"])
        if used + n > max_chars:
            break
        kept.append(m)
        used += n
    return list(reversed(kept)), used


messages = [{"role": "user", "content": f"turn-{i}: " + ("x" * (i * 8))} for i in range(1, 8)]
kept, used = pack(messages)
print("kept", [m["content"].split(":")[0] for m in kept], "chars", used)
