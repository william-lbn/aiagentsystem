from __future__ import annotations
import asyncio


async def run_parallel(tasks):
    return await asyncio.gather(*(t() for t in tasks), return_exceptions=True)


async def with_timeout(coro, seconds: float):
    return await asyncio.wait_for(coro, timeout=seconds)
