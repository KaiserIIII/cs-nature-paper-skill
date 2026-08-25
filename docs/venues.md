# Live venue-verification protocol

Venue rules change. Do not encode remembered page limits, templates, review
models, AI policies, or artifact requirements as permanent truth in this skill.

## Source order

Verify each requirement from the most authoritative current source available:

1. the current journal instructions or conference call for papers;
2. the current track-specific page and template instructions;
3. the publisher's ethics, AI, data, and artifact policies;
4. the live submission system when it exposes additional required fields;
5. an official FAQ or chairs' clarification.

Use third-party summaries only to locate a primary source, not as final evidence.
Record the URL, page title, relevant rule, track, publication year or volume,
and UTC verification date.

## Requirements card

Create a venue card containing at least:

```yaml
venue: ""
track_or_article_type: ""
cycle_or_volume: ""
verified_utc: ""
primary_sources: []
template_and_version: ""
page_or_word_rules: ""
reference_and_appendix_rules: ""
review_model_and_anonymity: ""
artifact_or_data_policy: ""
ethics_and_ai_disclosure: ""
required_declarations: []
submission_fields: []
open_questions: []
```

Where official pages disagree, report the conflict and ask the author to confirm
with the venue. Do not silently choose the more convenient interpretation.

## Preflight evidence

A `submission` gate passes only after:

- the live venue sources and verification date are stored in the research contract;
- the compiled manuscript uses the verified template and article type;
- page or word counts use the venue's stated inclusion rules;
- anonymity and supplemental links have been checked in the rendered PDF;
- declarations, conflicts, ethics, data/code availability, and AI disclosure are complete where applicable;
- unresolved questions are assigned to the author rather than guessed;
- no upload, release, email, or submission occurs without explicit authorization.

The card is provenance for a particular submission attempt, not a reusable
global table. Re-verify it before resubmission or after a deadline update.
