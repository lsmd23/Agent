# Subtask 09: Synthesis Protocol

## 目标

规定如何把各 subagent 的研究产物合并成主研究报告、实验计划和后续实现路线图。

## 子任务分类

主要属于：

- synthesis
- research management
- report writing
- decision making

## 输入

来自各 subagent 的交付物：

- literature table
- formal spec
- router/gate design
- memory design
- textual backprop design
- runtime prototype report
- benchmark spec
- baseline and ablation plan

## 合并流程

### Step 1: Normalize Terminology

统一术语：

- module
- agent
- tool
- skill
- memory
- route
- gate
- verifier
- reflection
- textual gradient
- trajectory

如果不同 subagent 使用冲突定义，必须保留冲突并给出主定义。

### Step 2: Build Architecture Map

输出一张结构说明：

```text
Task
  -> Encoder
  -> Router/Gates
  -> Module Pool
  -> Memory KV-cache
  -> Aggregator
  -> Verifier
  -> Halt
  -> Reflection/Textual Backprop
```

### Step 3: Identify Claims

把所有主张分为：

- 已有文献支持。
- 原型可验证。
- 需要实验验证。
- 暂时只是猜想。

### Step 4: Resolve Interfaces

检查 schema 是否能互相连接：

- state schema
- module schema
- memory schema
- route decision schema
- trajectory schema
- failure attribution schema
- metrics schema

### Step 5: Produce Research Roadmap

分为：

- week 1: toy runtime and deterministic tasks
- week 2: memory and verifier ablations
- week 3: code/search benchmark
- week 4: textual backprop replay
- week 5+: learned routing

## 主报告结构

建议最终报告结构：

1. Motivation
2. Related Work
3. Formal Model
4. Agent-Attention Runtime
5. Router and Gates
6. Memory KV-cache
7. Textual Backpropagation
8. Experimental Setup
9. Baselines and Ablations
10. Results
11. Failure Analysis
12. Limitations
13. Next Steps

## 决策记录模板

```markdown
## Decision

Chosen: ...

Alternatives:
- ...
- ...

Reason:
...

Risk:
...

Rollback:
...
```

## 交付物

- `master_research_outline.md`
- `architecture_map.md`
- `interface_alignment.md`
- `claim_evidence_matrix.md`
- `roadmap.md`
- `decision_log.md`

## 成功标准

- 能把各 subtask 结果合成一套连贯架构。
- 明确哪些结论已经有证据，哪些只是实验假设。
- 所有模块之间的数据接口一致。
- 下一阶段实验可以直接启动。

## 常见失败

- 把 subagent 输出简单拼接，没有冲突消解。
- 把 speculative claim 写成结论。
- 忽略失败案例，只保留正面叙事。
- 没有把文献、原型、实验指标连接起来。
