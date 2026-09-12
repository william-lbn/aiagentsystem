import os
if not os.getenv('OPENAI_API_KEY'): raise SystemExit('SKIP: set OPENAI_API_KEY')
try:
    from agents import Agent, Runner, function_tool
except ImportError: raise SystemExit("SKIP: pip install -e '.[openai]'")
@function_tool
def add(a:int,b:int)->int: return a+b
agent=Agent(name='math',instructions='Use tools for arithmetic.',tools=[add])
print(Runner.run_sync(agent,'What is 23+19?').final_output)
