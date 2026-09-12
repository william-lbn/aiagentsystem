state = "RECEIVED"
for nxt in ["TRIAGED", "EVIDENCE_COLLECTED", "WAITING_APPROVAL", "APPLIED", "VERIFIED"]:
    print(state, "->", nxt)
    state = nxt
