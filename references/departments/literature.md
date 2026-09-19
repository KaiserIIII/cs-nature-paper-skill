# Literature department contract

- **Mission:** establish what is known, unknown, closest, and contradictory.
- **Trigger:** a new topic, claim, gap, citation, or prior-art question.
- **Required inputs:** brief, constructs, aliases, scope, search budget.
- **Required capabilities:** discovery, identity verification, claim-support verification.
- **Optional capabilities:** systematic review, domain database specialist, translator.
- **Producer/checker:** separate search/synthesis producer and source checker for load-bearing claims.
- **Allowed tools:** approved web/database connectors, local PDFs, citation parsers.
- **Forbidden:** treating snippets/DOIs as support, invented records, leaking private papers.
- **Output contract:** search protocol, corpus snapshot, literature registry, thematic synthesis, closest-work table.
- **Evidence contract:** stable ID plus inspected section/page/line and relation in the claim-source matrix.
- **Handoff:** version/hash, exclusions, inaccessible sources, uncertainty, next owner (innovation or writing).
- **Failure:** API outage, identity conflict, inaccessible full text, indexing bias, duplicate/version conflict.
- **Stop:** coverage is sufficient for the question and new searches add no decision-changing work.
- **Reopen:** new closest work, correction, contradictory result, or changed scope.
- **Student explanation:** a paper can exist without supporting the sentence you want to cite; identity and support are separate checks.

Retrieval states are `METADATA_ONLY`, `FULLTEXT_RETRIEVED`,
`EXACT_REGION_VERIFIED`, and `UNAVAILABLE`. DOI/title metadata may establish
identity and discovery only. A load-bearing novelty, closest-work distinction,
method, or important factual claim needs materialized full text and an exact
page/section/line region checked by an actor distinct from the inspector.
Otherwise the claim relation is `BACKGROUND_ONLY`/`NOT_VERIFIED`, the literature
gate is conditional, and novelty remains `CONDITIONAL`. Projects that declare
no load-bearing literature claim may receive a documented scoped pass.
