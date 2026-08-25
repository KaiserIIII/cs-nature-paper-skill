# Literature and innovation departments

Use this reference when positioning a study, defining novelty, building theory,
or updating related work. Literature discovery and contribution design are
coupled, but the role that proposes a gap must not be the only role that checks
whether prior work already fills it.

## Literature department

### Capability contract

The department needs three distinct capabilities:

1. **Discovery:** reproducible queries over appropriate scholarly databases,
   proceedings, citation graphs, standards, and official technical sources.
2. **Identity verification:** title/authors/venue/year/DOI or stable identifier,
   version-of-record/preprint relationship, retractions/corrections, and access
   status.
3. **Claim-support verification:** inspect the relevant source region and label
   whether it supports, contradicts, qualifies, or does not address the paper's
   nearby claim.

Bibliographic existence is not claim support. Search-engine snippets, LLM
summaries, citation counts, and database metadata cannot replace reading the
relevant primary text.

### Search protocol

Record:

- review question, constructs, aliases, exclusions, time window, and venue or
  database scope;
- exact queries, filters, date, API/tool version, result limits, and pagination;
- deduplication and version-merging rules;
- screening criteria and exclusion reasons;
- inaccessible full text and likely language/indexing bias;
- backward/forward citation chasing and when it stops;
- corpus snapshot plus identifiers so another reader can reconstruct it.

Use three complementary scans where appropriate:

- **foundational/theory scan:** definitions, canonical mechanisms, and historic
  claims;
- **closest-work scan:** papers with the nearest construct, method, artifact,
  population, and claim;
- **recent/contradictory scan:** current results, negative evidence, corrections,
  and alternative explanations.

For software engineering, include venue proceedings and community standards;
for fast-moving ML/systems/security areas, distinguish preprints from archival
versions and record the search cutoff.

### Claim-to-source matrix

For each source retain:

| Source ID | Verified identity | Relevant source region | Paper claim | Relation | Scope mismatch | Confidence |
|---|---|---|---|---|---|---|

`Relation` is `SUPPORTS`, `CONTRADICTS`, `QUALIFIES`, or `BACKGROUND`. Quote only
short, necessary excerpts and respect source limits. If only an abstract is
available, say so and reduce confidence.

### Stop condition

Stop when registered databases and citation paths are executed, new searches
yield little decision-relevant evidence, closest work is explicitly compared,
and every load-bearing prior-work claim has an inspected anchor. Do not claim a
systematic review unless its protocol and reporting actually meet that standard.

## Innovation department

### Capability contract

The department needs:

- **gap and mechanism construction;**
- **falsifier and alternative generation;**
- **closest-competitor/historical challenge;**
- **feasibility and evidence-fit screening.**

Brainstorming volume is not novelty. Wild or cross-domain ideas are discovery
tools, not contributions until checked against literature, evidence, resources,
ethics, and falsifiability.

### Build novelty from contrasts

Write the closest-work contrast before the contribution list:

| Dimension | Closest work establishes | This study tests/builds | Evidence required | Result that erases novelty |
|---|---|---|---|---|

Use a novelty ladder:

1. new dataset/tool only;
2. known method in a new setting;
3. new empirical regularity with bounded scope;
4. mechanism discrimination or theory extension;
5. capability that enables a previously infeasible scientific/engineering task;
6. result that changes a field-level assumption or decision.

Lower rungs can still be publishable if important and rigorously validated.
Never inflate them by saying familiar components have not previously appeared
in one checklist.

### Mechanism and proposition contract

For every central proposition state:

- units and scope;
- causal/associational/descriptive role;
- mechanism or engineering rationale;
- observable prediction;
- rival explanation;
- differentiating analysis or experiment;
- outcome that weakens the preferred account;
- claim wording under positive, null, mixed, and failed results.

The innovation employee cannot redesign the hypothesis after seeing results
without a dated amendment and exploratory label.

### Adversarial innovation review

Select targeted challenges rather than invoking every persona:

- **competitor:** has the closest work already made the claimed contribution?
- **historian:** is the mechanism or method older than the current vocabulary?
- **methodologist:** can the design distinguish the proposed mechanism?
- **pragmatist:** what real decision changes, for whom, and under what cost?
- **contrarian:** what pattern would support the reverse interpretation?
- **ethicist/security reviewer:** could the capability create material harm or
  distort a population through missing data or access?

The final contribution must survive the strongest relevant challenge or be
narrowed. Do not aggregate persona scores into a novelty probability.

### Stop condition

Innovation passes when the gap is source-backed, the mechanism yields a
testable prediction, rivals are represented fairly, planned evidence can change
the interpretation, and the contribution remains meaningful under a bounded
claim. If not, revisit the research question before enlarging the experiment.
