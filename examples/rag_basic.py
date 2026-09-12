from agentlab.retrieval import HybridRetriever

docs = [
    {"id": "d1", "text": "MCP exposes tools resources and prompts to LLM applications", "freshness": 0.9},
    {"id": "d2", "text": "A2A coordinates stateful tasks between remote agents", "freshness": 0.9},
    {"id": "d3", "text": "RAG retrieves external knowledge before generation", "freshness": 0.7},
]
r = HybridRetriever(docs)
print(r.search("MCP tools resources", k=2))
