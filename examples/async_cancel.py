import asyncio


async def work(name, delay):
    await asyncio.sleep(delay)
    return name


async def main():
    tasks = [asyncio.create_task(work("fast", 0.01)), asyncio.create_task(work("slow", 1))]
    done, pending = await asyncio.wait(tasks, timeout=0.05)
    for p in pending:
        p.cancel()
    print("done", [d.result() for d in done], "cancelled", len(pending))


asyncio.run(main())
