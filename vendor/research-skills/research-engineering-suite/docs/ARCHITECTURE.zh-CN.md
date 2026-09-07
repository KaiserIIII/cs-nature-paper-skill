# 架构说明

`research-engineering-suite` 是一个编排型 Codex skill。它不替代底层专业 skill，而是在科研混合任务中决定先走哪条路径、何时切换路径、最后用什么证据验证。

## 总体流程

```text
Intake
  ↓
Evidence or failure-state collection
  ↓
Minimal plan
  ↓
Research / Writing / Coding / Debugging track
  ↓
Verification gate
  ↓
Final artifact or concise report
```

## 1. Intake

目标是建立最小可执行上下文：

- objective：要改变哪个结论、文件、实验、代码路径或 artifact。
- inputs：精确路径、论文、数据、figure、日志、命令、环境、约束。
- output：回答、代码 patch、实验计划、论文段落、review、表格、图、复现报告。
- evidence standard：一手文献、官方文档、本地 artifact、测试、数值检查、reviewer logic。
- risk：如果不检查，哪一部分最可能误导。

默认直接检查用户给出的文件、repo、日志或来源。只有当错误假设会显著改变结果时才追问。

## 2. 模式路由

| 主导模式 | 触发信号 | 第一动作 |
|---|---|---|
| Research | 文献、假设、引用、系统综述、事实核查 | 收敛 research question；查证来源；维护 evidence matrix。 |
| Writing | 论文、基金、review、rebuttal、摘要、DOCX/PDF/LaTeX | 明确目标格式和读者；让 claim 跟证据对齐。 |
| Coding | 实验实现、脚本、数据处理、模型、pipeline | 读 repo；定义行为；优先测试驱动。 |
| Debugging | traceback、failed test、错误图、坏服务 | 复现或检查当前失败；最小假设；最小修复。 |
| Verification | final check、CI、artifact 审查、引用诚信 | 用命令、测试、来源、渲染或本地文件确认。 |
| Figure | 论文图、panel、plot、schematic、caption | 分离 source data、plot/render 设置和 visual provenance。 |
| Reproduce | 复现、消融、参数扫描、方法对比 | 固定 seed/环境/命令，记录结构化结果和输出路径。 |
| Daily | 日常科研计划、checkpoint、项目续跑 | 选择一个可 review 的任务单元，保留 checkpoint 和 next action。 |

## 3. Research Track

适用于外部知识、文献、科学结论、数据库和引用完整性。

要求：

- 先把宽泛主题变成可回答问题。
- 区分 evidence、inference、recommendation。
- 当前事实、政策、API、统计数字和引用必须查 authoritative source。
- 不制造 DOI、作者、年份、样本量、结果、期刊规则。
- 生命科学问题优先路由到 `life-science-research:*`。
- 文献密集任务维护 compact evidence matrix。

## 4. Writing Track

适用于论文、基金、审稿、rebuttal、摘要、figure legend、slides、DOCX/PDF/LaTeX。

要求：

- 保留用户要求的格式、语言、压缩程度和目标读者。
- 研究问题不清楚时先 scoping，不直接写大纲。
- 批评要具体：novelty、method、controls、statistics、structure、interpretation、reproducibility。
- 修回任务要建立 reviewer concern 到 manuscript change/response 的追踪。
- 文件型输出要尽量验证解析、渲染或导出结果。

## 5. Coding Track

适用于科研脚本、数据处理、模型训练、仿真、可视化和自动化。

要求：

- 先读现有代码风格和 helper API。
- 行为变更优先用 `test-driven-development`。
- 保持 patch 小，避免无关重构。
- 记录命令、参数、输入路径、输出路径、seed 和环境。
- 区分 code correctness、scientific validity、reproducibility。

## 6. Debugging Track

适用于 traceback、failed test、错误输出、坏服务、复现失败。

要求：

- 先复现或检查当前失败状态。
- 事实先于猜测：错误文本、命令、输入、输出、环境、端口、artifact mismatch。
- 每次只检验一个最小可证伪假设。
- 修 root cause，不做宽泛重写。
- 修后重跑失败检查和邻近回归检查。

视觉/数据问题要拆开：

- source data 是否正确。
- 坐标、scale、contrast、projection、render pacing、export 是否正确。
- provenance 能精确追踪时，不用视觉相似度替代。

## 7. Figure Track

适用于论文图、数据图、schematic、panel、caption、截图、volume rendering、projection 或 visual provenance。

要求：

- 判断图是 data-derived、schematic、screenshot、rendering 还是 mixed。
- 数据派生图必须尽量追踪到 source file、command、parameter 和 processing step。
- 不把“视觉相似”当作 provenance。
- 分离 source data 与 axis scale、contrast、projection、color map、label、panel order、export size。
- 让 caption 与数据、代码、正文 claim 同步。

## 8. Reproduction Track

适用于复现、消融、参数扫描、benchmark 和方法变体对比。

要求：

- 先定义要复现的 claim/result。
- 记录 data version、code commit、command、parameters、seed、environment、hardware、output path。
- 变体运行要隔离 branch/worktree/output directory/run ID。
- 结果优先保存成 CSV/JSON/Parquet 或结构化日志。
- 区分代码没跑、代码跑了但数值不一致、数值一致但科学解释不成立、artifact 导出不一致。

## 9. Daily Track

适用于日常科研推进和项目续跑。

要求：

- 选择一个当天能完成并 review 的主任务。
- 定义 artifact：patch、实验结果、表格、图、段落、review note 或 decision。
- 用 commit、输出目录、run manifest 或简洁日志保留 checkpoint。
- 收尾写 result、surprise、blocker、next action。

## 10. Verification Gate

完成前检查：

- 是否回答了最新用户请求。
- 主要 claim 是否绑定来源、文件、命令、测试或测量结果。
- 是否运行了相关测试、parser、renderer、linter、命令或 artifact inspection。
- 未验证的部分是否明确说明。
- 最终是否保留可复用的命令、路径、参数和残余风险。

## 底层 skill 路由

| 需求 | 底层 skill |
|---|---|
| 文献、论文、引用、peer review、paper pipeline | `academic-research-suite` |
| 生物医学数据库、蛋白、药物、基因、临床试验 | `life-science-research:*` |
| 功能、bugfix、refactor、行为变更 | `test-driven-development` |
| 报错、失败运行、错误结果 | `systematic-debugging` |
| 完成前验证 | `verification-before-completion` |
| Word/PDF/LaTeX/PPTX/XLSX | `docx` / `pdf` / `latex-tectonic` / `pptx` / `xlsx` |
| GitHub repo、PR、CI | `github:*` |
| Hugging Face 模型、数据、训练、评测 | `hugging-face:*` |
| 本地网页、浏览器 UI、截图验证 | `playwright` / `browser-use:browser` |
| 图、panel、plot、visual artifact | 项目绘图脚本、notebook、Python 工具链；生成式图像只用于视觉创作，不作为科学证据。 |
| 复现、消融、参数扫描 | 隔离分支/输出目录、结构化 run manifest、`verification-before-completion` |
