# Lab 23A — HTTP 观察—动作—后置状态闭环｜正常路径

## 实验目标

启动真实 loopback HTTP 服务，通过 GET 解析 observation，再以绑定 revision 的 POST 执行动作，验证服务端状态和 effect count。

## 环境与版本

Python 3.11–3.13 标准库 `http.server/urllib/html.parser`；需允许绑定 `127.0.0.1` 临时端口；不访问外网。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch23_browser.py
```

实际输出：

```json
{"transport":"loopback_http","observed_revision":1,"observed_targets":["approve"],"server_revision":2,"server_status":"APPROVED","effect_count":1,"evidence_level":"L1_MECHANISM","passed":true}
```

## 调试断点

停在 `_TaskPageParser.handle_starttag`、`LocalBrowserTask.act` 与 handler `do_POST`；区分目标 grounding、HTTP receipt 和 server postcondition。

## 验收标准

退出码 0；只产生一次 effect；状态从 WAITING 变为 APPROVED。它是真实 HTTP/HTML 实验，但不是 JavaScript 浏览器或 WebArena/OSWorld benchmark。
