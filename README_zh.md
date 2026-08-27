# CS Nature Paper V3.2.0

面向计算机科学研究、以学生为中心、受证据约束的可执行科研操作系统。

[English](README.md) | [v3.1.1 历史正式版](https://github.com/KaiserIIII/cs-nature-paper-skill/releases/tag/v3.1.1) | [MIT License](LICENSE)

## 这个项目是什么

CS Nature Paper 是一个 Agent Skill，帮助你把研究想法、代码库、数据集、
论文草稿、审稿意见或拒稿结果，逐步转化为当前证据与资源真正能够支撑的
最强研究成果包。它扮演科研负责人：解释陌生概念、组织工作、执行安全且
可逆的任务，并在涉及科学判断、较高成本、伦理、范围变化、公开操作或
不可逆行为时停下来交由作者决定。

它不是论文生成器、模型、SaaS、录用预测器或自动发布工具。它的职责是让
研究问题、协议、实验、主张、证据、图表、写作与审查始终通过明确记录
相互连接，避免论文文字跑到真实证据前面。

`v3.1.1` tag 仍是历史稳定版本，对应提交：
`081aa693b907d8cc07104d1b8251d46301094ef7`。当前 `v3.2` 分支从精确基线
`6b34dcba551bdf200c2d7dd49bcb6b6057ef67c4` 开发最大自治 release candidate。

## 系统如何工作

```text
研究想法、代码、数据、草稿、审稿意见或拒稿结果
                         |
                         v
                SKILL.md 诊断与路由
                         |
            +------------+------------+
            |                         |
            v                         v
       科研控制面                   科研执行面
  研究问题、主张、协议、       检索、阅读、编程、实验、
  证据、风险、预算、权限、     分析、绘图、写作、编译、
  科研图状态                   验证与审查
            |                         |
            +------------+------------+
                         |
                         v
             带 provenance anchor 的类型化工件
                         |
                         v
              PASS / CONDITIONAL / FAIL
                         |
                         v
             继续、缩小、修订、重开或停止
```

**科研控制面**负责科学含义：研究问题、范围、主张、证据关系、冻结协议、
修订、风险、权限和完成状态。**科研执行面**负责有限范围内的实际工作。
一条命令运行成功，并不自动使输出成为正式证据；输出必须以类型化工件
返回，并记录输入、命令、环境、哈希、不确定性、适用范围、代码版本和
验证状态。

工作流的事实来源是自适应 `research_graph.json`，而不是固定的阶段编号。
节点可以并行、失败、重开、回滚或被替代。每次状态转换还会写入追加式、
哈希关联的事件日志，因此科研图可以重建，篡改也能够被检测。

## 仓库结构

```text
SKILL.md                  自然语言路由、策略与主入口
agents/openai.yaml        $cs-nature-paper 的 Codex/OpenAI 元数据

references/
  core/                   控制循环、科研图、证据、安全、能力市场
  departments/            七个部门的契约与交接规范
  domains/                13 个 CS 领域 profile
  study-types/            实证、benchmark、理论、因果等研究设计
  methods/                统计、实验决策与文献支持关系
  mentoring/              面向学生的解释规范
  reviewing/              威胁驱动的审查与有界修订
  hosts/                  Codex、Claude Code 等宿主适配

assets/
  templates/v3/           新项目的私有状态模板
  schemas/                可机读 JSON 契约
  registry/               能力、方法、领域、研究类型和 Skill 注册表
  evals/                  行为、路由和安全压力用例
  legacy/v2/              保留的迁移输入，不用于创建新项目

scripts/                  确定性的 Python CLI 与运行时工具
tests/                    单元、集成、安全与回归测试
benchmarks/               已提交的运行时基准记录
docs/                     架构、审计、示例和发布报告
.github/                   Ubuntu/Windows 持续集成
```

`SKILL.md` 通过渐进式加载保持入口简洁：只有当模式、领域、研究类型、
方法、威胁或宿主需要时，才读取对应 reference。运行时工具只依赖 Python
标准库。

## 七个科研部门

七个部门是由科研图动态启用的能力契约，不是每次都必须顺序执行的流水线。

| 部门 | 主要职责 | 关键边界 |
|---|---|---|
| 文献 Literature | 检索、来源身份、材料获取、精确区域的主张支持核验 | 摘要片段或元数据不能支持关键主张 |
| 创新 Innovation | gap、机制、closest work、替代解释、falsifier 和贡献范围 | 不能因为一次快速检索没找到就宣称创新性 |
| 实现与实验 Implementation and Experiment | 协议到代码、pilot、正式实验、统计和可恢复任务 | pilot 和探索性结果不能静默升级为正式证据 |
| 图表 Figures | 绑定源数据的绘图、不确定性、可访问性和导出审计 | 图表不能产生比源数据更强的结论 |
| 写作 Writing | 可追溯证据、适配 venue 的写作和 claim trace | 文字不能扩大未经支持的范围或确定性 |
| 验证 Validation | 独立、fail-closed 地检查科学、数据、代码和文档 | 伪造、保密和授权失败不能通过平均分掩盖 |
| 审查 Review | 根据真实威胁选择审查视角、严重度、最小修复和剩余风险 | reviewer 数量不等于共识或录用预测 |

对于关键工作，生产者与检查者应当分离。外部 Skill 被视为“员工”：参与
正式证据工作前，必须具有精确固定的来源、最小权限、相关行为试验和回滚
路径。

## 科研状态与证据

初始化项目时会创建私有 `.research-state/` 目录。初始化不会修改
`.gitignore`，也会拒绝覆盖已有状态。

```text
project.json              项目标识、模式、领域、预算和权限
research_contract.json    论证、构念、范围、协议和 venue
research_graph.json       节点、边、当前状态和事件历史
claims.json               标准化主张、范围和 falsifier
evidence_ledger.json      证据关系、不确定性和替代解释
literature_registry.json  来源身份、材料获取和主张支持
experiment_registry.json discovery、pilot、formal 和修订实验
artifact_manifest.json    文件、哈希、命令、环境和公开边界
decision_log.md           人类可读的重要决策记录
amendments.json           追加式协议与分析修订
risks.json                风险、触发条件、负责人、缓解和剩余风险
employee_registry.json    已审核能力和权限
venue_profile.json        由当前一手来源支持的投稿要求
```

迁移会保留原始状态：V2 状态从 `.research-state` 复制到
`.research-state-v3`，V3 状态复制到 `.research-state-v31`。读取时依次
优先选择 `.research-state-v31`、`.research-state-v3`、`.research-state`。

证据 provenance 分为三个等级：

| 等级 | 含义 |
|---|---|
| `DECLARED` | 有人声明该记录存在，但运行时没有实际观察到 |
| `OBSERVED` | 真实命令或获取操作已经执行，并记录时间、退出状态、输出和哈希 |
| `VERIFIED` | 独立检查者重新核验了产出以及输入、配置和代码版本 |

旧记录即使写着 `status=VERIFIED`，如果缺少 provenance，也会迁移为
`DECLARED`，不能直接支持正式通过。文献同样采用 fail-closed 原则：
发现候选文献、验证来源身份、实际获取材料、验证精确区域对主张的支持，
是四个相互独立的操作。

## 安装

把经过审核的稳定 tag 安装到一个全新目录，然后核对其提交。

PowerShell：

```powershell
$SkillRoot = "$env:USERPROFILE\.codex\skills\cs-nature-paper"
git clone --branch v3.1.1 --depth 1 https://github.com/KaiserIIII/cs-nature-paper-skill.git $SkillRoot
git -C $SkillRoot rev-parse HEAD
```

Bash：

```bash
git clone --branch v3.1.1 --depth 1 \
  https://github.com/KaiserIIII/cs-nature-paper-skill.git \
  ~/.codex/skills/cs-nature-paper
git -C ~/.codex/skills/cs-nature-paper rev-parse HEAD
```

预期输出为：

```text
081aa693b907d8cc07104d1b8251d46301094ef7
```

不要覆盖含有本地改动的现有安装。使用外部 Skill 前应审核其代码，所有
参与正式研究的依赖都应固定到已经审核的 commit。

## 自然语言使用

项目的主要交互方式是描述研究任务，而不是填写 CLI 问卷。例如：

```text
使用 $cs-nature-paper，采用 copilot 模式。

我想研究 LLM 自动修复 Python 项目，科研经验不多。预算是普通个人电脑
和有限 API。请先完成领域导览、核验 closest literature、提出范围明确的
研究问题，并执行可行性门。正式实验、范围变化、付费资源、上传、发布或
投稿前停下来让我确认。
```

也可以从已有论文和实验材料开始：

```text
使用 $cs-nature-paper 的 review 模式审查这份草稿和实验工件。
把每个关键主张追溯到证据，根据真实威胁选择审查视角，给出最小且可辩护
的修复方案。不要预测录用结果。
```

## 运行模式

| 模式 | 用途 |
|---|---|
| `copilot` | 默认模式：执行常规工作，在重要检查点停下 |
| `guided` | 在请求决策前解释每个主要科研门 |
| `autopilot` | 在明确的预算和权限范围内持续推进 |
| `maximum-autonomy` | 在 standing authorization 允许的有限本地范围内持续执行，支持 session resume、自愈和 fail-closed completion contract |
| `plan` | 定位、gap、研究问题、协议和资源规划 |
| `execute` | 代码、数据、实验、分析与 provenance |
| `write` | 受证据约束的论文与 LaTeX/文档工作 |
| `revision` | 审稿问题、有界修订与转投 |
| `review` | 对抗性、威胁驱动的独立审查 |
| `preflight` | 当前 venue 规则与投稿包就绪检查 |
| `competition` | 正在进行的 CUMCM 工作；重大方向仍由作者决定 |
| `competition-autopilot` | 比较已提供赛题并启动可辩护的基线 |
| `competition-review` | 对竞赛论文和提交包做红队审查 |

Autopilot 不会取消作者控制权。遇到证据矛盾、provenance 缺失、预算边界、
伦理问题、未审核能力、协议修订或外部操作时，它必须停止。

Maximum autonomy 使用 `scripts/autonomy.py` 作为统一 policy/authorize 边界：
普通、可逆科研工作默认自动执行；网络科研、有界协议修订和中风险 Skill 招聘
会自动执行并写入 hash-chain audit。只有根本性科研范围变化、伦理、credentials、
付费、全局/管理员安装、私有数据外传、不可逆外部操作、公开发布和投稿才询问
作者。`scripts/director_loop.py` 调用真实 executor，并且只在 artifact 与 evidence
通过 output contract 后推进 graph。项目完成语义为 `READY_FOR_SUBMISSION`；
软件 release readiness 由独立流程验证。

## CUMCM 比赛覆盖层

比赛模式是通用 Research Graph 上的 policy overlay，继续使用原有的 evidence
ledger、claims、experiments、artifacts、provenance 和 handoffs，不建立第二套
科研状态系统。Runtime 只能根据时钟、风险、决策相关性和预计运行时间对
通用图节点进行排序、限制、冻结或放行。

唯一权威的时间边界是带时区的 ISO-8601 `contest_start_utc` 和
`submission_deadline_utc`。Runtime 统一转换为 UTC，并根据系统时钟计算实际
比赛时长、已用时间、剩余时间、阶段、STOP RULE 和 HARD FREEZE。仅配置时间
后，状态仍是 `UNVERIFIED`；必须由人工明确记录当届官方来源后才能核验。
未核验期间，Runtime 不得用截止时间授权新 job，也不得声称官方规则已确认。
人工偏移、暂停和恢复都必须填写 actor 与 reason，并追加到 SHA-256 哈希链
event log；`competition_clock.json` 只是当前派生快照。

三种典型调用方式：

```text
Use $cs-nature-paper in competition mode.
初始化这份 CUMCM 赛题和比赛时钟。重大科学方向变化由作者决定；每次输出
Runtime 计算的 dashboard 后，执行 Research Graph 中最高 ROI 的可用节点。
```

```text
Use $cs-nature-paper in competition-autopilot mode.
读取已提供的赛题和当前 competition state，核验时钟来源，比较题目并启动
最小且可辩护的 baseline。按图状态、风险、决策相关性、ETA 和剩余时间调度。
```

```text
Use $cs-nature-paper in competition-review mode.
审查这份竞赛论文和提交包，输出按严重性排序且有 evidence anchor 的问题，
以及十轴评分雷达。不要预测奖项，也不要编造当届官方规则。
```

默认 CUMCM profile 使用既定 72 小时阶段边界；其他时长按比例映射，除非
profile 给出显式边界。`SUBMISSION_FREEZE` 是正常计划阶段；绝对剩余 6 小时
触发的 `FINALIZATION_MODE` 和剩余 2 小时触发的 `HARD_FREEZE` 会覆盖普通
调度。任何新执行 job 都必须先通过 ETA 加当前阶段 safety margin 的门禁。

## 最小 CLI 工作流

CLI 提供确定性的科研控制面。在 PowerShell 中：

```powershell
$SkillRoot = "$env:USERPROFILE\.codex\skills\cs-nature-paper"
$Project = "D:\research\llm-repair"

python "$SkillRoot\scripts\research_state.py" init $Project `
  --study-type ml-benchmark --mode copilot --domain llm

python "$SkillRoot\scripts\research_state.py" audit $Project --gate argument
python "$SkillRoot\scripts\research_graph.py" validate $Project
python "$SkillRoot\scripts\research_graph.py" status $Project
python "$SkillRoot\scripts\research_graph.py" plan-next $Project
python "$SkillRoot\scripts\research_graph.py" ready $Project
python "$SkillRoot\scripts\research_graph.py" advance $Project
python "$SkillRoot\scripts\evidence_anchor.py" ledger $Project --deep
```

初始化并操作比赛覆盖层：

```powershell
python "$SkillRoot\scripts\research_state.py" init $Project `
  --study-type algorithmic --mode competition-autopilot `
  --domain mathematical-modeling

python "$SkillRoot\scripts\competition_runtime.py" configure-clock $Project `
  --start "2026-09-10T10:00:00Z" `
  --deadline "2026-09-13T10:00:00Z" `
  --official-source "https://official.example/rules" --actor "team-captain"

python "$SkillRoot\scripts\competition_runtime.py" verify-clock $Project `
  --official-source "https://official.example/rules" --actor "team-captain"

python "$SkillRoot\scripts\competition_runtime.py" dashboard $Project
python "$SkillRoot\scripts\competition_runtime.py" status $Project
python "$SkillRoot\scripts\competition_runtime.py" schedule $Project
python "$SkillRoot\scripts\competition_method_router.py" route `
  "Minimize facility cost subject to capacity constraints"
python "$SkillRoot\scripts\competition_review.py" audit competition-review.json
```

`configure-clock` 只记录候选边界，不会自动证明其权威性。执行
`verify-clock` 前必须重新检查真实比赛的当届官方来源。需要有记录的时钟
校正时，使用 `adjust-clock --offset-seconds ... --reason ... --actor ...`；
不要手工编辑快照或 event log。

解析能力或方法手册时，要把“选中了什么”与“实际执行了什么”区分开：

```powershell
python "$SkillRoot\scripts\skill_router.py" resolve `
  --project $Project --capability statistical-modeling

python "$SkillRoot\scripts\method_router.py" route `
  "Compare repair rates across repositories and random seeds" --project $Project
```

项目还提供文献核验、claim-driven 实验规划、可恢复长任务、证据执行与
验证、审查、交接、dashboard、隐私检查、安全压力用例、行为用例和发布
验证运行时。对任一脚本执行 `--help` 可以查看准确接口。

## 验证状态

`v3.1.1` 正式版通过了 57 个单元与集成测试；必要的
[GitHub Actions run](https://github.com/KaiserIIII/cs-nature-paper-skill/actions/runs/33107704416)
覆盖 Ubuntu/Windows 与 Python 3.10/3.11/3.12，矩阵结果为 6/6 PASS。

四层验证具有不同含义：

1. Schema 和确定性测试检查局部不变量。
2. 工作流集成测试检查状态、科研图、路由、迁移和 provenance。
3. Answer-hidden 行为用例定义安全和用户交互预期。
4. 公开安全的合成 smoke workflow 检查运行时能否端到端执行。

合成流程的分类是 `HARNESS_SELF_TEST`；它不是科学证据，也不是对研究模型
的评测。Model-backed behavior evaluation 仍为 `NOT_RUN`。不得把 harness
self-test 描述为真实模型评测。

开发验证命令：

```bash
python -m unittest discover -s tests -v
python scripts/validate_registry.py
python scripts/validate_release.py
python scripts/smoke_run.py --output .ci-smoke-result.json
python scripts/check_smoke.py .ci-smoke-result.json
python scripts/competition_smoke_run.py --output .competition-smoke-result.json
```

Competition smoke 使用有限的合成选址 fixture 和标准库穷举，只验证 runtime
集成。它的分类是 `HARNESS_SELF_TEST`，model-backed behavior evaluation 仍为
`NOT_RUN`。

## 这个项目不声称什么

- 不承诺 Nature、顶会或任何 venue 的录用结果。
- 不制造创新性、引用、数据、统计结果或 reviewer 共识。
- 不把 pilot、摘要片段、编译成功或单元测试通过包装成更强的科学证据。
- 不静默安装 Skill、使用凭证、花费资金、暴露私有材料、上传、发布或投稿。
- 不替代导师、领域专家、伦理委员会、artifact evaluator、审稿人或当前的
  venue 一手规则。
- 付费文献、实时投稿要求、外部 Skill、API 和模型服务仍需在启用时获取
 访问权限并重新验证。

目标不是得到最大的主张，而是得到现有记录、研究设计和资源能够诚实支撑
的最强主张。

## 进一步阅读

- [V3 架构](docs/V3_ARCHITECTURE.md)
- [V3.1 合成端到端示例](docs/v3.1-end-to-end-example.md)
- [V3.1.1 发布报告](docs/v3.1.1-release-report.md)
- [行为评测协议](docs/behavior-evaluation.md)
- [V1/V2/V3 替换与迁移审计](docs/v3-v1-v2-design-audit.md)
- 历史分支：[v3.1.1-hardening](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3.1.1-hardening)、[v3.1](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3.1)、[v3](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3)、[v2](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v2)、[v1](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v1)

## 许可证

[MIT](LICENSE)
