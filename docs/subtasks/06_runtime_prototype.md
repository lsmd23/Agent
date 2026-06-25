# Subtask 06: Runtime Prototype

## 目标

基于形式化 spec 实现最小可运行的 Agent-Attention Runtime，用于记录和比较 routing、memory、gating、verification、halt 和 reflection 的行为。

## 子任务分类

主要属于：

- engineering prototype
- instrumentation
- experimental harness

## 最小功能

Runtime 必须支持：

- task input
- state initialization
- module registry
- router
- memory retrieval
- module activation
- aggregator/state updater
- verifier gate
- halt gate
- budget gate
- trajectory logging
- reflection/memory write

## 推荐目录

```text
src/
  runtime/
    state.py
    modules.py
    router.py
    gates.py
    memory.py
    verifier.py
    trajectory.py
    runner.py
experiments/
  tasks/
  trajectories/
tests/
```

当前已有简化起点：

- `src/agent_attention_runtime.py`
- `tests/test_runtime.py`

## Runtime Loop

```text
for step in max_steps:
  query = encode(state)
  memories = memory.retrieve(query)
  route = router.select(state, modules, memories)
  outputs = execute(route)
  state = aggregator.update(state, outputs)
  verification = verifier.maybe_check(state)
  halt = halt_gate(state, verification, budget)
  log(event)
  if halt: break
reflection = reflect(state, trajectory)
memory.maybe_write(reflection)
```

## Trajectory Event Schema

每个事件至少包含：

```json
{
  "event_id": 1,
  "step": 1,
  "kind": "route|execute|memory|verify|halt|reflection",
  "payload": {},
  "timestamp": 0.0
}
```

## 测试要求

单元测试：

- code task 应路由到 code agent。
- research task 应路由到 search/critic。
- 不相关 memory 不应污染 query。
- budget gate 应阻止超预算 activation。
- halt gate 应给出 reason。
- trajectory 应包含 route、execute、halt、reflection。

## 实验要求

先支持 deterministic toy modules，再接入真实工具：

1. deterministic module
2. local shell/python tool
3. web/search tool
4. LLM-backed subagent
5. verifier with tests or citations

## 交付物

- 可运行 runtime。
- CLI runner。
- trajectory JSON 输出。
- 单元测试。
- demo tasks。
- `README` 使用说明。

## 成功标准

- 新任务可以一条命令跑完。
- 所有决策都可在 trajectory 中复盘。
- 可以开关 memory、verifier、router strategy。
- 能导出 metrics 所需字段。

## 常见失败

- 实现一个复杂 agent，但没有日志。
- 工具调用成功了，但无法解释为什么被调用。
- 没有 deterministic toy 模式，导致实验不可复现。
- 状态更新太随意，无法比较不同策略。
