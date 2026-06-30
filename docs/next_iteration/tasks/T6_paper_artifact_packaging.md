# T6: Paper Artifact Packaging

Suggested agent: Scribe

## Objective

Prepare the project for paper writing and artifact review after real benchmark results exist.

## Dependencies

- Requires T4.
- Should incorporate T5 and T7 if available.

## Required Reads

- `docs/publication_gap_assessment.md`
- `docs/deliverables/09/master_research_outline.md`
- `docs/deliverables/09/claim_evidence_matrix.md`
- T3/T4/T5/T7 reports

## Required Work

1. Update the claim-evidence matrix:

- accepted claims
- unsupported claims
- negative results
- limitations

2. Draft paper structure:

- title
- abstract skeleton
- contributions
- method section outline
- experiment setup
- result table index
- limitation section

3. Create reproducibility instructions:

- environment setup
- benchmark acquisition
- run commands
- expected output files
- secret handling

4. Prepare artifact checklist:

- scripts
- manifests
- configs
- summaries
- tests

## Deliverables

- `docs/paper_outline.md`
- `docs/artifact_reproducibility.md`
- updated `docs/deliverables/09/claim_evidence_matrix.md`
- `docs/next_iteration/reports/T6_paper_artifact_packaging.md`

## Acceptance Criteria

- Every claim names its evidence source.
- Proxy/toy results are clearly separated from end-task results.
- The paper outline honestly states compute and benchmark limitations.

## Failure Modes

- Writing a persuasive story that outruns the evidence.
- Hiding negative results.
- Omitting exact model/version/budget settings.
