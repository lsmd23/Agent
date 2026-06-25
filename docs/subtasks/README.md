# Subagent Research Task Pack

这组文档把 Agent-Transformer-like Architecture 研究拆成若干可并行推进的子任务。每个子任务都面向一个后续 subagent，要求它产出可合并、可验证、可复用的研究材料，而不是泛泛讨论。

## 推荐执行顺序

1. `01_literature_map.md`: 先建立文献地图和概念边界。
2. `02_formal_model.md`: 把类比落到状态、模块、路由、记忆、更新函数。
3. `03_router_and_gates.md`: 设计 agent/tool/memory/router/gate 的具体策略。
4. `04_memory_kv_cache.md`: 设计跨任务行为记忆和检索机制。
5. `05_textual_backprop.md`: 设计失败归因和 textual update 机制。
6. `06_runtime_prototype.md`: 把抽象落到最小可运行 runtime。
7. `07_benchmark_and_metrics.md`: 构建 benchmark、指标和日志 schema。
8. `08_baselines_and_ablations.md`: 设计严谨 baseline 与 ablation。
9. `09_synthesis_protocol.md`: 规定如何把各 subagent 结果合并成主研究报告。

## 子任务依赖关系

```text
Literature Map
  -> Formal Model
      -> Router/Gates
      -> Memory KV-cache
      -> Textual Backprop
          -> Runtime Prototype
              -> Benchmark/Metrics
                  -> Baselines/Ablations
                      -> Synthesis
```

## 通用输出要求

每个 subagent 必须输出：

- `scope`: 当前子任务研究边界。
- `claims`: 可以被证据支持的结论。
- `design`: 可实现的设计，而不是单纯概念类比。
- `interfaces`: 与其他子任务相连的数据结构或 API。
- `experiments`: 至少 2 个可执行实验或对照。
- `risks`: 该方向最可能失败的地方。
- `open_questions`: 仍需主 agent 或其他 subagent 决策的问题。

## 通用质量标准

- 不要默认多 agent 更强，必须讨论成本、稳定性和负迁移。
- 不要只说 Transformer/MoE 类比，要给出可执行机制。
- 所有指标必须能从 trajectory/log 中计算。
- 每个设计都要说明最小版本、增强版本和可能的反例。
- 如果引用论文，优先使用论文原文、官方代码、benchmark 页面或作者项目页。
