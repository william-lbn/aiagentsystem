def compact(events):
    facts = []
    open_items = []
    for e in events:
        if e.startswith("FACT:"):
            facts.append(e[5:].strip())
        if e.startswith("TODO:"):
            open_items.append(e[5:].strip())
        if e.startswith("DONE:") and e[5:].strip() in open_items:
            open_items.remove(e[5:].strip())
    return {"facts": facts[-4:], "open_items": open_items[-4:]}


events = [
    "FACT: tenant=acme",
    "TODO: inspect logs",
    "FACT: service=payments",
    "DONE: inspect logs",
    "TODO: rollback?",
    "FACT: error=timeout",
]
print(compact(events))
