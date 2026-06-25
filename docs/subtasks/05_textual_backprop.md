# Subtask 05: Textual Backpropagation

## 目标

设计任务失败后的局部归因与 textual update 机制，让系统能够把失败反馈转化为可审计的 prompt、memory、skill、router rule、verifier checklist 或 halt threshold 更新。

## 子任务分类

主要属于：

- textual backpropagation
- reflection
- failure attribution
- continual improvement

## 基本流程

```text
final failure
  -> identify failed component
  -> inspect evidence from trajectory
  -> generate local textual gradient
  -> propose bounded update
  -> verify update on replay or held-out task
  -> accept, reject, or quarantine update
```

## 失败归因对象

至少支持：

- `router`: 选错模块、重复模块、忽略成本。
- `memory`: 检索错误、写入错误、陈旧记忆、负迁移。
- `module`: agent 输出错误、工具参数错误、schema 不匹配。
- `aggregator`: 错误合并、丢失关键证据、过度压缩。
- `verifier`: 漏检、误报、检查项不完整。
- `halt`: 过早停止、迟迟不停止、预算耗尽。

## Textual Gradient Schema

```json
{
  "failure_id": "...",
  "symptom": "...",
  "root_cause_hypothesis": "...",
  "blamed_component": "router|memory|module|aggregator|verifier|halt",
  "evidence_event_ids": [1, 2, 3],
  "local_gradient": "...",
  "proposed_update": {
    "target": "...",
    "before": "...",
    "after": "..."
  },
  "expected_effect": "...",
  "rollback_condition": "..."
}
```

## 更新目标

允许更新：

- router scoring rule
- intent keyword
- memory usefulness score
- memory blacklist
- module prompt
- verifier checklist
- tool schema description
- halt threshold
- budget policy

禁止或谨慎更新：

- 大范围重写所有 prompt。
- 用单个失败覆盖全局策略。
- 未经 replay 验证就提升 memory 权重。
- 把 verifier 结论当作绝对真相。

## 实验设计

### 实验 A: Failure Replay

对失败 trajectory 生成 textual gradient，然后 replay：

- before update success
- after update success
- cost change
- repeated action ratio change
- new failure introduced

### 实验 B: Local vs Global Update

比较：

- no update
- local router update
- local memory update
- local verifier update
- global prompt rewrite

预期：局部更新更可控，全局更新可能短期提升但更容易引入副作用。

## 指标

- attribution accuracy
- update acceptance rate
- replay improvement
- regression rate
- repeated failure reduction
- rollback frequency
- false blame rate

## 交付物

- `failure_attribution_schema.json`
- `textual_gradient_policy.md`
- `update_acceptance_rules.md`
- `failure_replay_protocol.md`
- 可选：`reflection_engine.py` 原型

## 成功标准

- 每个 update 都能追溯到 trajectory evidence。
- 能区分 symptom 和 root cause hypothesis。
- 有 rollback 或 quarantine 机制。
- 能说明 textual backprop 和普通总结的区别。

## 常见失败

- 反思只写“下次更小心”，没有可执行更新。
- 归因总是怪最后一个模块。
- 没有 replay，导致更新是否有效不可知。
- 单个失败导致 router 过拟合。
