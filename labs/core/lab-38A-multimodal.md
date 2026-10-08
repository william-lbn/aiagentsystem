# Lab 38A — 实时多模态 Agent：事件时间与取消 epoch｜正常路径

## 实验目标

把音频 partial、视觉 frame 与候选工具结果写入同一有序事件流。候选工作在 epoch 0 注册并在用户打断前完成，因此只有一条**本地结果**被接受，且每个 payload 以 digest 留痕。没有调用外部执行器。

## 可证伪假设与不变量

不变量：实时系统中的 effect 只能在它被授权的 cancellation epoch 内提交。网络顺序、模型输出顺序与物理事件时间不能混为一谈。

## 环境与版本

- Python 3.11–3.13；x86_64/arm64；不需要摄像头、麦克风、GPU 或 API key；
- fixture 表示真实 session control-plane，不声称测量音视频模型质量或端到端媒体延迟；
- OpenAI Realtime 或本地 streaming VLM/ASR 可替换感知层，但仍必须服从相同 epoch gate。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
session = RealtimeSession()
session.ingest(100, "audio", "audio.partial", {"text": "move"})
session.ingest(105, "vision", "vision.frame", {"object": "arm", "distance_cm": 5})
epoch = session.begin_effect("move-1", 110, {"distance_cm": 5})
assert session.complete_effect("move-1", epoch, 120, {"moved": True}) == "COMMITTED"
assert len(session.effects) == 1
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch38_multimodal.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"outcome":"COMMITTED","active_epoch":0,"effect_count":1,"events":[{"seq":1,"event_time_ms":100,"modality":"audio","kind":"audio.partial","epoch":0},{"seq":2,"event_time_ms":105,"modality":"vision","kind":"vision.frame","epoch":0},{"seq":3,"event_time_ms":110,"modality":"tool","kind":"effect.started","epoch":0},{"seq":4,"event_time_ms":120,"modality":"tool","kind":"effect.committed","epoch":0}],"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- sequence 与 event-time 的区别；
- effect 注册的 epoch；
- commit 之前的 active epoch 比较；
- raw media 不入日志，只保留最小必要 metadata/digest。

## 验收标准

退出码 0；事件 seq 为 1–4；时间单调；effect started/committed epoch 都为 0；本地 commit count 恰为 1。L1 不代表真实音频、视觉、外部副作用或机器人硬件已经通过测试。

## 反例与进阶注入

- 注入乱序 frame，先放入 reorder buffer，超过 watermark 才 quarantine；
- 测语音 barge-in、WebRTC 断线、工具 timeout 与 session resume；
- 在真实机器人上增加 E-stop 与独立 safety controller，模型不能成为最后一道物理安全边界。
