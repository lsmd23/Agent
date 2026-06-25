# Subtask 03: Router And Gates

## 目标

设计 Agent-Attention Runtime 的 routing 和 gating 机制，回答：何时调用哪个 agent/tool/memory/skill/verifier？如何在效果、成本、延迟、风险之间权衡？

## 子任务分类

主要属于：

- agent-level attention
- sparse activation
- budget-aware routing
- gate design

## 需要设计的组件

### Router

输入：

- `state_t`
- `module_pool`
- `memory_candidates`
- `budget_status`
- `failure_signals`

输出：

```json
{
  "selected_modules": ["..."],
  "scores": [],
  "rationale": "...",
  "expected_cost": 0.0,
  "expected_risk": 0.0
}
```

### Gates

需要分别设计：

- `ToolGate`: 是否需要外部工具。
- `SearchGate`: 是否需要检索网页、论文、文档。
- `MemoryGate`: 是否读取/写入跨任务记忆。
- `VerifierGate`: 是否需要验证。
- `HaltGate`: 是否停止。
- `SafetyGate`: 是否需要人类确认。
- `BudgetGate`: 是否允许继续激活高成本模块。

## 路由策略层级

先实现 4 个层级，方便 ablation：

1. `rule_router`: 基于关键词和任务类型。
2. `lexical_router`: 基于文本相似度和成本惩罚。
3. `embedding_router`: 基于向量相似度和元数据。
4. `learned_router`: 基于历史 trajectory 的监督或 bandit 学习。

## 推荐打分项

- semantic match
- module reliability
- task-family success rate
- current uncertainty
- expected information gain
- cost
- latency
- risk
- repetition penalty
- memory transfer confidence

## 实验设计

### 实验 A: Sparse Activation vs Fixed Workflow

比较：

- always planner -> executor -> critic
- top-1 router
- top-2 router
- adaptive top-k router

指标：

- task success
- average module calls
- repeated action ratio
- latency
- premature halt

### 实验 B: Gate Accuracy

对每个 gate 统计：

- true positive
- false positive
- false negative
- cost saved
- errors introduced

特别关注：

- SearchGate 错误触发会浪费成本。
- HaltGate 过早停止会直接损害成功率。
- VerifierGate 永远开启会拉高成本。

## 交付物

- `router_design.md`
- `gate_design.md`
- `routing_features.md`
- `router_ablation_plan.md`
- 可选：`router.py` 原型

## 成功标准

- 每个 gate 有输入、输出、阈值和失败模式。
- routing score 可解释，并且能记录到 trajectory。
- 至少设计一个成本敏感实验。
- 至少设计一个 negative routing case。

## 常见失败

- router 总是选择最强模型，失去稀疏激活意义。
- gate 没有独立指标，只在最终成功率里被混掉。
- 忽略 repeated action，导致循环调用同一模块。
- memory 内容直接污染 query，造成负迁移。
