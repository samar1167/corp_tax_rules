# Concept Scope

## Purpose

This prototype demonstrates a rules-first compliance platform concept for tax workflows.

It is intended to prove that we can:

- store versioned rules, primitives, decision tables, modules, and change sets as explicit artifacts
- move those artifacts through draft, review, approval, and activation states
- evaluate live taxpayer scenarios against active rule-driven module structures
- preserve immutable audit traces for runtime decisions
- operate the lifecycle visually through a browser workflow, not only through admin or scripts

It is not intended to be a full-feature production tax engine yet.

## What The Concept Demonstrates

### 1. Rules-First Lifecycle

The system supports:

- draft authoring
- supersede instead of in-place editing
- review and approval transitions
- activation through change sets
- immutable active and approved artifacts

Artifacts covered in the concept:

- rule versions
- primitive versions
- decision table versions
- module versions
- change sets

### 2. Module Assembly

The concept shows that tax logic can be assembled in layers:

- rules feed primitives
- primitives feed decision tables
- primitives and decision tables feed modules
- modules are bundled into change sets for activation

### 3. Runtime Execution

The active ITR concept currently demonstrates:

- form eligibility
- regime selection
- partial tax computation for the new regime

Runtime uses active module graph loading and returns traceable outputs.

### 4. Auditability

Each live evaluation can create:

- immutable audit entries
- hash-chained logs
- rule lineage
- primitive lineage
- decision-table lineage

### 5. Visual Operability

The browser studio currently demonstrates:

- create, clone, supersede, and edit flows
- review and approval flows
- module and change-set promotion
- guided rule-to-change-set promotion
- live ITR scenario execution

## In-Scope For This Concept

- Django + SQLite implementation
- rules-first artifact model
- lifecycle controls and immutability
- first usable ITR module concept for AY 2026-27
- browser-based workflow studio
- guided promotion of a selected artifact chain
- audit logging and trace visibility

## Explicitly Out Of Scope For Now

These are intentionally parked in `todo.md`:

- full ITR product coverage
- full corporate tax product coverage
- batch promotion across many rules at once
- import-assisted authoring
- full generic rule interpreter
- full generic decision interpreter
- visual decision-table row editor
- complete reviewer diff/history tooling
- governance-wide cross-module execution
- production hardening, scaling, and security maturity

## Current Concept Boundary

This prototype should be evaluated as:

- a platform concept
- a workflow concept
- an artifact-governance concept

It should not yet be evaluated as:

- a complete tax filing product
- a comprehensive statutory engine
- a production-ready compliance system

## Current Success Criteria

The concept is successful if a reviewer can:

1. create or copy a draft rule-based artifact
2. roll it upward into primitive, decision table, module, and change set structures
3. move that chain through review and approval states
4. activate a coherent approved change set
5. run a live ITR scenario and inspect the trace and audit outcome
6. understand what is implemented vs intentionally deferred

## Primary Evaluation Paths

### Path A: Lifecycle Demonstration

- create or supersede a rule
- roll it into a primitive
- roll the primitive into a decision table
- roll both into a module
- bundle into a change set
- review, approve, and activate

### Path B: Runtime Demonstration

- run ITR form eligibility
- run regime selection
- run tax computation
- inspect traceability and audit records

### Path C: Governance Demonstration

- confirm active artifacts are immutable
- confirm draft artifacts are editable/deletable
- confirm incomplete activations are blocked

## Recommended Next Phase

When moving beyond this concept, the next phase should focus on full-product depth rather than more workflow polish:

- broaden tax-domain coverage
- add import-assisted content loading
- strengthen rule and decision schemas
- reduce hand-coded runtime behavior

Until then, this concept should remain a controlled demonstration of the rules-first platform approach.
