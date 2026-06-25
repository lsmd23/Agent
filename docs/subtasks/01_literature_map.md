# Subtask 01: Literature Map

## 目标

建立本研究的文献地图，回答：已有工作分别解决了 agent loop、tool use、multi-agent aggregation、routing、memory、reflection、continual learning、evaluation 中的哪些问题？哪些问题仍然没有被系统解决？

## 子任务分类

主要属于：

- literature review
- theory positioning
- benchmark and framework survey

## 输入

- 原始研究 guideline。
- `docs/research_memo.md` 中已有的初步文献列表。
- 相关关键词：ReAct、Toolformer、HuggingGPT、Reflexion、Voyager、Memory Networks、Mixture-of-Agents、MasRouter、Agent-as-a-Router、LLM routing、agent memory、textual backpropagation。

## 核心问题

1. 哪些论文可以作为固定 workflow / single-agent / retrieval-memory / MoA / routing 的代表 baseline？
2. 哪些工作真正有 routing policy，哪些只是 controller 或 planner？
3. 哪些工作保存行为经验，而不仅是知识检索？
4. 哪些工作有失败反馈更新机制？
5. 哪些 benchmark 可以衡量 long-horizon agent 的效率、稳定性和迁移？

## 推荐方法

按以下类别整理文献：

- `Loop and Acting`: ReAct、Plan-and-Execute、Reflexion 类。
- `Tool Use`: Toolformer、API/tool learning、HuggingGPT 类。
- `Multi-Agent Aggregation`: Mixture-of-Agents、debate、committee、panel 类。
- `Routing`: model routing、agent routing、skill routing、multi-agent system routing。
- `Memory`: Memory Networks、RAG memory、episodic memory、skill library。
- `Self-Improvement`: Reflexion、Voyager、textual feedback、self-evolving agents。
- `Evaluation`: WebShop、ALFWorld、HumanEval、SWE-bench、agent benchmark、routing benchmark。

## 输出格式

输出一个文献表：

```markdown
| Work | Year | Category | Core Mechanism | Agent Module Mapping | Evaluation | Limitation For This Project |
| ---- | ---- | -------- | -------------- | -------------------- | ---------- | --------------------------- |
```

再输出一个 taxonomy：

```text
Fixed workflow
Dynamic planner/controller
Tool-use learner
Memory-augmented agent
Multi-agent aggregator
Routing-optimized agent
Self-improving agent
```

## 交付物

- `literature_table.md`
- `taxonomy.md`
- `gap_analysis.md`
- `must_read_papers.md`

## 成功标准

- 至少覆盖 20 篇或系统。
- 每篇都说明和本研究的关系，不只写摘要。
- 明确指出本项目和 ReAct、MoA、HuggingGPT、Reflexion、Voyager 的差异。
- 找出 3 个可作为主 baseline 的系统和 3 个可借鉴的机制。

## 常见失败

- 把所有 agent paper 都塞进列表，但没有结构。
- 只按年份排序，没有按机制分类。
- 忽略 evaluation 和 benchmark。
- 过度依赖二手博客，没有回到论文或官方实现。
