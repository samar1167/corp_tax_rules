# Delivery Todo

## Workflow Hardening
- Add module supersede, review, and approval APIs so future module revisions can be promoted entirely from the UI.
- Add decision-table lifecycle transitions similar to rule and primitive transitions.
- Add clearer activation diagnostics that explain which dependency blocks activation.
- Add comparison views for rule, primitive, and module versions before approval.
- Add change-set detail screens with lifecycle history and activation snapshots.
- Add activation history and superseded-vs-active lineage views across artifacts.
- Add artifact diff views so reviewers can see what changed before approval.
- Add governance-oriented “what changed” summaries across a bundled promotion path.

## Runtime Expansion
- Extend ITR computation beyond the current new-regime slice.
- Add deduction, filing timeline, verification, and penalty flows to the ITR module.
- Start the first corporate tax vertical slice with entity classification and rate determination.
- Add governance-layer cross-module rule execution and consolidated compliance status.
- Define a stricter JSON rule schema and decision-table schema before widening authoring volume.
- Build import-assisted authoring from markdown and structured JSON into draft artifacts.
- Build a more generic rule and decision interpreter so less runtime behavior stays hand-coded.
- Add deduction eligibility primitives and regime-sensitive deduction logic for ITR.
- Add filing timeline, belated return, revised return, and verification workflows.
- Add late fee, interest, surcharge, and broader compliance outcome computations.
- Expand tax computation with old-regime slabs, age-based slabs, and special-rate interactions.

## Product Surface
- Turn the current workflow cockpit into role-based screens for tax author, reviewer, and activator.
- Add inline traces for rule, primitive, and decision-table outcomes directly on the UI.
- Add import flows from markdown or structured seed files so domain experts can load content faster.
- Add audit search and replay tools from the workflow screen.
- Add batch promotion so multiple rules can be rolled into one primitive/module/change-set journey together.
- Add guided multi-artifact selection and comparison views before approval.
- Add richer artifact detail screens for change sets and activation history.
- Add decision-table visual row editor to reduce raw JSON editing in the browser.

## Quality Gates
- Add automated tests for lifecycle transitions, activation safety, and ITR regressions.
- Add fixture packs for representative taxpayers and filing scenarios.
- Add precompiled active-version indexes for faster runtime loading.
