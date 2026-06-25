# Subtask 02: Formal Model

## 目标

把“Agent-Transformer-like Architecture”从类比变成可实现的形式化模型，明确 state、module、query/key/value、router、gate、memory、aggregator、verifier、halt 的定义。

## 子任务分类

主要属于：

- formalization
- architecture design
- interface design

## 核心假设

Agent runtime 可以表示为显式循环计算：

```text
state_t = Update(state_{t-1}, observation_t, action_{t-1}, memory)
route_t = Router(Query(state_t), ModulePool, Memory)
outputs_t = Execute(route_t)
state_{t+1} = Aggregate(state_t, outputs_t)
halt_t = HaltGate(state_{t+1})
```

## 必须定义的对象

### State

至少包含：

- `goal`: 原始目标，作为 residual anchor。
- `task_state`: 当前任务分解与进度。
- `working_memory`: 短期上下文。
- `observations`: 工具、agent、memory 返回。
- `beliefs`: 当前被接受的事实或假设。
- `uncertainties`: 未解决问题。
- `failure_signals`: 错误、冲突、测试失败、验证失败。
- `budget`: token、时间、工具调用、费用。
- `route_history`: 已激活模块与分数。
- `verification_status`: 是否已验证、验证结果。

### Module

每个计算单元定义为：

```json
{
  "id": "...",
  "kind": "agent|tool|memory|skill|verifier|aggregator",
  "capability": "...",
  "input_schema": {},
  "output_schema": {},
  "cost": 0.0,
  "latency": 0.0,
  "risk": 0.0,
  "reliability": 0.0,
  "history_features": {}
}
```

### Query / Key / Value

- `Query`: 当前任务需求、状态、失败信号、预算和证据需求。
- `Key`: 模块能力、schema、历史成功率、成本、风险、适用任务。
- `Value`: 模块执行结果、memory 内容、skill、verifier 判断。

## 路由函数

先定义可解释版本：

```text
score_i =
  semantic_match(Q, K_i)
  + alpha * reliability_i
  + beta * past_success_i
  - gamma * cost_i
  - delta * latency_i
  - eta * risk_i
  - rho * repetition_i
  + bonus_i(state)
```

再定义可学习版本：

```text
pi(module_i | state_t) = learned_router(features(state_t, module_i))
reward = success - cost - latency - invalid_calls - repeated_actions
```

## 输出格式

输出一份形式化 spec：

- symbol table
- state schema
- module schema
- route decision schema
- memory entry schema
- trajectory event schema
- update equations
- halt conditions
- invariants

## 推荐 invariants

- 原始 goal 不可被覆盖，只能被引用和分解。
- 每个 state update 必须记录 evidence source。
- 每个 halt 必须给出 reason。
- 每次 memory write 必须说明成功/失败/不确定。
- 每个 verifier 结论必须绑定检查项。

## 交付物

- `formal_spec.md`
- `schemas.json`
- `routing_equations.md`
- `state_invariants.md`

## 成功标准

- 另一个 subagent 可以只读 spec 就实现 toy runtime。
- 所有评价指标都能从 state 或 trajectory event 中计算。
- 明确指出哪些部分是类比，哪些部分是实际机制。

## 常见失败

- 数学符号漂亮但无法落到日志字段。
- state 过大，等价于 full-history agent。
- 没有定义 halt，导致 loop-stuck。
- 没有 residual goal，导致计划漂移。
