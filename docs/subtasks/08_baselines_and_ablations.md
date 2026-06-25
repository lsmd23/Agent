# Subtask 08: Baselines And Ablations

## 目标

设计严谨的 baseline 和 ablation，判断 Agent-Attention Runtime 是否真的比固定 workflow 更高效、更稳定、更可迁移。

## 子任务分类

主要属于：

- experimental design
- baseline implementation
- ablation study

## 必须比较的 Baselines

### Single ReAct Agent

单 agent 执行 think-act-observe loop。

用于回答：动态 routing 是否优于强单体 agent？

### Fixed Workflow Agent

固定流程：

```text
Planner -> Executor -> Critic -> Summarizer
```

用于回答：动态 routing 是否优于人工 workflow？

### Full-History Agent

把完整轨迹塞回 context。

用于回答：结构化 state 和压缩是否优于简单堆上下文？

### Retrieval-Memory Agent

单 agent 加 memory retrieval。

用于回答：收益来自 memory，还是来自 module routing？

### MoA-Style Agent

多 agent 分层生成和聚合。

用于回答：sparse routing 是否比固定多 agent aggregation 更省成本？

### Proposed Agent-Attention Agent

动态路由 agent/tool/memory/skill/verifier。

用于回答：可路由、可激活、可持续优化的 architecture 是否有效。

## 核心 Ablations

- no memory
- no verifier
- verifier always on
- no halt gate
- no budget gate
- no repetition penalty
- no risk penalty
- no cost penalty
- no textual backprop
- memory read only
- memory write only after success
- top-1 vs top-2 vs adaptive top-k
- rule router vs lexical router vs embedding router vs learned router

## 结果表模板

```markdown
| System | Success | Cost | Latency | Module Calls | Repeated Ratio | Premature Halt | Verifier Catch | Memory Reuse | Negative Transfer |
| ------ | ------- | ---- | ------- | ------------ | -------------- | -------------- | -------------- | ------------ | ----------------- |
```

## 统计建议

- 每个 task family 至少 20 个任务。
- 报告均值和置信区间。
- 按任务类型分别报告，不只报告总体平均。
- 对失败样本做 qualitative error analysis。
- 报告 cost-adjusted success，而不是裸成功率。

## Error Analysis 分类

失败原因至少分为：

- bad route
- bad memory
- bad module output
- bad aggregation
- verifier miss
- verifier false alarm
- premature halt
- budget exhausted
- loop stuck
- external tool failure

## 交付物

- `baseline_specs.md`
- `ablation_matrix.md`
- `result_table_template.md`
- `error_taxonomy.md`
- 可选：baseline runner

## 成功标准

- 每个 baseline 都公平使用相同任务和预算。
- 每个 ablation 只改变一个变量。
- 报告不只展示 proposed win，也展示 proposed 失败的场景。
- 能明确判断收益来自 routing、memory、verifier 还是 feedback。

## 常见失败

- baseline 太弱，导致结论没有说服力。
- ablation 同时改多个变量。
- 不控制 token/cost budget。
- 只挑 proposed 成功的任务展示。
