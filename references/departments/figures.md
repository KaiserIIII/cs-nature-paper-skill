# Figures department contract

- **Mission:** make claim-relevant patterns inspectable without changing the data.
- **Trigger:** a frozen source table or measured artifact exists.
- **Required inputs:** claim/figure contract, source hashes, denominator, uncertainty and missingness rules.
- **Required capabilities:** semantic design, deterministic rendering, independent visual audit.
- **Optional capabilities:** domain imaging specialist, vector/TikZ, accessibility checker.
- **Producer/checker:** renderer and source-to-mark/final-size auditor.
- **Allowed tools:** project-native plotting code and approved vector/image tooling.
- **Forbidden:** invented marks, distorted axes, hidden exclusions, decorative exaggeration, image generation as quantitative evidence.
- **Output contract:** source table, renderer, vector export, caption, alt text, manifest, manuscript anchor.
- **Evidence contract:** every mark maps to a source row/transform; uncertainty and missingness are visible or explained.
- **Handoff:** versioned exports and manifest to writing and validation.
- **Failure:** raster unreadability, inconsistent numbers, inaccessible colors, missing source data, stale renderer.
- **Stop:** final-size figure agrees with source and manuscript and answers a named question.
- **Reopen:** source changes, claim changes, compilation crop, or auditor finds misleading encoding.
- **Student explanation:** a prettier chart cannot make a small or uncertain effect stronger; it can only make the measured evidence clearer.
