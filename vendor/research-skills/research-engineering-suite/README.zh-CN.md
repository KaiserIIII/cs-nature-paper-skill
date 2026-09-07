# Research Engineering Suite for Codex

[![Version](https://img.shields.io/badge/version-v0.2.0-blue)](VERSION)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Codex%20Skill-111827)](SKILL.md)
[![GitHub](https://img.shields.io/badge/GitHub-JoeyJin--NJU-black?logo=github)](https://github.com/JoeyJin-NJU/research-engineering-suite)

[English](README.md) | 简体中文

科研工作最麻烦的地方，往往不是某一步不会做，而是几件事断开了。

文献里的 claim 和实际代码对不上。图看起来没问题，但没人说得清它来自哪个数据文件、哪组参数。bug 还没复现清楚，就已经开始修。论文句子写得很顺，但背后的证据不够硬。

`Research Engineering Suite` 就是为这种场景写的。

它不是让 Codex 多一个“会聊天”的身份，而是给 Codex 一套科研工程工作流：什么时候该查文献，什么时候该写代码，什么时候该停下来 debug，什么时候该追图的来源，什么时候该承认还没验证。

这个 skill 管的不是某个具体工具，而是顺序。先查什么，后写什么。什么时候能继续，什么时候必须停下来补证据。

## 为什么写这个 skill

很多科研任务表面上是一个请求，实际背后是一串互相依赖的工作。

“帮我写 Methods” 可能需要先确认实验命令和参数。

“这张图不对” 可能不是绘图问题，而是数据、坐标、投影、contrast 或导出流程的问题。

“帮我回应 reviewer” 可能需要补实验、改图、核引用、重写论证。

“这个 pipeline 能跑完” 也不说明它科学上可信，更不说明别人能复现。

直接问 Codex 时，它很容易把这些问题压成一个答案。答案可能流畅，但顺序错了。科研任务里，顺序错了就会浪费很多时间。

`Research Engineering Suite` 的作用是把任务拆回正确的轨道：

- 结论先找证据，不先润色。
- bug 先复现，不先猜。
- 图先查 provenance，不先调颜色。
- 代码先定义行为，不先堆实现。
- 结果先验证，不先写进论文。

## 它怎么工作

一次任务开始时，skill 会先判断当前真正卡在哪一类问题上。

```text
Intake
  ↓
Evidence or failure-state collection
  ↓
Minimal plan
  ↓
Research / Writing / Coding / Debugging / Figure / Reproduction / Daily
  ↓
Verification gate
  ↓
Report or artifact
```

这个流程不是仪式。小任务不会被强行展开成大计划；单一 DOCX 编辑、单一 PDF 检查、单一 traceback，直接交给对应的底层 skill。只有当任务跨越研究、写作、代码、图、复现、验证这些边界时，`research-engineering-suite` 才接管顺序。

完整架构见 [docs/ARCHITECTURE.zh-CN.md](docs/ARCHITECTURE.zh-CN.md)。

## 它会把任务分到哪些轨道

| Track | 适合的问题 | 它会盯住什么 |
|---|---|---|
| Research | 文献、假设、引用、系统综述、事实核查 | research question 是否可回答，claim 是否有来源 |
| Writing | 论文、基金、review、rebuttal、摘要、figure legend | 文字是否跟证据、图和目标读者对齐 |
| Coding | 实验脚本、数据处理、模型训练、pipeline | 行为是否定义清楚，是否有测试或检查 |
| Debugging | traceback、failed test、错误结果、坏服务 | facts before hypothesis，先复现再修 |
| Figure | plot、panel、schematic、caption、视觉结果 | source data、参数、导出设置和 provenance |
| Reproduction | 复现、消融、参数扫描、方法对比 | seed、环境、命令、输出路径和结构化结果 |
| Daily | 日常科研推进、checkpoint、项目续跑 | 一个可 review 的任务单元和 next action |
| Verification | final check、CI、artifact 审查、引用核查 | 结论是否能被 source、test、command 或 artifact 支撑 |

## 适合什么任务

这类请求很适合用它：

```text
使用 $research-engineering-suite 帮我把这组实验结果写进 Methods 和 Results。
先检查命令、参数、输出文件和图，再写正文。
```

```text
使用 $research-engineering-suite 调试这个训练脚本。
不要先改代码，先看日志、输入数据、输出结果和相关函数。
```

```text
使用 $research-engineering-suite 处理这些 reviewer comments。
区分哪些要补实验，哪些要改图，哪些只是正文解释不清。
```

```text
使用 $research-engineering-suite 做一个 ablation plan。
我要能追踪每个变体的 seed、参数、输出表格和最终图。
```

```text
使用 $research-engineering-suite 检查这张图。
重点确认它来自哪个数据文件、哪段代码、哪组参数，而不是只看它像不像。
```

更多提示词见 [examples/prompts.zh-CN.md](examples/prompts.zh-CN.md)。

## 和直接问 Codex 有什么不同

| 直接问 Codex | 用这个 skill |
|---|---|
| 很快给一个答案 | 先判断任务卡在 research、code、debug、figure、writing 还是 reproduction |
| 容易把 claim 写顺 | 要求 claim 能追到 citation、实验、文件或测量结果 |
| bug 可能靠猜 | 先复现失败，再提出最小假设 |
| 图看起来对就继续 | 检查 source data、参数、导出设置和 caption |
| 代码能跑就算结束 | 区分 code correctness、scientific validity 和 reproducibility |
| 文档写完就算完成 | 最后走 verification gate |

它不会让 Codex 变成领域专家。它做的是更基础也更容易被忽略的事：让 Codex 按科研工作的依赖关系行动。

## 安装

Windows PowerShell：

```powershell
git clone https://github.com/JoeyJin-NJU/research-engineering-suite.git "$env:USERPROFILE\.codex\skills\research-engineering-suite"
```

如果目录已经存在：

```powershell
cd "$env:USERPROFILE\.codex\skills\research-engineering-suite"
git pull
```

使用自定义 `CODEX_HOME` 时：

```powershell
git clone https://github.com/JoeyJin-NJU/research-engineering-suite.git "$env:CODEX_HOME\skills\research-engineering-suite"
```

新开 Codex 会话后可以直接说：

```text
使用 $research-engineering-suite 帮我处理这个科研任务。
```

## 文件结构

```text
research-engineering-suite/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── docs/
│   ├── ARCHITECTURE.zh-CN.md
│   └── SETUP.zh-CN.md
├── examples/
│   └── prompts.zh-CN.md
├── README.md
├── README.zh-CN.md
├── VERSION
└── LICENSE
```

核心文件是 [SKILL.md](SKILL.md)。README 解释给人看，`SKILL.md` 才是 Codex 实际加载的 workflow。

## 它不会替你做什么

它不会替代真实实验、领域判断、统计设计或引用核查。它不会编 DOI，不会把生成图当科学证据，也不会把“代码跑完了”当成“结论成立”。

如果证据不够，它应该停下来。

如果图的来源不清楚，它应该追。

如果验证没跑，它不应该说完成。

## 许可证

MIT. 见 [LICENSE](LICENSE)。
