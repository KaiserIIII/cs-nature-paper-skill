# Figure department

Use this reference for quantitative figures, conceptual diagrams, scientific
images, captions, alt text, or journal export. A publication figure is a
compact scientific argument backed by source data, not decoration.

## Required roles

- **Semantics planner:** identifies the question, comparison, estimand,
  denominator, uncertainty, missingness, and intended reading order.
- **Renderer:** implements the figure deterministically from declared source
  data and transformation code.
- **Independent auditor:** checks the source-to-mark mapping, misleading
  encodings, accessibility, final-size legibility, and export integrity.
- **Domain imaging specialist, when needed:** handles microscopy, 3D fields,
  molecular dynamics, topology, geospatial, or other modality-specific data.

A general charting skill must not impersonate a domain imaging specialist, and
a specialist visualizer must not decide the study's estimand.

## Seven-gate figure workflow

### 1. Figure contract

For each planned figure record:

- scientific question and claim ID;
- source files/tables and hashes;
- unit of observation, denominator, grouping, ordering, and transformations;
- uncertainty definition and repeated-measure/dependence structure;
- missing, excluded, censored, and failed observations;
- panels, intended comparison, caption claim, and downstream manuscript use.

If the figure cannot be tied to a claim, RQ, mechanism, or named threat, demote
or remove it.

### 2. Semantic design

Choose the smallest truthful encoding:

- counts/proportions: dots, intervals, bars only when zero and length matter;
- distributions: raw points, ECDF, box/violin with sample size and definition;
- relationships: points/lines with uncertainty and dependence made explicit;
- transitions or joint states: state table, alluvial/flow, or UpSet-like view
  when it clarifies actual combinations;
- model effects: coefficient/marginal-effect plot with reference and interval;
- time: genuine temporal axis, observation windows, and discontinuities;
- mechanisms/workflows: vector diagram that distinguishes measured stages from
  unmeasured downstream outcomes.

Do not select a chart because it looks fashionable. Avoid 3D perspective for
ordinary comparisons, truncated axes that distort magnitude, dual axes without
a defensible mapping, rainbow maps, unlabeled smoothing, hidden denominators,
and aggregations that conceal relevant variation.

### 3. Deterministic rendering

Use project-native plotting code, frozen source tables, explicit styles, and a
headless/reproducible backend. Keep data transformation separate from visual
styling. Record library versions, dimensions, fonts, palette, random seeds, and
export options. Refuse to overwrite a formal figure silently; write a new
version or use an approved deterministic rebuild path.

### 4. Scientific integrity audit

Independently recompute plotted values and compare them with tables/prose.
Inspect units, denominators, error-bar meaning, multiplicity, sample size,
group/order consistency, log scales, normalization, smoothing, excluded data,
and non-nested/exceptional cases. Missingness must be visible or explained.
Images require truthful scale bars, channel/contrast disclosure, and a record
of any crop, registration, denoising, segmentation, or enhancement.

### 5. Accessibility and visual hierarchy

Use redundant encodings such as marker/line style in addition to color. Check
color-vision deficiencies, grayscale, contrast, reading order, panel labels,
legend placement, and jargon. Inspect at final publication size; target at
least 8 pt text unless current venue rules require otherwise. Write concise alt
text that conveys the comparison and pattern without claiming more than the
caption/evidence.

### 6. Export and manifest

Prefer PDF/SVG for vector marks and a high-resolution raster only when the
content requires it. Verify embedded fonts, transparency, clipping, bounding
boxes, physical dimensions, DPI for raster elements, and venue color mode.
Create an export manifest containing source hashes, code/config revision,
software versions, output hashes, dimensions, fonts, palette, and audit date.

### 7. Manuscript integration

Compile the real manuscript, inspect the page at 100% and print-like size, and
check that caption, callout, figure order, labels, numbers, supplement links,
and text claims agree. A standalone PNG preview is not the final audit.

## Upgrading a visually plain paper

Improve information architecture before adding ornament:

1. promote the paper's mechanism to one clear overview diagram;
2. replace repeated isolated charts with a coherent small-multiple or joint
   state view when comparisons share scales;
3. expose uncertainty, raw variation, and exceptional cases;
4. apply a restrained, consistent type/palette/spacing system;
5. reduce redundant legends and decoration;
6. use annotations only for evidence-backed takeaways;
7. move diagnostic complexity to the supplement while preserving audit trails.

Novel styling cannot rescue an undefined construct or weak comparison.

## Tool boundaries

General scientific-visualization skills are preferred for ordinary statistical
figures. Domain packages such as ParaView, napari, VMD/MDAnalysis, or topology
toolkits are specialists for matching data. Image-generation tools may create
clearly disclosed conceptual or decorative artwork when allowed by the venue;
they must never fabricate quantitative marks, experimental images, participants,
or empirical evidence. All load-bearing diagrams should remain editable and
traceable to explicit text/data inputs.
