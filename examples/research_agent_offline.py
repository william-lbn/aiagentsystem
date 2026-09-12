from agentlab.retrieval import HybridRetriever

corpus = [
    {
        "id": "official-mcp",
        "text": "MCP exposes tools resources prompts standardized for LLM applications",
        "freshness": 1,
    },
    {"id": "official-a2a", "text": "A2A uses Agent Cards messages stateful tasks and artifacts", "freshness": 1},
    {"id": "runtime", "text": "Agent runtime owns loop policy state checkpoint trace and execution", "freshness": 0.8},
]
hits = HybridRetriever(corpus).search("protocol for tools and agent tasks", 3)
print("claim: MCP handles tool/resource context; A2A handles agent task collaboration")
print("evidence:", [x["id"] for x in hits])
