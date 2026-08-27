# CS Nature Paper V3.1.1 - 可执行科研操作系统

面向科研经验有限用户的证据约束型 CS Research OS。它把研究组织为“主张—证据—机制”，同时保留 V1 的 CEO 执行体验和 V2 的科学边界。

[English](README.md) | [v3.1.1 hardening 分支](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3.1.1-hardening) | [v3.1 分支](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3.1) | [v3 分支](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3) | [保留的 v2 分支](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v2) | [保留的 v1 分支](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v1) | [MIT License](LICENSE)

## 这是什么

这是给科研训练尚不完整、但希望认真做 CS 研究的学生使用的入口。你只需描述想研究的问题，系统会把它拆成入门说明、文献核验、研究问题、可行性、pilot、正式协议、证据、图表、写作、审查和复现准备；重要科学判断和公开操作仍由作者决定。

## V3.1 增加什么

V3.1 保留 V2/V3 的科学边界，并把运行时真正落地：

- 面向本科生的即时导师解释和 Guided/Copilot/Autopilot 模式；
- 控制平面与执行平面，以及可并行、回滚、重开、修订的 research graph；
- 可行性门、claim-driven experiment decision matrix 和正式 provenance anchor；
- 13 个领域 profile、15 个 study-type profile，不设万能实验配额；
- 能按能力选择最小合格 Skill 团队，并生成 delegation/handoff；
- 可执行、可重建的 research graph 事件日志，支持 ready/advance/reopen/rollback；
- 深度 evidence anchor 核验本地工件、哈希、区域、commit、命令、退出状态和 checker；
- 文献、方法、实验、长任务、审查、雄心分析和 answer-hidden 行为评测运行时；
- 新项目只使用 `assets/templates/v3/`，V2 模板明确放在 `assets/legacy/v2/`。

## 七部门与科学边界

七个部门仍按能力和威胁动态启用。V3.1 不伪造引用、结果、统计、novelty 或 reviewer 共识，不把 pilot 冒充 formal，不静默安装或公开，不自动投稿。

## 模式

| 模式 | 用途 |
|---|---|
| `autopilot` | 有预算边界的自动理解、检索、可行性筛选和推进 |
| `copilot` | 默认模式，自动执行常规工作并在关键处停下 |
| `guided` | 逐门解释并请求主要决策 |
| `plan` / `execute` / `write` / `revision` / `review` / `preflight` | 与 V2 兼容的聚焦模式 |

## 安装和启动

```bash
git clone --branch v3.1.1-hardening https://github.com/KaiserIIII/cs-nature-paper-skill.git ~/.codex/skills/cs-nature-paper
python scripts/research_state.py init /path/to/project --study-type empirical --mode copilot --domain machine-learning
python scripts/research_state.py audit /path/to/project --gate argument
python scripts/research_graph.py validate /path/to/project
python scripts/skill_router.py resolve /path/to/project --capability statistical-modeling
python scripts/evidence_anchor.py validate /path/to/project/anchor.json --deep --root /path/to/project
```

V3.1 状态包含 research contract、research graph、evidence ledger、文献/实验/工件 registry、风险、amendment、venue 和员工 registry。初始化不会覆盖已有状态，默认保持私有。

迁移 V2 项目：

```bash
python scripts/research_state.py migrate-v2 /path/to/project
```

V2 保留在 `.research-state`，V3 写入 `.research-state-v3`，V3.1 写入 `.research-state-v31`；迁移会记录来源并拒绝覆盖目标。

推荐给学生的第一句话：

```text
使用 cs-nature-paper autopilot。我想研究 LLM 自动修复 Python 项目。
我科研经验不多，请优先在普通个人电脑和合理 API 预算内设计，
并把每个重要科学决策停下来让我确认。
```

## 四层验证

- Level 1：schema/确定性单元测试，证明局部不变量；
- Level 2：workflow integration，证明状态、图、路由和溯源能协同；
- Level 3：answer-hidden behavior runner，证明安全和用户行为；模型不可用时标记 `NOT_RUN`；
- Level 4：合成/公开安全的端到端 smoke run，证明流程可执行，不制造论文结果。

这些验证都不等于论文真实、顶会接收或 Nature 承诺。

## 开发验证

```bash
python -m unittest discover -s tests -v
python scripts/validate_registry.py
python scripts/validate_release.py
python scripts/smoke_run.py --output .ci-smoke-result.json
python scripts/check_smoke.py .ci-smoke-result.json
```

发布前按 `docs/behavior-evaluation.md` 运行行为、路由、安全、科学压力和学生体验用例。通过测试只代表边界内的证据，不代表投稿接收。

## License

[MIT](LICENSE)
