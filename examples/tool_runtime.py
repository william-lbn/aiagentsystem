from agentlab import ToolRegistry, tool


@tool("Safe read", risk="low")
def read_record(record_id: int) -> dict:
    return {"id": record_id, "status": "open"}


@tool("Dangerous delete", risk="high", idempotent=False)
def delete_record(record_id: int) -> dict:
    return {"deleted": record_id}


r = ToolRegistry()
r.register(read_record)
r.register(delete_record)
print(r.schema())
print(r.execute("read_record", {"record_id": 42}))
print(r.execute("missing", {}))
