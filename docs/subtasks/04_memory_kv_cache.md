# Subtask 04: Memory KV-Cache

## 目标

设计跨任务 Agent KV-cache，使 agent 不只检索知识，还检索行为经验：过去类似任务用了哪些模块、哪些 route 成功、哪些失败模式要避免、哪些 verifier 有效。

## 子任务分类

主要属于：

- memory
- retrieval
- continual learning
- cross-task transfer

## Memory Entry Schema

建议最小格式：

```json
{
  "id": "...",
  "key": {
    "task_family": "...",
    "task_signature": "...",
    "route_signature": "...",
    "tool_schema_signature": "...",
    "failure_signature": "..."
  },
  "value": {
    "workflow": "...",
    "trajectory_summary": "...",
    "reflection": "...",
    "useful_modules": ["..."],
    "avoid_modules": ["..."],
    "verifier_checks": ["..."]
  },
  "metadata": {
    "success": true,
    "usefulness": 0.0,
    "confidence": 0.0,
    "created_at": "...",
    "last_used_at": "...",
    "negative_transfer_count": 0
  }
}
```

## 关键设计问题

1. 什么时候读 memory？
2. 什么时候写 memory？
3. memory key 如何避免过宽或过窄？
4. 如何压缩 trajectory？
5. 如何记录失败经验？
6. 如何遗忘、降权或隔离坏 memory？
7. 如何计算 useful memory reuse？

## 检索策略

建议对比：

- lexical retrieval
- embedding retrieval
- hybrid retrieval
- task-family filtered retrieval
- success-only retrieval
- success + failure retrieval
- verifier-approved retrieval

## 写入策略

只在以下情况写入：

- 任务成功且 route 可复用。
- 任务失败但归因清楚。
- verifier 发现关键错误。
- 某个 memory 导致负迁移，需要记录 avoid pattern。

不要写入：

- 未验证的中间猜测。
- 与任务无关的全文轨迹。
- 无归因的失败抱怨。

## 实验设计

### 实验 A: Memory Transfer

构造重复任务族：

- Python test fix
- citation-heavy research answer
- multi-source search synthesis

比较：

- no memory
- knowledge memory only
- trajectory memory
- trajectory + failure memory

### 实验 B: Negative Transfer

故意加入相似但错误的 memory，测量：

- retrieval precision
- wrong route activation
- verifier catch rate
- final success loss

## 指标

- memory retrieval precision
- useful memory reuse rate
- negative transfer rate
- memory write acceptance rate
- stale memory rate
- cross-task transfer gain
- route improvement after memory

## 交付物

- `memory_schema.json`
- `memory_policy.md`
- `retrieval_ablation.md`
- `negative_transfer_cases.md`
- 可选：`memory_store.py` 原型

## 成功标准

- 能区分知识 memory、trajectory memory、skill memory、failure memory。
- 每次 memory read/write 都可审计。
- 设计中包含遗忘或降权机制。
- 有明确方法测量 memory 是否真的有用。

## 常见失败

- memory 越多越好，这是错的。
- 把完整历史塞进 memory，导致 retrieval 噪声。
- 只保存成功，不保存失败模式。
- memory 一旦写入永不修正。
