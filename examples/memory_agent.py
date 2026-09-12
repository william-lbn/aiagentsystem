from agentlab.memory import MemoryStore

m = MemoryStore()
m.add("m1", "用户偏好 Python 并希望所有实验可单步调试", kind="preference")
m.add("m2", "上一次项目选择 SQLite 做本地演示", kind="decision")
print([(x.key, x.text) for x in m.search("调试 Python", k=2)])
