from agentlab.retrieval import HybridRetriever

docs = [
    {"id": "runbook", "text": "payments timeout runbook retry circuit breaker rollback", "freshness": 1.0},
    {"id": "postmortem", "text": "payments outage caused by connection pool exhaustion", "freshness": 0.8},
    {"id": "faq", "text": "payment service overview owners dashboards", "freshness": 0.6},
]
for hit in HybridRetriever(docs).search("payments timeout rollback", k=3):
    print(hit["id"], hit["score"])
