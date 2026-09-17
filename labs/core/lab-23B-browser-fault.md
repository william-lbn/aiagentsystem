# Lab 23B — 陈旧 Observation 拒绝｜故障注入

## 实验目标

在 GET observation 与 POST action 之间改变环境 revision，验证服务端返回冲突且不执行旧动作。

## 环境与版本

与 Lab 23A 相同；仅监听 loopback 地址。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch23_browser.py --fault
```

实际输出：

```json
{"observed_revision":1,"server_revision":2,"server_status":"CHANGED","error":"stale_observation","effect_count":0,"evidence_level":"L3_CONTAINED","passed":true}
```

## 调试断点

在 `mutate_environment` 和 server revision compare 停下；确认 HTTP 409/`stale_observation` 在 `effect_count += 1` 之前发生。

## 验收标准

退出码 0、`effect_count=0`、`contained=true`。不要把“故障被阻断”写成“浏览器任务已恢复”；恢复需要重新观察和重新决策。
