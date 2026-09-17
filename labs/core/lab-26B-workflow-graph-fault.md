# Lab 26B — Graph Topology 漂移阻断｜故障注入

## 实验目标

用改变节点序列后的 graph 实例恢复旧 run，验证 topology signature mismatch 在任何 `apply` effect 前被拒绝。

## 环境与版本

与 Lab 26A 相同。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch26_workflow_graph.py --fault
```

实际输出：

```json
{"process_boundary":"close_reopen_sqlite","history":["collect","approve"],"final_node":null,"effect_count":0,"error":"graph_signature_mismatch","evidence_level":"L3_CONTAINED","passed":true}
```

## 调试断点

在 `DurableGraph.resume` 的 persisted/current signature compare 停下；确认异常发生后 effects 表仍为空。

## 验收标准

退出码 0、拓扑错误被系统检测、`effect_count=0`、`contained=true`。实验未执行 graph migration，也不证明分布式 checkpoint durability。
