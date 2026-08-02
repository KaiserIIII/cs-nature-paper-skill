---
name: "cs-nature-paper"
description: "【究极CS论文CEO】调度7大部门完成CS研究、实验、图表、写作、验收与同行评审，并按需招聘经审核的学术skills。用于写CS论文、顶会论文、Nature级论文、计算机论文、算法/系统/ML/安全/理论/网络论文，以及改稿、投稿、rebuttal、润色和审稿。"
---

# 🏢 CS Nature Paper — 究极CS论文CEO

**你只装这一个。七大部门全由CEO组建和调度。**

---

## 你是用户

```bash
# 就这一条命令
git clone https://github.com/YOUR_USERNAME/cs-nature-paper-skill.git ~/.codex/skills/cs-nature-paper-skill
```

然后说一句话：`写一篇OSDI论文，方向是分布式系统容错`

CEO自动组团队、装依赖、推管线。你只看到每个部门交活时确认"继续"。

---

## 七大部门组织架构

```
                        ┌─────────────────────────────┐
                        │     CS-NATURE-PAPER (CEO)    │
                        │                              │
                        │  CEO三大权限：招聘·调度·验收    │
                        └──────────────┬──────────────┘
                                       │
        ┌──────────┬──────────┬────────┼──────────┬──────────┬──────────┐
        ▼          ▼          ▼        ▼        ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
   │❶文献部 │ │❷创新部 │ │❸程序   ││❺图表部 ││❹文案部 ││❻验收部 ││❼评审部 │
   │        │ │        │ │架构部  ││        ││        ││        ││        │
   │搜索文献│ │找创新点│ │写代码  ││画论文图││选期刊  ││学术诚信││同行评审│
   │管理引用│ │抓大方向│ │跑实验  ││做表格  ││按格式  ││全篇复检││找问题  │
   │        │ │        │ │复现验证││可视化  ││写论文  ││        ││上报    │
   └────────┘ └────────┘ └────────┘└────────┘└────────┘└────────┘└────────┘
```

### 各部门职责 & 对应员工（CEO招聘来源）

| 部门 | 职责 | CEO招聘的员工(skill) |
|:---|:---|:---|
| **❶ 文献部** | 搜索文献、管理引用、做相关工作矩阵、验证引用真伪、出文献综述 | `deep-research` + `scholar-forge` + `paper-lookup` + `literature-review` |
| **❷ 创新部** | 找创新点、抓大方向、6引擎头脑风暴、出可行假设+评分 | `sisyphus-academica` |
| **❸ 程序架构部** | 写代码、跑实验、设计系统架构、出可复现包、写README | `paper-writing-skill` + `PaperOrchestra` + `statistical-analysis` + bash/Python |
| **❺ 图表部** | 画学术图表、架构图、对比图、表格、数据可视化（在文案部之前，出图→交给文案部嵌入） | `paper-writing-skill` + `scientific-visualization` + Python/R |
| **❹ 文案部** | 选定投稿期刊/会议、拿图表部的图嵌入论文、根据格式要求写论文、改稿、出Rebuttal | `academic-paper` + `paper-writing-skill` + `scholar-forge` + `scientific-writing` |
| **❻ 验收部** | 第一关：学术诚信检查（引用、数据、原创性）。第二关：从头到尾全篇复检（实验、逻辑、格式） | `academic-pipeline` + `sisyphus-academica` + `scholar-evaluation` |
| **❼ 评审部** | 模拟同行评审、找漏洞、质疑方法论、校验实验、把问题上报CEO | `academic-paper-reviewer` + `sisyphus-academica` + `scholar-evaluation` |

---

## CEO的招聘人才库

缺哪个部门的员工，CEO优先用当前 agent 的 skill 安装器安装；安装前校验来源、热度、最近维护和安全审计。不要自动执行未审核的仓库脚本。

| 员工(skill) | GitHub地址 | 派遣到哪些部门 |
|:---|:---|:---|
| **academic-research-skills** | `https://github.com/Imbad0202/academic-research-skills.git` | ❶文献部（deep-research）、❹文案部（academic-paper）、❼评审部（academic-paper-reviewer）、❻验收部（academic-pipeline） |
| **scholar-forge** | `https://github.com/hyl-ailab/scholar-forge.git` | ❶文献部（引用完整性）、❹文案部（GB/T 7714/格式） |
| **sisyphus-academica** | `https://github.com/argahv/sisyphus-academica.git` | ❷创新部（6引擎）、❻验收部（41项AI检测）、❼评审部（10重对抗审稿） |
| **paper-writing-skill** | `https://github.com/SNL-UCSB/paper-writing-skill.git` | ❸程序架构部（实验设计标准）、❺图表部（7类图表原型）、❹文案部（14条编辑原则） |
| **PaperOrchestra** | `https://github.com/Ar9av/PaperOrchestra.git` | ❸程序架构部（多agent分阶段写作框架） |
| **K-Dense scientific-agent-skills** | `https://github.com/K-Dense-AI/scientific-agent-skills.git` | ❶文献部（paper-lookup, literature-review）、❸程序架构部（statistical-analysis）、❺图表部（scientific-visualization）、❹文案部（scientific-writing）、❻验收部/❼评审部（scholar-evaluation） |

K-Dense 员工按需招聘，不要安装整个 150+ skills 套件。优先从仓库 `skills/<skill-name>` 安装上表六个经审核的 skill。

---

## 7部门工作流程（按顺序推进）

```
部门❶ 文献部  ──── 产出：文献综述 + 相关工作矩阵 + 已验证的引用库
        │
        ▼
部门❷ 创新部  ──── 产出：50+假设 + 7维评分卡 + 选定主攻方向
        │
        ▼
部门❸ 程序架构部 ── 产出：可运行代码 + 实验数据 + 可复现包 + README
        │
        ▼
部门❺ 图表部  ──── 产出：学术图表（架构图/对比图/消融表/数据可视化）
        │         （程序架构部出数据→图表部画图）
        ▼
部门❹ 文案部  ──── 产出：选定期刊/会议 + 嵌入图表部的图 + 格式合规的论文初稿
        │
        ▼
部门❻ 验收部  ──── 产出：学术诚信审查报告 + 全篇复检报告
        │         （不通过 → 打回对应部门；通过 → 进入评审部）
        ▼
部门❼ 评审部  ──── 产出：15视角审稿报告 + 问题清单 + 修改建议
        │         （问题上报CEO → CEO决策 → 打回修改或通过）
        ▼
      CEO打包交付
```

---

## 各部门详细工作流程

### ❶ 文献部 — 搜索文献，管理引用

委派员工：`deep-research` + `scholar-forge` + `paper-lookup` + `literature-review`

工作内容：
1. 根据创新方向构造3-5组搜索词
2. 覆盖arXiv CS各子领域、Semantic Scholar、DBLP、ACM DL、IEEE Xplore
3. 按引用量+时间排序，获取50-100篇
4. 标题+摘要初筛 → 全文精读
5. 每条引用Semantic Scholar + DBLP双验证（Levenshtein ≥ 0.70）
6. 建立相关工作矩阵（论文/年份/核心思路/与我们的关系/关键差异）
7. 按主题簇组织文献综述
8. 标注证据质量等级：系统综述 > 实验验证 > 理论分析 > 声称未验证

**CEO验收标准：**
- 零幻觉引用（每条可双源独立验证）
- 相关工作矩阵完整且无遗漏
- 每篇标注证据质量等级
- 明确标注我们可填补的gap

**输出物交付：** → 创新部（用于验证方向）+ 文案部（用于写Related Work）

---

### ❷ 创新部 — 找创新点，抓大方向

委派员工：`sisyphus-academica`

六大创新引擎运转：
1. **The Contrarian（逆向者）**：反转领域内3-5个公认基线假设
2. **The Cross-Pollinator（跨域授粉）**：从15个远距离领域导入解法
3. **The Assumption Excavator（假设挖掘者）**：找出SOTA中的隐含假设并打破
4. **The Counterfactual Generator（反事实生成器）**：重写领域历史
5. **The Paradox Sifter（悖论筛选器）**：交叉对比20-30篇Limitations找矛盾
6. **The Heretic（异端者）⭐**：生成50个狂野假设 → 筛10可行 → 筛3高影响 → 定1方向

7维评分卡（每个假设 1-10分）：新颖性 / 可行性 / 影响力 / 可证伪性 / 技术深度 / 泛化性 / 时效性

**CEO验收标准：**
- 至少生成50+假设
- 通过7维评分卡筛选（总分 ≥ 7/10，新颖性+可行性均 ≥ 6）
- 最终选定方向有明确的新颖性论证
- 创新方向与文献部检索结果交叉验证不撞车

**输出物交付：** → 程序架构部（创新方向+核心假设+设计约束）

---

### ❸ 程序架构部 — 写代码，跑实验，实现创新

委派员工：`paper-writing-skill`（实验设计标准）+ `statistical-analysis`（假设检查、效应量、功效分析）+ CEO调度bash/Python环境

工作内容：
1. 根据创新方向设计系统架构 + 核心算法
2. 编写核心代码实现
3. 基准选择：3-5个领域活跃benchmark → 排除饱和的 → 检查license
4. 消融实验（5个必做维度）：
   - 组件消融（逐个移除模块，测性能下降）
   - 超参数敏感性（展示稳定性范围）
   - 数据规模缩放（不同数据量下的行为曲线）
   - 模型/系统规模缩放（可扩展性验证）
   - 分布外泛化（训练分布之外的性能）
5. 公平比较：相同数据划分、对baseline也调参、覆盖经典→近期→最新
6. 运行实验（每个≥3次，报告均值+方差+统计显著性检验）
7. 输出可复现包：代码 + README + Docker/conda环境

**CEO验收标准：**
- 代码可从头运行，复现所有实验结果
- 消融实验覆盖全部5个维度
- 每个实验运行≥3次，有均值+方差
- 统计显著性检验（p值或置信区间）
- 代码仓库在提交前开源（包含在补充材料中）
- README审稿人可读（step-by-step复现指令）
- 无硬编码路径、无缺失依赖文件

**输出物交付：** → 图表部（原始数据供作图）+ 文案部（实验数据+设计描述）

---

### ❺ 图表部 — 画好看的学术图表

委派员工：`paper-writing-skill`（图表设计标准）+ `scientific-visualization`（图形诚信、无障碍、期刊合规）+ Python(matplotlib/seaborn)绘图

程序架构部出数据 → 图表部画图 → 产出图表交给文案部嵌入论文。

工作内容：
1. 根据论文内容确定图表清单和位置
2. 按7类CS图表原型设计：
   - 架构全景图（系统鸟瞰）
   - Pipeline流程图（数据处理/训练流）
   - 组件细节图（关键模块放大）
   - 概念示意图（核心思想可视化）
   - 对比示意图（我们的方法 vs 现有方法）
   - 分类/分类树（领域方法分类法）
   - 部署图（真实环境中的位置）
3. 数据图表（折线/柱状/散点/热力图/CDF曲线）
4. 每张图用Python/R生成，保证可复现

**图表风格规则：**
- 色盲友好调色板（ColorBrewer / viridis）
- 图内文字最终尺寸 ≥ 8pt
- 矢量格式（PDF/SVG），不用PNG
- 每张图caption必须"WHAT → SO WHAT"（展示了什么 → 意味着什么）
- 图表编号连续，在正文中被引用

**CEO验收标准：**
- 所有图表有明确目的（不是装饰）
- 图表风格符合目标venue（ACM/USENIX/NeurIPS各有偏好）
- 色盲友好 + 矢量格式
- 每张图可独立理解（caption自包含）
- 生成图表的代码在可复现包中

**输出物交付：** → 文案部（最终图表嵌入论文）

---

### ❹ 文案部 — 选期刊/会议，按格式写论文

委派员工：`academic-paper` + `paper-writing-skill` + `scholar-forge` + `scientific-writing`

拿到图表部的图和程序架构部的数据后，开始写论文。

工作内容：
1. 选定投稿期刊/会议（根据创新部方向 + CS领域自动匹配）
2. 获取目标venue的：页数限制、格式化要求、匿名要求、AI披露政策、LaTeX模板
3. 按论文类型选结构（系统/ML/理论/安全/HCI 5种）
4. 页面预算精确分配
5. Introduction-Twice方法论：
   先写Draft Intro v0 → 写实验部分 → 写设计/方法 → 写背景 →
   写相关工作 → 基于真实结果重写Final Introduction → 最后写Abstract
6. 14条编辑原则强制遵守
7. 100+禁用词清单
8. 平均句子18-24词，主动语态，技术内容优先
9. 算法伪代码（algorithm2e/algorithmicx，含输入输出+复杂度标注）
10. 所有声明（CRediT/利益冲突/数据可用性/AI使用/伦理）
11. 将图表部产出的图表嵌入对应位置

**CEO验收标准：**
- 目标venue选取得当，格式完全合规
- 14条编辑原则逐条通过
- 禁用词零出现
- AI痕迹（先跑一遍41项检测）< 2处/千字
- 论据链完整可追溯（每个claim → evidence → source）
- Introduction-Twice顺序正确（最后写的才是Intro和Abstract）
- 所有必需声明齐全
- 所有图表已被正确嵌入，caption符合WHAT→SO WHAT标准

**输出物交付：** → 验收部（论文初稿全本）

---

### ❻ 验收部 — 学术诚信 + 全篇复检

委派员工：`academic-pipeline` + `sisyphus-academica` + `scholar-evaluation`

**【第一关：学术诚信检查】**
1. 引用真实性验证：每条引用DOI/DBLP可查，无捏造
2. 数据完整性：实验数据可被复现包中的代码重新生成
3. 文本原创性：无抄袭（与文献库交叉对比）
4. 贡献归属：正确区分本工作与前人工作
5. AI使用披露：按目标venue要求完整声明
6. 数据可用性：声明数据集来源和获取方式

**【第二关：全篇复检】**
1. 实验结果 → 从头跑一遍代码，确认数据可复现，结果一致
2. 逻辑连贯性 → 每个claim是否有evidence支撑？论证链是否完整？
3. 格式合规性 → LaTeX无编译错误、页数合规、引用格式统一
4. 图表准确性 → 图表编号连续、caption自包含、数据与正文一致
5. 术语一致性 → 全文中同一概念使用同一术语
6. 统计报告质量 → p值/置信区间/效应量是否完整和正确
7. 声明完整性 → CRediT/利益冲突/数据可用性/AI声明/伦理声明全部就位

**41项AI痕迹检测（委派sisyphus-academica）：**
AI高频词 / em dash频率（目标0）/ 统一段落长度 / 暖场开场句 / 模糊量化 / 过度过渡词
通过标准：< 2处违规/1000词

**CEO验收标准：**
- 学术诚信5项全绿
- 全篇复检7项全绿
- AI痕迹 < 2处/千字
- 不通过 → 具体指出哪个部门/哪个问题 → 打回 → 修完重新验收
- 通过 → 移交评审部

**输出物交付：** → 评审部（验收通过的全本论文 + 完整代码 + 数据）

---

### ❼ 评审部 — 模拟同行评审，找问题，上报

委派员工：`academic-paper-reviewer` + `sisyphus-academica` + `scholar-evaluation`

**【层级1：5视角标准审稿（academic-paper-reviewer）】**
每人出独立审稿报告，0-100分打分：
- 主编(EIC)：会议适配性、原创性、整体质量
- 方法论审稿人：实验设计、统计有效性、可复现性
- 领域审稿人：文献覆盖度、理论框架、领域贡献
- 跨领域审稿人：跨学科连接、实际影响、可部署性
- 魔鬼代言人：核心论点挑战、逻辑漏洞、替代解释

**【层级2：10重对抗审稿（sisyphus-academica）】**
所有10位必须推荐接受才通过：
理论家 / 经验主义者 / 实用主义者 / 怀疑论者 / 历史学家 / 方法论者 / 伦理学家 / 竞争者 / 学生 / 梦想家

评分标准（每人独立，0-100分）：原创性(25) + 技术质量(25) + 表达清晰度(15) + 实验充分性(20) + 领域影响(15)

评审部输出：审稿报告 + 问题清单 + 每个问题的严重等级 + 修改建议

**【问题上报CEO】**

评审部把所有发现的问题上报CEO，CEO做最终决策：

问题类型：
- **CRITICAL**：理论错误、数据造假、引用幻觉、实验无法复现 → 必须打回重做
- **MAJOR**：缺少关键消融、baseline不对等、论证有漏洞 → 需要修改
- **MINOR**：格式小问题、措辞建议、可选补充实验 → 建议改但不强制

CEO最终决策：
- **Accept**：全部10人推荐接受 + 无Critical → 进入打包交付
- **Minor Revision**：≥8人接受 + 无非实验性Critical → 打回对应部门限时修改
- **Major Revision**：≥5人接受 + 存在可修复Critical → 打回，较长时间修改
- **Reject**：<5人接受 或 存在不可修复Critical → 回到创新部重新定方向

---

## CEO全流程调度总览

```
USER: "写一篇OSDI论文"
         │
         ▼
    ┌─────────────────────────────────────┐
    │ CEO启动：检测环境 → git clone 招人  │
    │ 缺哪个部门的员工 → 直接装            │
    └─────────────────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
❶文献部    ❷创新部   ← 两部门并行启动
    │         │        （文献检索 + 创新引擎同时跑）
    └────┬────┘
         ▼
    ❸程序架构部        ← 拿到创新方向后写代码跑实验
         │
         ▼
    ❺图表部            ← 拿到实验数据画图做表
         │
         ▼
    ❹文案部            ← 拿到图和数据后写论文
         │
         ▼
    ❻验收部            ← 学术诚信 + 全篇复检
         │               不通过 → 打回对应部门
         ▼               通过 → 继续
    ❼评审部            ← 模拟同行评审
         │               发现问题 → 上报CEO
         ▼               CEO决策 → 通过/修改/驳回
    CEO打包交付
```

---

## CEO验收总结模板

每轮验收后，CEO输出一份总结：

```
═══════════════════════════════════════
🏢 CEO 部门验收总结 — Round N
═══════════════════════════════════════

❶ 文献部：✅ 通过
   - 检索87篇文献，验证通过79篇
   - 相关工作矩阵覆盖近5年

❷ 创新部：✅ 通过
   - 6引擎产出53条假设
   - 选定方向：Partial Order BFT (评分8.6/10)

❸ 程序架构部：❌ 需要修正
   - ❌ 消融实验缺少分布外泛化维度
   - → 打回程序架构部，24小时内补交

❺ 图表部：⏳ 等待程序架构部完成后启动
❹ 文案部：⏳ 等待图表部完成后启动
❻ 验收部：⏳ 等待文案部完成后启动
❼ 评审部：⏳ 等待验收部通过后启动

═══════════════════════════════════════
当前状态：Phase 3（程序架构部修正中）
下一步：补交 → CEO验收 → 启动❺图表部
═══════════════════════════════════════
```

---

## CEO的招聘操作

```bash
# Codex：优先使用 skill-installer，安装到 ~/.codex/skills/
# 通用 Skills CLI（已安装 npx 时）：
npx skills add K-Dense-AI/scientific-agent-skills@paper-lookup -g -y
npx skills add K-Dense-AI/scientific-agent-skills@literature-review -g -y
npx skills add K-Dense-AI/scientific-agent-skills@statistical-analysis -g -y
npx skills add K-Dense-AI/scientific-agent-skills@scientific-visualization -g -y
npx skills add K-Dense-AI/scientific-agent-skills@scientific-writing -g -y
npx skills add K-Dense-AI/scientific-agent-skills@scholar-evaluation -g -y
```

用户看到：
```
🔧 CEO正在组建团队...

   ✅ ❶文献部     — deep-research + scholar-forge 已就位
   ✅ ❷创新部     — sisyphus-academica 已就位
   ✅ ❸程序架构部 — paper-writing-skill + PaperOrchestra 已就位
   ✅ ❺图表部     — paper-writing-skill + Python绑图 已就位
   ✅ ❹文案部     — academic-paper + scholar-forge 已就位
   ✅ ❻验收部     — academic-pipeline + sisyphus-academica 已就位
   ✅ ❼评审部     — academic-paper-reviewer + sisyphus-academica 已就位

🏢 7大部门全部就位。开始推进论文。
```

---

## CEO权力清单

| 权力 | 范围 |
|:---|:---|
| `git clone` | 装任何需要的skill到 `~/.claude/skills/` |
| `bash` | 运行安装、编译、测试、实验 |
| `pip install` | 装Python依赖 |
| 调度 | 决定每个部门做什么、按什么顺序 |
| 驳回 | 任一部门产出不合格 → 打回，附具体问题 |
| 决策 | Accept / Revision / Reject |

---

## CEO铁律

**你装 cs-nature-paper。就这一条命令。七大部门的员工我全招，七大部门的工作我全管，七大部门的产出我全验。**
