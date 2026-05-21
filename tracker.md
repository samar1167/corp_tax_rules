# Rule Handling System Tracker

## Goal

Build a rules-first tax compliance platform using:

- Django as the application framework
- SQLite as the initial database
- ITR and Corporate Tax as the first domain modules

This tracker is based on:

- `ITR_Rule_System.md`
- `corporate_tax_approach.md`
- `itr_approach.md`

## Core Build Principles

- Rules are the source of truth; code is derived from approved rules.
- Primitives are the atomic, complete, share-nothing rule units.
- Modules are built from primitives, decision tables, and computation functions.
- Governance sits above modules and owns cross-module rules.
- Versioning is additive only; approved items are immutable and superseded, not edited.
- Setup-time validation handles completeness, conflict detection, approval, and activation.
- Runtime should stay simple: load active versions, evaluate, compute, apply consequences, log immutably.

## Initial Scope

- Build the platform foundation first, not form-specific screens first.
- Support one initial persistence layer with SQLite.
- Use Django apps to separate concerns:
  - `core_rules`
  - `itr`
  - `corporate_tax`
  - `governance`
  - `audit`
- Start with backend APIs/admin workflows before UI-heavy filing journeys.

## Progress Log

- [x] 2026-05-20: Studied architecture docs and created the initial tracker.
- [x] 2026-05-20: Created Django project scaffold, settings split, app structure, and requirements manifest.
- [x] 2026-05-20: Added core versioned rule/primitive/module/change-set models and admin registration.
- [x] 2026-05-20: Added immutability guards plus primitive validation helpers for completeness/conflict checks.
- [x] 2026-05-20: Switched to the `test` pyenv environment and validated Django/DRF availability.
- [x] 2026-05-20: Generated and applied initial migrations in the test SQLite database.
- [x] 2026-05-20: Seeded AY 2026-27 ITR eligibility rules and the first ITR primitive.
- [x] 2026-05-20: Implemented and verified the first runtime slice for ITR form eligibility evaluation.
- [x] 2026-05-20: Re-verified in the `test` environment that all Django migrations are applied and the database is up to date.
- [x] 2026-05-20: Added decision-table models, seeded the first ITR decision table, and activated the first ITR module version for AY 2026-27.
- [x] 2026-05-20: Removed `test.sqlite3`, standardized back to the dev database, and verified dev migrations are fully applied.
- [x] 2026-05-20: Seeded the dev database with the first core ITR objects after standardizing on `db.sqlite3`.
- [x] 2026-05-20: Switched ITR runtime form selection from inline branching to actual stored decision-table execution.
- [x] 2026-05-20: Added immutable audit-log creation to the ITR evaluation flow with hashed payloads and hash chaining.
- [x] 2026-05-20: Added browsable audit API endpoints and richer audit admin inspection for manual trace lookup.
- [x] 2026-05-20: Switched ITR runtime rule loading to the active `ModuleVersion -> PrimitiveVersion -> RuleVersion` graph.
- [x] 2026-05-20: Extended audit logs with explicit primitive lineage and decision-table trace fields.
- [x] 2026-05-20: Added the second ITR vertical slice for regime selection with seeded rules, primitive, decision table, API endpoint, and audit logging.
- [x] 2026-05-20: Added the first ITR tax-computation slice for new-regime slabs, 87A rebate, and cess with API and audit logging.
- [x] 2026-05-20: Added core-rules module readiness/reporting APIs so module assembly health is inspectable as the process grows.
- [x] 2026-05-20: Hardened module readiness lookup by trimming whitespace from the assessment-context query parameter.
- [x] 2026-05-20: Added lightweight change-set grouping, activation-readiness reporting, and a seeded initial ITR activation bundle.
- [x] 2026-05-20: Added the first rule-version supersede flow to create draft next versions instead of editing active versions in place.
- [x] 2026-05-20: Added the first primitive-version supersede flow to create draft next primitive versions with carried-forward rule links.
- [x] 2026-05-20: Added lifecycle delete protection so draft versions can be deleted but active/approved/superseded versions cannot.
- [x] 2026-05-20: Added friendlier admin/API delete messaging for protected versioned records while keeping model-layer delete guards in place.
- [x] 2026-05-20: Added a draft change-set bundle helper that groups selected draft versions and auto-includes linked draft dependencies for review.
- [x] 2026-05-20: Added review and approval transition APIs for rules, primitives, and change sets with readiness checks before approval.
- [x] 2026-05-20: Added atomic change-set activation with readiness gating, module-graph safety checks, and activation snapshots.
- [x] 2026-05-20: Added a browser-based workflow studio plus `todo.md` so lifecycle actions, ITR runs, and remaining delivery work are visible in one UI.
- [x] 2026-05-20: Expanded the workflow studio into an authoring surface with rule/primitive/module create, clone, detail, edit, and module review/approval flows.
- [x] 2026-05-21: Added decision-table authoring, detail, supersede, review, and approval flows to the browser studio.
- [x] 2026-05-21: Added a guided browser promotion flow that rolls rule -> primitive -> decision table -> module -> change set in one path.
- [x] 2026-05-21: Added `concept_scope.md` to define the prototype boundary, success criteria, and explicitly deferred work.
- [x] 2026-05-21: Added a concrete “Corporate Concept Slice 1” implementation plan to the master tracker based on `corporate_tax_approach.md`.
- [x] 2026-05-21: Implemented and seeded the first corporate-tax concept slice with six primitives, two decision tables, one active module, runtime API, audit logging, persistence, and a browser simulation path.
- [x] 2026-05-21: Implemented and seeded the first governance cross-module slice with active governance module/rules, runtime API, audit logging, persistence, and a browser simulation path that evaluates live ITR and corporate outputs together.
- [x] 2026-05-21: Added unified governance posture aggregation with severity buckets and per-module signals so cross-module evaluation now returns a consolidated compliance posture.
- [x] 2026-05-21: Fixed governance UI payload coercion so cross-module browser evaluation uses serializer-typed numeric/date values instead of raw form strings.

## Phase 1: Project Foundation

- [x] Create Django project scaffold.
- [x] Configure SQLite as the default database.
- [x] Create Django apps: `core_rules`, `itr`, `corporate_tax`, `governance`, `audit`.
- [x] Set up environment settings split for local/dev/test.
- [x] Add base dependencies for Django, Django REST Framework, and test tooling.
- [ ] Define coding conventions for rule IDs, enums, statuses, and version keys.
- [x] Add initial README section describing the rules-first architecture.

## Phase 2: Canonical Domain Model

- [x] Design the core `Rule` model using the architecture fields:
  - `rule_id`
  - `name`
  - `source`
  - `natural_language`
  - `structured_logic`
  - `mode`
  - `scope`
  - `trigger`
  - `consequence`
  - `severity`
  - `version`
  - `status`
  - approval metadata
- [x] Design `PrimitiveDefinition` and `PrimitiveVersion` models.
- [x] Design `ModuleDefinition`, `ModuleVersion`, and module contract models.
- [x] Design `DecisionTable` and `DecisionTableVersion` models.
- [ ] Design `ComputationFunction` registry metadata model.
- [x] Design `ChangeSet` model for atomic activations.
- [x] Design `AssessmentContext` model to bind AY/FY/version selection.
- [x] Design `CrossModuleRule` model for governance-layer rules.
- [x] Separate PII-bearing taxpayer data from evaluation/audit data.

## Phase 3: Reference Data and Enums

- [x] Define enums for rule mode: `OBSERVER`, `ALERT`, `CONTROL`, `DESIGNER`.
- [x] Define enums for severity: `INFO`, `WARNING`, `CRITICAL`, `ABSOLUTE`.
- [x] Define lifecycle states: `DRAFT`, `UNDER_REVIEW`, `APPROVED`, `ACTIVE`, `SUPERSEDED`.
- [x] Define module statuses and contract statuses.
- [ ] Define tax-domain enums needed by ITR and corporate modules.
- [ ] Standardize version format for rules, primitives, modules, and contracts.

## Phase 4: Rule Authoring and Storage

- [x] Build Django admin/forms for authoring rules.
- [x] Support structured logic as machine-readable JSON/DSL rather than plain text only.
- [x] Add source citation fields for Act/section/notification/instruction references.
- [x] Add validation to ensure required rule metadata is present before review.
- [x] Prevent in-place edits to approved/active versions.
- [x] Implement supersede flow that creates a new version instead of overwriting.
- [x] Enforce lifecycle delete policy for versioned records.

## Phase 5: Primitive Assembly

- [x] Create workflow to group rules into a primitive version.
- [ ] Enforce primitive completeness checks:
  - all expected input states handled
  - no missing consequence/output definitions
  - no dependency on other primitive outputs
- [x] Enforce primitive conflict detection for contradictory outcomes on same inputs.
- [x] Store primitive approval decision and approver metadata.
- [x] Mark approved primitives immutable.
- [ ] Add primitive comparison/diff view between versions.
- [x] Add primitive supersede flow to create draft next versions.

## Phase 6: Module Assembly

- [x] Create workflow to assemble modules from approved primitives.
- [x] Model decision tables whose inputs come from primitive outputs only.
- [ ] Register pure computation functions for tax calculations.
- [ ] Define module completeness checks:
  - all primitives approved
  - decisions fully covered
  - computations defined
  - no known domain gaps
  - contract defined
- [x] Store module contracts with `PROVIDES`, `CONSUMES`, version dependency, and fallback behavior.
- [ ] Enforce directed dependencies and reject circular module dependencies.
- [x] Mark approved module versions immutable.
- [x] Add a module readiness/reporting surface for active module assembly state.

## Phase 7: Setup-Time Engine

- [ ] Implement setup pipeline matching the architecture document:
  - completeness verification
  - conflict detection
  - approval gate
  - module assembly
  - module approval
  - cross-module rule registration
  - atomic activation via change set
- [x] Build impact analysis for rule/primitive/module changes.
- [x] Build activation safety checks so partial activation is impossible.
- [ ] Pre-compile approved rule logic for runtime execution.
- [ ] Index active versions by assessment context for fast lookup.

## Phase 8: Runtime Evaluation Engine

- [x] Accept an evaluation event plus assessment context.
- [x] Load active primitive versions for the context.
- [x] Evaluate primitives independently.
- [x] Feed primitive outputs into decision tables.
- [ ] Feed outcomes into computation functions.
- [x] Evaluate consequences based on mode and severity.
- [x] Evaluate governance-layer cross-module rules when relevant.
- [x] Return final outputs plus traceability metadata.
- [ ] Keep observer/alert evaluations async by default.
- [x] Keep control-mode rules capable of synchronous blocking.

## Phase 9: Audit and Traceability

- [x] Create immutable evaluation log model.
- [x] Record rule/primitive/module version used for every evaluation.
- [x] Store hashes/category references instead of raw personal identifiers in audit logs.
- [x] Add tamper-evident strategy for logs, starting with hash chaining.
- [x] Store computation results with rule lineage for reproducibility.
- [x] Add admin/report views for audit trace lookup by context, taxpayer hash, and filing record.

## Phase 10: ITR Module Implementation

- [x] Convert `ITR_Rule_System.md` rules into structured records.
- [ ] Identify the primitive set needed for ITR eligibility, computation, deductions, process, verification, and penalty.
- [x] Build initial ITR form-selection decision table.
- [x] Build regime-selection logic for old vs new regime.
- [ ] Build core income computation functions.
- [ ] Build deduction eligibility logic for old regime.
- [ ] Build filing timeline and verification rule flows.
- [ ] Build derived object mapping from rules to taxpayer/income/deduction/filing data objects.
- [x] Activate first usable ITR module version for AY 2026-27.

## Phase 11: Corporate Tax Module Implementation

- [x] Convert `corporate_tax_approach.md` primitives into structured records.
- [ ] Implement corporate primitive groups:
  - entity classification
  - regime determination
  - income computation
  - tax computation
  - audit and compliance
  - process compliance
- [ ] Build decision tables for:
  - tax rate determination
  - filing form and sequence
  - MAT vs normal tax outcome
- [ ] Implement computation functions for taxable income, book profit, MAT, surcharge, and final liability.
- [x] Encode the corporate module contract with `PROVIDES` and `CONSUMES`.
- [x] Activate first usable corporate module version for Tax Year 2026-27.

### Corporate Concept Slice 1

This is the recommended next implementation slice for the current concept phase.

Goal:

- prove that the same framework can support a second tax domain
- keep corporate tax separate from ITR as its own module
- avoid jumping into full MAT/book-profit complexity too early

Scope of Slice 1:

- [x] Implement `CORP.ENTITY_TYPE`
- [x] Implement `CORP.PE_STATUS`
- [x] Implement `CORP.TURNOVER_CATEGORY`
- [x] Implement `CORP.INCORPORATION_DATE_STATUS`
- [x] Implement `CORP.REGIME_TRACK`
- [x] Implement `CORP.FILING_ROUTE`

Decision-table focus for Slice 1:

- [x] Build corporate regime-track decision table
- [x] Build corporate filing-route decision table

Module contract for Slice 1:

- [x] `PROVIDES`:
  - `entity_type`
  - `pe_status`
  - `turnover_category`
  - `incorporation_date_status`
  - `regime_track`
  - `filing_route`
  - `compliance_alerts`
- [x] `CONSUMES`:
  - company profile
  - registration facts
  - turnover facts
  - incorporation facts
  - optional PE indicators

Runtime target for Slice 1:

- [x] Add one corporate runtime evaluation endpoint
- [x] Return entity classification, regime track, filing route, and alerts
- [x] Create audit logs for corporate evaluations

UI target for Slice 1:

- [x] Add a corporate simulation path beside ITR in the browser studio
- [x] Reuse the same authoring, promotion, review, approval, and activation workflow

Explicitly deferred beyond Slice 1:

- [ ] full taxable-income computation
- [ ] book-profit computation
- [ ] MAT vs normal tax computation
- [ ] surcharge and cess depth
- [ ] transfer pricing
- [ ] AMT for LLP and wider entity classes beyond the concept path

## Phase 12: Governance Layer

- [ ] Implement cross-module rule registration.
- [ ] Validate cross-module rules against module contracts only.
- [ ] Add circular dependency detection across modules.
- [x] Implement unified compliance status aggregation.
- [x] Implement cross-module evaluation triggers.
- [ ] Add governance dashboards for compliance/audit visibility.

## Phase 13: API and Admin Surface

- [ ] Build internal APIs for:
  - rule CRUD
  - primitive review/approval
  - module review/approval
  - activation/change set execution
  - runtime evaluation
  - audit trace retrieval
- [x] Build admin screens for tax/domain experts rather than only developer-managed fixtures.
- [x] Add a lightweight API to bundle draft rule/primitive/module artifacts into a reviewable draft change set.
- [x] Add initial review/approval APIs for rule, primitive, and change-set transitions.
- [x] Add initial activation API for approved change sets with atomic lifecycle updates.
- [x] Add an initial browser UI to operate the rule lifecycle and run live ITR evaluations.
- [x] Add browser authoring/detail screens for rule, primitive, and module draft management.
- [x] Add browser authoring/detail screens for decision-table draft management.
- [x] Add a guided browser promotion flow spanning draft assembly through change-set bundling.
- [ ] Add import tools to load rules from Markdown/CSV/JSON seed formats.

## Phase 14: Testing Strategy

- [ ] Add unit tests for rule validation and versioning behavior.
- [ ] Add completeness tests for primitives.
- [ ] Add conflict detection tests.
- [ ] Add module contract validation tests.
- [ ] Add runtime evaluation tests by assessment year/context.
- [ ] Add audit log immutability tests.
- [ ] Add regression fixtures for key ITR and corporate tax scenarios.
- [ ] Add cross-module rule tests once governance layer is live.

## Phase 15: Near-Term Milestones

- [x] Milestone 1: Django project boots with core models and admin.
- [x] Milestone 2: Rule versioning and primitive approval workflow works end-to-end.
- [x] Milestone 3: One ITR decision flow evaluates successfully from stored rules.
- [ ] Milestone 4: One corporate tax computation flow evaluates successfully.
- [ ] Milestone 5: Audit trace reproduces a historical evaluation exactly.
- [x] Milestone 6: Cross-module governance rule executes across two modules.

## Suggested Build Order for the First Iteration

- [x] Start with `core_rules` models, migrations, and admin.
- [x] Implement versioning + approval restrictions first.
- [x] Implement primitive completeness/conflict checks next.
- [x] Implement minimal runtime evaluator for one primitive.
- [x] Implement ITR form eligibility as the first working slice.
- [ ] Implement audit logging immediately once first slice runs.
- [ ] Add corporate tax after the ITR vertical slice proves the architecture.

## Notes

- Current runtime evaluation works for the first ITR eligibility slice and is assessment-context aware at the module/rule selection level. Stored decision-table execution is now wired for the initial form-selection flow.
- Current runtime now loads rule versions through the active module/primitive graph rather than broad rule-id filtering.
- The seeded AY 2026-27 data now includes one active ITR primitive, one active ITR decision table, and one active ITR module version, not the full ITR module domain.
- The seeded AY 2026-27 data now includes two active ITR primitives (`ITR.FORM_ELIGIBILITY`, `ITR.REGIME_SELECTION`) and two active decision tables.
- The seeded AY 2026-27 data now includes a third active primitive `ITR.TAX_COMPUTATION` for the new-regime computation slice.
- Current tax computation support is partial: new-regime slab tax, 87A rebate, and cess are implemented; old-regime slab computation, surcharge, and broader income-head computations are still pending.
- The first governance slice now evaluates live ITR and corporate outputs together through `INDIA_TAX_GOVERNANCE@1.0` and returns review actions from stored cross-module rules.
- Governance evaluation now also returns a consolidated posture summary with `CLEAR`, `WATCH`, `REVIEW_REQUIRED`, or `CRITICAL_REVIEW`, plus per-module signals that explain the aggregate outcome.
- Module assembly health is now inspectable via `/api/core-rules/modules/<module_code>/readiness/`.
- Change-set grouping and activation readiness are now inspectable via `/api/core-rules/change-sets/` and `/api/core-rules/change-sets/<code>/activation-readiness/`.
- Rule versions can now be superseded through `/api/core-rules/rule-versions/supersede/`, which creates a draft next version with lineage metadata.
- Primitive versions can now be superseded through `/api/core-rules/primitive-versions/supersede/`, optionally swapping in replacement rule versions.
- Lifecycle deletion is now guarded at the model layer: draft versions can be deleted; non-draft protected versions are blocked everywhere.
- Admin/API delete flows now return clearer success/error messages for draft deletions and blocked active-record deletions.
- Active local database is now [db.sqlite3](/home/samar/projects/corp_tax_rules/db.sqlite3). `test.sqlite3` has been removed to avoid settings confusion.
- Current seeded dev counts: 1 assessment context, 12 rule definitions/versions, 1 primitive version, 1 decision table version, 1 module version.
- ITR API evaluations now also create an `EvaluationLog` entry with event id, payload hashes, and a hash-chain link to the previous audit record.
- Audit records can now be inspected in admin and via `/api/audit/evaluation-logs/` with context or event-id lookup.
- Audit records now store explicit `primitive_trace` and `decision_table_trace` alongside the rule trace.

## Deferred for Later

- [ ] Rich end-user filing UI.
- [ ] Production database migration from SQLite to PostgreSQL.
- [ ] OCR/document ingestion.
- [ ] External system integrations with GST/TDS/MCA.
- [ ] Advanced async processing/distributed workers.
- [ ] AI-assisted authoring with human approval gates.

## Open Decisions

- [ ] Final structured rule DSL format: JSON schema vs custom expression language.
- [ ] Whether computation functions live in DB metadata, Python registry, or both.
- [ ] Whether approval workflow stays in Django admin first or gets a custom review UI early.
- [ ] Whether Markdown docs become importable seeds or remain reference-only.
- [ ] Exact app boundaries for future GST/TDS/MCA modules.
