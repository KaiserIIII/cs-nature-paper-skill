# CS Nature Paper v2

面向计算机科研与投稿的证据约束型总控 skill。它把研究组织为“主张—证据—机制”，避免把实验数量、agent 数量、篇幅或模拟审稿人一致性误当成科学贡献。

[English](README.md) · [保留的 v1 分支](https://github.com/KaiserIIII/cs-nature-paper-skill/tree/v1) · [MIT License](LICENSE)

## 第二代改了什么

v2 用六道科学门替换 v1 固定、耗 token 的全流水线：

1. 明确利益相关者问题、构念、适用范围、机制和可证伪条件；
2. 将每个关键主张映射到所需证据和实际证据；
3. 冻结协议、保留历史证据，并在修改前登记 amendment；
4. 只有在新实验能检验明确威胁或改变结论时才扩大实验；
5. 先通过编辑 90 秒测试，再堆叠专家细节；
6. 核验引用、数字、统计、图表、工件和当期投稿规则。

七大部门仍然保留，但按任务自适应启用。局部润色、拒稿诊断或图表检查不再强制启动整条流水线。

## 七种模式

| 模式 | 用途 |
|---|---|
| `full` | 从研究材料到分阶段投稿包 |
| `plan` | 定位、研究问题和协议 |
| `execute` | 实现实验并冻结可复现证据 |
| `write` | 按证据起草或修改论文 |
| `revision` | 处理评审或拒稿，控制范围膨胀 |
| `review` | 编辑、领域与方法的证据化审查 |
| `preflight` | 核验最新投稿规则和提交包 |

## 安装

把本目录克隆或复制到所用 agent 的 skills 目录。Codex 的一种常见安装方式是：

```bash
git clone --branch v2 https://github.com/KaiserIIII/cs-nature-paper-skill.git ~/.codex/skills/cs-nature-paper
```

应先审查第三方 skill 并固定版本。v2 不会静默安装依赖、执行未审查 hook、公开工件或自动投稿。

## 使用

直接在请求中调用：

```text
使用 $cs-nature-paper 的 revision 模式。拒稿信只保留在本地，建立问题—证据—修改矩阵，并判断哪些新增实验真的会改变论文主张。
```

大型项目可以初始化可选的私有研究状态：

```bash
python scripts/research_state.py init /path/to/project --study-type empirical --mode full
python scripts/research_state.py audit /path/to/project --gate argument
```

它会创建 `/path/to/project/.research-state/`：

- `research_contract.json`：构念、范围、机制、协议和 venue 来源；
- `evidence_ledger.json`：主张状态、证据锚点、不确定性和反证；
- `decision_log.md`：重要科研决定和 amendment。

初始化不会覆盖现有状态；这些文件默认私有，是否发布净化后的版本由作者决定。

## 关键边界

- 单一固定目标支持有限的 fixed-target 主张，不自动代表总体；
- 依赖解析、编译等步骤可能只是执行复现的前置门槛；
- 关联不自动等于衰减、因果、混杂控制或维护成本；
- 重复次数、环境、baseline 和消融由研究设计决定，不设万能数量；
- 模拟审稿角色不是独立人类审稿人，也不能保证接收；
- 投稿时从期刊或会议官网重新核验规则，不维护容易过期的静态页数表。

## 版本策略

- `v1`：原版永久保留；
- `v2`：第二代开发与候选发布分支；
- `main`：只有作者审阅并合并后才升级。

## 开发验证

```bash
python -m unittest discover -s tests -v
python /path/to/skill-creator/scripts/quick_validate.py .
```

## License

[MIT](LICENSE)
