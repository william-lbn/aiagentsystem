try:
    from langgraph.graph import StateGraph, START, END
except ImportError: raise SystemExit('SKIP: pip install langgraph')
from typing_extensions import TypedDict
class S(TypedDict): n:int
def inc(s:S): return {'n':s['n']+1}
g=StateGraph(S); g.add_node('inc',inc); g.add_edge(START,'inc'); g.add_edge('inc',END)
print(g.compile().invoke({'n':41}))
