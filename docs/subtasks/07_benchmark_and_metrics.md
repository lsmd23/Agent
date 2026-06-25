# Subtask 07: Benchmark And Metrics

## 目标

设计能评估 Agent-Attention Runtime 的 benchmark、任务集、日志字段和指标，避免只看最终成功率。

## 子任务分类

主要属于：

- evaluation
- benchmark design
- instrumentation

## 任务类型

### Type A: Code Agent Tasks

任务应包含：

- 小型 repo issue。
- 失败测试。
- 需要定位文件、修改代码、运行验证。
- 有明确 pass/fail。

可用任务：

- toy bug repo
- HumanEval-style repair
- SWE-bench Lite 子集
- 自制 pytest fixtures

### Type B: Search Agent Tasks

任务应包含：

- 需要多源证据。
- 可能存在来源冲突。
- 需要引用或证据链。
- 有可人工判定答案。

### Type C: Mini Research Agent Tasks

任务应包含：

- 文献检索。
- 方法 taxonomy。
- baseline 和 ablation 设计。
- 输出 research memo。

## 指标分层

### Final Metrics

- task success rate
- test pass rate
- answer correctness
- citation correctness
- human preference score

### Process Metrics

- average module calls
- average tool calls
- token cost
- latency
- budget exhaustion rate
- repeated action ratio
- invalid tool call ratio
- loop-stuck rate
- premature stopping rate

### Routing Metrics

- route precision
- oracle route regret
- useful activation rate
- unnecessary activation rate
- top-k diversity
- cost-adjusted reward

### Memory Metrics

- retrieval precision
- useful memory reuse rate
- negative transfer rate
- stale memory rate
- memory write acceptance rate

### Verifier Metrics

- verifier catch rate
- verifier false positive rate
- verifier false negative rate
- verification cost
- post-verification success gain

## 日志字段要求

每个 task run 保存：

- task id
- task family
- runtime config
- router strategy
- memory config
- module registry snapshot
- trajectory events
- final answer
- final success label
- failure reason
- metrics summary

## 对照设计

同一任务必须跑：

- Single ReAct baseline
- Fixed Workflow baseline
- Retrieval-memory baseline
- MoA-style baseline
- Proposed Agent-Attention runtime

## 交付物

- `benchmark_spec.md`
- `task_schema.json`
- `trajectory_schema.json`
- `metrics_definitions.md`
- `scoring_script.py`
- 小型 seed benchmark

## 成功标准

- 每个指标都能从日志中计算。
- 每个任务有明确 success label。
- 能区分“做对了但很贵”和“做错了但很省”。
- 能报告 negative transfer 和 premature halt。

## 常见失败

- 只看最终成功率。
- benchmark 太小，无法体现 routing。
- 人工评分标准不一致。
- 不保存失败原因，导致无法 textual backprop。
