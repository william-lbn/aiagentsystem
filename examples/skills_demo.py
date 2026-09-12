from pathlib import Path

skills = {"incident": Path("skills/incident.md"), "review": Path("skills/code-review.md")}
query = "线上故障需要定位"
selected = "incident" if "故障" in query else "review"
print({"selected": selected, "path": str(skills[selected])})
