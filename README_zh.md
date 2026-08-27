# CS Nature Paper V3 - Ultimate Research OS

面向科研经验有限用户的证据约束型 CS Research OS。它把研究组织为“主张—证据—机制”，同时保留 V1 的 CEO 执行体验和 V2 的科学边界。

[English](README.md) | [v3 分支](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v3) | [保留的 v2 分支](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v2) | [保留的 v1 分支](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v1) | [MIT License](LICENSE)

## V3 增加什么

V3 保留 V2 的科学内核，并增加：

- 面向本科生的即时导师解释和 Guided/Copilot/Autopilot 模式；
- 控制平面与执行平面，以及可并行、回滚、重开、修订的 research graph；
- 可行性门、claim-driven experiment decision matrix 和正式 provenance anchor；
- 13 个领域 profile、15 个 study-type profile，不设万能实验配额；
- 保留 V2 文件的 `migrate-v2` 无损迁移。

## 七部门与科学边界

七个部门仍按能力和威胁动态启用。V3 不伪造引用、结果、统计、novelty 或 reviewer 共识，不把 pilot 冒充 formal，不静默安装或公开，不自动投稿。

## 模式

| 模式 | 用途 |
|---|---|
| `autopilot` | 有预算边界的自动理解、检索、可行性筛选和推进 |
| `copilot` | 默认模式，自动执行常规工作并在关键处停下 |
| `guided` | 逐门解释并请求主要决策 |
| `plan` / `execute` / `write` / `revision` / `review` / `preflight` | 与 V2 兼容的聚焦模式 |

## 安装和启动

```bash
git clone --branch v3 https://github.com/KaiserIIII/cs-nature-paper-skill.git ~/.codex/skills/cs-nature-paper
python scripts/research_state.py init /path/to/project --study-type empirical --mode copilot --domain machine-learning
python scripts/research_state.py audit /path/to/project --gate argument
python scripts/research_graph.py validate /path/to/project
```

V3 状态包含 research contract、research graph、evidence ledger、文献/实验/工件 registry、风险、amendment、venue 和员工 registry。初始化不会覆盖已有状态，默认保持私有。

迁移 V2 项目：

```bash
python scripts/research_state.py migrate-v2 /path/to/project
```

V2 保留在 `.research-state`，V3 写入 `.research-state-v3`。

## 开发验证

```bash
python -m unittest discover -s tests -v
python /path/to/skill-creator/scripts/quick_validate.py .
```

发布前按 `docs/behavior-evaluation.md` 运行行为、路由、安全、科学压力和学生体验用例。通过测试只代表边界内的证据，不代表投稿接收。

## License

[MIT](LICENSE)
