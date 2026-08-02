# CS Nature Paper — Usage Examples

Real-world examples demonstrating each mode with actual CS paper scenarios.

---

## Mode 1: `ideate` — Innovation Brainstorming

```
User: 帮我想创新点，我的方向是分布式系统容错，特别关注拜占庭容错协议的性能优化

AI (Phase 0 — IDEATION):

🔍 领域扫描中...

识别到的基线假设（将被逆向引擎挑战）：
1. "BFT协议必须经过3f+1个节点才能保证安全性" (PBFT, 1999)
2. "视图切换(view change)是BFT协议性能的主要瓶颈"
3. "speculative execution可以但会牺牲安全性"
4. "跨地域部署下BFT延迟不可避免"

🧬 6大创新引擎输出:

[引擎1: The Contrarian]
→ 反向假设1: "2f+1个节点足以保证安全性，如果我们在应用层增加可验证延迟证明"
→ 反向假设2: "view change不是瓶颈——实际上是leader选举的消息复杂度是瓶颈"
→ 评分: 新颖性8, 可行性7, 影响力9

[引擎2: The Cross-Pollinator]
→ 从数据库领域导入: "MVCC(多版本并发控制)可以消除BFT中的锁竞争"
→ 从控制理论导入: "将BFT共识建模为反馈控制系统，动态调整超时参数"
→ 评分: 新颖性9, 可行性5, 影响力7

[引擎3: The Assumption Excavator]
→ 发现SOTA假设: "所有拜占庭节点行为模式相同" → 现实中攻击者有不同策略
→ 评分: 新颖性7, 可行性8, 影响力8

[引擎6: The Heretic — 皇冠输出]
→ 最终假设: "大部分BFT场景不需要全序(total order)——偏序(partial order)+冲突解决
  在实际工作负载中可以达到99.7%的吞吐量，同时将延迟降低60%"
→ 评分: 新颖性9, 可行性8, 影响力10, 可证伪性9, 技术深度8, 泛化性7, 时效性9
→ 总分: 8.6/10 ✅ 通过阈值

📊 创新评分卡:
1. Partial Order BFT (Heretic) — 8.6/10 ⭐推荐
2. 2f+1 Safety with VDP (Contrarian) — 8.0/10
3. Adaptive Timeout via Control Theory (Cross-Pollinator) — 7.3/10

建议优先推进 #1。是否进入实验设计阶段？
```

---

## Mode 2: `experiment-design` — Experiment Design

```
User: 我的假设是用partial order替代total order在BFT中，帮我设计实验

AI (Phase 1 — EXPERIMENT DESIGN):

📐 基准选择协议:

识别的benchmark:
1. YCSB (Yahoo Cloud Serving Benchmark) — ✅ 广泛使用，2年内活跃
2. SmallBank — ✅ OLTP工作负载标准
3. TPC-C — ✅ 但注意: license限制，不能用完整版 → 用TPC-C-like变体
4. ETCD benchmark — ✅ 分布式一致性系统实际场景
5. PBFT microbenchmark — ⚠️ 已饱和，SOTA接近理论上限 → 排除

📊 实验矩阵:

实验1: 吞吐量 vs 冲突率
- 变量: 冲突率 0%, 1%, 5%, 10%, 20%
- 对比: PBFT, HotStuff, Narwhal, 你的方法
- 硬件: AWS c5.4xlarge × 4节点
- 运行: 每配置5次, report mean ± std

实验2: 延迟分布 (CDF)
- 变量: 负载 50%, 80%, 95% of saturation
- 指标: p50, p95, p99, p99.9 latency
- 需要: 时间同步精度 ≥ 100μs

实验3: 故障恢复 (拜占庭容错场景)
- 注入: 1/4, 2/4 节点拜占庭行为
- 拜占庭类型: crash、slow、equivocation
- 指标: recovery time, throughput degradation during attack

消融实验:
□ 组件消融: 去掉conflict resolver → 测正确性降低
□ Partial order窗口大小: 100, 500, 1000, 5000
□ 超参数: 批大小 1-1024, 超时间隔 10ms-500ms
□ 规模: 4, 7, 10, 16, 31节点
□ 跨地域: us-east-1, us-west-2, eu-west-1, ap-southeast-1

📋 可复现checklist: [所有项已规划]
□ Docker: Ubuntu 22.04 + Rust 1.80 + Tokio runtime
□ 代码仓库结构: /src (核心协议), /bench (benchmark), /scripts (部署)
□ README: 包含从头运行到重新生成论文图表的所有步骤

是否批准实验方案并进入文献调研？
```

---

## Mode 5: `review` — 15-Perspective Review

```
User: 帮我审这篇刚写完的KV Cache压缩论文

AI (Phase 5 — REVIEW):

📋 Paper profile detected:
- Domain: ML Systems / Efficient Inference
- Type: Empirical ML paper
- Target: ICML 2026

=== LAYER 1: STANDARD REVIEW (5 Perspectives) ===

[EIC Review]
Journal Fit: 8/10 — Strong ICML fit, practical impact on LLM serving
Originality: 7/10 — Compression via low-rank is known; your adaptive
  rank selection is novel
Overall Quality: 7/10 — Solid experiments, but missing some ablations

[Methodologist Review]
Statistical Validity: Pass
- All experiments run 5 times, mean ± std reported ✅
- Missing: statistical significance test between your method and
  the second-best baseline on the primary metric ❌
Reproducibility: Conditional Pass
- Code provided ✅
- Docker environment provided ✅
- Missing: random seeds not explicitly fixed in config ❌

[Domain Reviewer]
Literature Coverage: 7/10
- Good coverage of KV cache compression methods
- Missing: Scissorhands (OSDI'24), H2O (NeurIPS'23)
- Theoretical grounding of rank selection could be stronger

=== LAYER 2: ADVERSARIAL REVIEW (10 Perspectives) ===

[The Skeptic]
Q1: "How do you know the improvement isn't just from better
    hyperparameter tuning of the baseline methods?"
Q2: "Did you try simply reducing the number of KV heads as a
    stronger baseline?"
→ Responses needed

[The Historian]
Q: "Low-rank approximation for KV cache was explored in
    'Efficient Transformers: A Survey' (Tay et al., 2020) —
    what is fundamentally different about your approach?"
→ You need to cite and distinguish from this line of work

[The Competitor]
"I would attack your experiment design on:
 1. You only test on Llama-family models — what about
    non-RoPE architectures?
 2. Your longest sequence is 32K — current SOTA models
    handle 128K+. Why no long-context evaluation?"
→ This is a real weakness in the current draft

[... all 10 reviewers produce independent reports ...]

=== EDITORIAL DECISION ===
10 adversarial reviewers: 7 Accept, 2 Minor concerns, 1 Major concern
Decision: MINOR REVISION
- Must fix: The Competitor's long-context concern, add statistical tests
- Should fix: The Historian's literature gap
- Nice to have: Test on non-Llama architectures

Proceed to Phase 6 (REVISION)?
```

---

## Mode 7: `polish` — De-AI-ify and Compress

```
User: 帮我润色这篇论文，要去掉AI写作痕迹，目标10页

AI (Phase 7 — POLISH):

🔍 AI痕迹扫描结果:

检测到的AI模式:
1. "delve into" → 3 occurrences (Line 45, 112, 203) ❌
2. em dash → 7 occurrences ❌ (目标: 0)
3. Throat-clearing: "In this section, we discuss..." → Line 78 ❌
4. Uniform paragraph length: Section 3 has 6 paragraphs of 4-5 sentences each ⚠️
5. 模糊量化: "significantly outperforms" → Line 156 (无具体数字) ❌
6. "it is important to note" → Line 89, 234 ❌
总计: 14 violations / 8500 words = 1.65/千字 ❌ (目标 <2, 但应优化)

📏 压缩操作 (当前11.2页 → 目标10页):

1. 消除冗余: Section 2.1 和 Section 5.2 重复解释KV cache机制 → -0.3p
2. 压缩Introduction: 3-paragraph buildup → 1-paragraph with immediate contribution → -0.4p
3. Related Work: 12段 → 8段，批量引用 → -0.3p
4. 去Section开场白: 7处 "in this section we" → -0.1p
5. 合并图表: Figure 3+4 → 复合子图 → -0.2p
6. Evidence束: 多处逐条列举 → 多子句并句 → -0.1p
7. 附录迁移: 实现细节3段 + 额外消融2表 → Appendix → -0.3p
预估压缩后: 9.5页 ✅

📝 润色示例:

Before:
"It is important to note that our method significantly outperforms
existing approaches, demonstrating the crucial role of adaptive
rank selection in KV cache compression."

After:
"Our method achieves 23.7% higher throughput than the best prior
method (H2O) at the same memory budget, and matches uncompressed
quality within 0.3% on MMLU. Adaptive rank selection accounts for
18.3 of the 23.7 percentage points."

是否应用所有润色和压缩修改？
```

---

## Mode 8: `camera-ready` — Final Submission

```
User: 准备NeurIPS终稿提交

AI (Phase 8 — FINALIZE):

📋 终检清单:

✅ LaTeX: neurips_2026.sty, 无编译错误, 1个warning (overfull hbox in Table 2)
✅ 引用: 所有45条引用在refs.bib中有完整条目
✅ 图表: Figure 1-6 + Table 1-3, 全在正文中被引用
✅ 页数: 9.8/10页 (含参考文献)
✅ 匿名: 双盲, 所有作者信息已移除, acknowledgments移至最终版
✅ 补充材料: supplement.pdf (5页), 已上传至匿名链接
✅ AI声明: 按NeurIPS 2026政策填写
✅ CRediT: 作者贡献声明已添加
✅ 利益冲突: 声明已添加
✅ 数据可用性: "All benchmarks used are publicly available..."

⚠️ Overfull hbox in Table 2 — 建议手动调整列宽或拆分长单元格

📦 提交包:
├── paper.tex          (主文件)
├── refs.bib           (参考文献)
├── neurips_2026.sty   (模板)
├── figs/              (6个PDF图)
├── supplement.pdf     (补充材料)
└── code/
    ├── README.md      (审稿人可读的复现指南)
    ├── environment.yml
    ├── src/           (核心代码)
    └── scripts/       (复现论文所有图表的脚本)

提交包已准备好。你可以直接从Overleaf或直接上传至OpenReview。
```
