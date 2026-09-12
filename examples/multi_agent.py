import asyncio
from agentlab.workflow import run_parallel


async def researcher():
    await asyncio.sleep(0.01)
    return {"facts": ["MCP", "A2A"]}


async def critic():
    await asyncio.sleep(0.01)
    return {"risks": ["prompt injection", "cost"]}


print(asyncio.run(run_parallel([researcher, critic])))
