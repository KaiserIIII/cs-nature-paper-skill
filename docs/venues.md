# Venue Configuration Guide · 顶会配置指南

Auto-detected venue-specific settings for 20+ top CS conferences and journals.

---

## Machine Learning / AI

| Venue | Template | Pages | Blind | AI Disclosure | Key Style Notes |
|:---|:---|:---|:---|:---|:---|
| **NeurIPS** | `neurips_2026.sty` | 9 (main) + unlimited appendix | Double-blind | [Required](https://neurips.cc/Conferences/2026/EthicsGuidelines) | No page numbers; \texttt{neurips_2026} option `final` for camera-ready |
| **ICML** | `icml2026.sty` | 8 (main) + unlimited appendix | Double-blind | Required | Anonymous \texttt{\\icmlauthor} commands in draft mode |
| **ICLR** | `iclr2026_conference.sty` | 8 (main) + unlimited appendix | Double-blind | Required | Use \texttt{\\usepackage[final]{iclr2026_conference}} for camera-ready |
| **CVPR** | `cvpr.sty` | 8 (excluding references) | Blind until acceptance | Recommended | IEEE-style; \texttt{\\thecvpr} rule for page limits |
| **ICCV** | `iccv.sty` | 8 (excluding references) | Blind until acceptance | Recommended | Same as CVPR template |
| **AAAI** | `aaai24.sty` | 7 (+1 for references) | Double-blind | Allowed with disclosure | Must use AAAI Press format |
| **ACL/EMNLP** | `acl.sty` | 8 (+unlimited references/appendix) | Anonymized for review | Recommended | \texttt{\\aclfinalcopy} for camera-ready |
| **JMLR** | `jmlr2e.sty` | Unlimited (journal) | N/A | Recommended | Two-column workshop format available |

---

## Systems

| Venue | Template | Pages | Blind | Key Style Notes |
|:---|:---|:---|:---|:---|
| **OSDI** | `osdi.cls` | 12 (excluding references) | Single-blind | USENIX format; 10pt, two-column; author names required on submission |
| **SOSP** | `acmart.cls` (sigconf) | 12 (excluding references) | Single-blind | ACM format; 9pt; permission/copyright block required |
| **NSDI** | `nsdi.cls` | 12 (excluding references) | Single-blind | USENIX format; same as OSDI |
| **ATC** | `usenix.sty` | 12 (excluding references) | Single-blind | USENIX format; anonymization optional but common |
| **EuroSys** | `acmart.cls` (sigconf) | 12 (excluding references) | Single-blind | ACM format |
| **ASPLOS** | `acmart.cls` (sigconf) | 11 (excluding references) | Single-blind | ACM format |
| **FAST** | `usenix.sty` | 12 (excluding references) | Single-blind | USENIX format |
| **ISCA/MICRO** | `acmart.cls` (sigconf) | 11 | Single-blind | ACM format; IEEE also accepted at MICRO |

### Systems Paper Writing Tips
- Evaluation section: 30-40% of paper length — the most important section
- Start with end-to-end performance, then drill into microbenchmarks
- Always report tail latency (p99, p99.9), not just average
- Implementation section: ~1-1.5 pages, focus on surprising/non-obvious choices
- Systems papers benefit from architecture diagrams with specific component names

---

## Theory / Algorithms

| Venue | Template | Pages | Blind | Key Style Notes |
|:---|:---|:---|:---|:---|
| **STOC** | `acmart.cls` | 15 (excluding references) | Single-blind | ACM format |
| **FOCS** | `ieeetran.cls` | 10 (excluding references) | Single-blind | IEEE format |
| **SODA** | `siamart.cls` | 10 | Single-blind | SIAM format; requires SIAM copyright |
| **ITCS** | `lipics.cls` | 15 | Single-blind | LIPIcs format |
| **COLT** | `jmlr.cls` | Unlimited (proceedings) | Single-blind | PMLR format |
| **ICALP** | `lipics.cls` | 15 | Single-blind | LIPIcs format |

### Theory Paper Writing Tips
- Theorem statements before proof sketches
- Clearly distinguish between "proof sketch" and "full proof" (latter in appendix)
- Proof structure: provide intuition paragraph before formal notation
- Notation table (cheat sheet) highly recommended for papers with heavy notation
- Use `amsthm`, `algorithm2e` or `algorithmicx`, and `cleveref`

---

## Security / Privacy

| Venue | Template | Pages | Blind | Key Style Notes |
|:---|:---|:---|:---|:---|
| **IEEE S&P** | `ieeetran.cls` | 13 (excluding references) | Single-blind | IEEE format |
| **CCS** | `acmart.cls` (sigconf) | 12 (excluding references) | Double-blind | ACM format |
| **USENIX Security** | `usenix.sty` | 13 (excluding references) | Single-blind | USENIX format |
| **NDSS** | `ndss.cls` | 13 (excluding references) | Double-blind | Custom NDSS format; must use their template |
| **CRYPTO / EUROCRYPT** | `iacrtrans.cls` | 30 (excluding references, LNCS) | Single-blind | IACR format |

### Security Paper Writing Tips
- Threat model must appear early (usually Section 2 or 3) — reviewers will reject if unclear
- Always state what your defense does NOT protect against
- Responsible disclosure: if you found real-world vulnerabilities, document disclosure timeline
- Attack papers: provide proof-of-concept code in supplementary material
- Defense papers: provide performance overhead at realistic deployment scales

---

## Networking

| Venue | Template | Pages | Blind | Key Style Notes |
|:---|:---|:---|:---|:---|
| **SIGCOMM** | `acmart.cls` (sigconf) | 12 (excluding references) | Single-blind | ACM format |
| **NSDI** | `nsdi.cls` | 12 (excluding references) | Single-blind | USENIX format |
| **CoNEXT** | `acmart.cls` (sigconf) | 10 (excluding references) | Single-blind | ACM format |
| **IMC** | `acmart.cls` (sigconf) | 10 (excluding references) | Single-blind | ACM format |
| **MobiCom** | `acmart.cls` (sigconf) | 12 (excluding references) | Single-blind | ACM format |

### Networking Paper Writing Tips
- "One table that explains everything" — a concise comparison table of your system vs. all baselines
- Deployment context matters: "tested on X campus network with Y real users" > "simulated"
- Time-series plots are essential for networking papers (throughput over time, latency over time)
- Always discuss packet-level behavior, not just application-level metrics

---

## Programming Languages / Compilers

| Venue | Template | Pages | Blind | Key Style Notes |
|:---|:---|:---|:---|:---|
| **PLDI** | `acmart.cls` (sigplan) | 12 (excluding references/appendix) | Single-blind | ACM SIGPLAN format |
| **POPL** | `acmart.cls` | 25 (excluding references) | Single-blind | ACM format |
| **OOPSLA** | `acmart.cls` (sigplan) | 25 (excluding references) | Single-blind | ACM SIGPLAN format |
| **ICFP** | `acmart.cls` (sigplan) | 12 (excluding references) | Single-blind | ACM SIGPLAN format |
| **CGO** | `acmart.cls` (sigplan) | 11 | Single-blind | ACM SIGPLAN format |
| **ASPLOS** | `acmart.cls` (sigconf) | 11 | Single-blind | ACM format |

### PL Paper Writing Tips
- Formal semantics: use inference rule notation consistently
- "PL papers are read with a pen" — provide enough detail to verify claims by hand
- Artifact evaluation is expected at top PL venues (POPL, PLDI, OOPSLA)
- Provide mechanized proofs (Coq/Isabelle/Lean) as supplementary material
- List all undefined behaviors your approach eliminates or catches

---

## Database

| Venue | Template | Pages | Blind | Key Style Notes |
|:---|:---|:---|:---|:---|
| **SIGMOD** | `acmart.cls` (sigconf) | 12 (excluding references) | Single-blind | ACM format |
| **VLDB** | `vldb.cls` | 12 (excluding references) | Single-blind | PVLDB format |
| **ICDE** | `ieeetran.cls` | 12 (excluding references) | Single-blind | IEEE format |
| **CIDR** | `cidr.cls` | 6 (vision/talk proposals) | Single-blind | Very different format — concise, visionary |

### Database Paper Writing Tips
- Always test on at least 3 different datasets/workloads
- Cold cache vs. warm cache performance
- Report both latency and throughput, ideally with Pareto curves
- Memory budget fairness: compare at equal memory budgets

---

## HCI

| Venue | Template | Pages | Blind | Key Style Notes |
|:---|:---|:---|:---|:---|
| **CHI** | `acmart.cls` (sigchi) | 10 (excluding references) | Anonymized | ACM SIGCHI format |
| **UIST** | `acmart.cls` (sigchi) | 10 (excluding references) | Anonymized | ACM SIGCHI format |
| **CSCW** | `acmart.cls` (sigchi) | 10 (excluding references) | Anonymized | ACM SIGCHI format |

### HCI Paper Writing Tips
- Method section needs: participants (N=?, demographics), apparatus, procedure, measures
- Report IRB approval or exemption
- Statistical reporting: effect sizes, not just p-values
- Qualitative data: thematic analysis with representative quotes
- Study materials in appendix (survey questions, interview protocols)

---

## Vision / Graphics

| Venue | Template | Pages | Blind | Key Style Notes |
|:---|:---|:---|:---|:---|
| **SIGGRAPH** | `acmart.cls` | 8-10 (excluding references) | Double-blind | ACM format; video figure strongly recommended |
| **SIGGRAPH Asia** | `acmart.cls` | 8-10 (excluding references) | Double-blind | Same as SIGGRAPH |
| **CVPR / ICCV / ECCV** | See ML/AI section above | | | |

### Vision/Graphics Paper Writing Tips
- Visual results must be on the first page (teaser figure)
- Provide zoom-in insets on figures to show detail differences
- User studies: validate perceptual quality, not just metrics
- Video figure is often the deciding factor at SIGGRAPH
- For generative models: report diversity metrics, not just quality

---

## General Guidelines (All Venues)

1. **Always check the current year's Call for Papers** — rules change annually.
2. **Page limits are hard limits** — "excluding references" means exactly that; don't try to squeeze text into the reference list.
3. **AI disclosure is becoming mandatory everywhere** — even if not required, disclose AI tool usage. Most venues follow [ACL's AI policy](https://www.aclweb.org/adminwiki/index.php/ACL_Policy_on_Publication_Ethics) or similar.
4. **Artifact evaluation** — if your venue offers it, submit. AE badges (Available, Functional, Reproduced) signal credibility.
5. **Rebuttal periods** — most ML venues now have an author response period (typically 5-7 days). Plan for it before submission.
