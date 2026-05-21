# Rule Governance Platform — Architectural Approach
## A Reusable Framework for Rules-First System Design
### Capture Date: May 2026

---

## How to Use This Document

This document captures a complete architectural approach for building
a Rule Governance Platform using a rules-first design philosophy.

Paste this document at the start of any new conversation to restore
full architectural context. Build forward from here — do not re-derive
decisions already made.

This document is domain-agnostic. The approach applies to any compliance,
governance, or rule-enforcement system regardless of industry.

---

# PART 1: THE PHILOSOPHY

---

## 1.1 The Core Idea

Most software systems embed rules inside code.
Developers interpret business rules and translate them into logic.
Rules become invisible, rigid, and expensive to change.

This platform inverts that entirely:

```
TRADITIONAL:
  Business rule exists
  → Developer interprets it
  → Translates into code
  → Rule is now invisible
  → Change requires developer
  → Weeks to update

THIS APPROACH:
  Rule is defined above the code
  → Rule is compiled into executable logic
  → Code is derived FROM the rule
  → Rule remains visible and owned by business
  → Change creates new rule version
  → Hours to update
```

> **"Rules above code. Always."**

---

## 1.2 The Foundational Principles

### PRINCIPLE 1: Rules Are the Source of Truth
Every system behaviour is traceable to a rule.
No behaviour exists without a rule that created it.
Rules are not documentation — they ARE the system.

### PRINCIPLE 2: Systems Are Data Sources
Every connected system — ERP, CRM, databases, APIs —
has exactly one role: generate and expose data.
No system owns rules. No system owns governance.
All rules live in one place, above all systems.

### PRINCIPLE 3: Processes Are Derived from Rules
Processes do not define rules.
Rules define processes.
When rules change, processes adapt.
Compliance is structurally guaranteed — not verified after the fact.

### PRINCIPLE 4: Rules Operate on a Spectrum
```
SILENT OBSERVER → ACTIVE ALERT → CONTROLLER → DESIGNER

Observer:   Rule watches. Records. Process unaware.
Alert:      Rule notifies. Process continues.
Controller: Rule gates. Process cannot proceed without conforming.
Designer:   Rule constructs the process dynamically.
```
Mode is a property of each rule. It can change over time.
Rules graduate along the spectrum as governance matures.

### PRINCIPLE 5: Govern What Matters
```
IN SCOPE:
  Approval rules
  Segregation rules
  Threshold rules
  Sequence rules
  Compliance rules
  Cross-system rules
  Temporal rules

OUT OF SCOPE:
  Data type validation [data layer]
  UI field validation [application layer]
  Authentication [security layer]
  Performance rules [infrastructure layer]
  Micro-process automation [process layer]
  Strategic decisions [human judgment]
```

Test for any proposed rule:
1. Is this a business decision, not a data constraint?
2. Does violation have meaningful business consequence?
3. Does this span more than one system or role?
4. Would a compliance officer recognise this as their concern?

Pass at least 2 of 4 → belongs in the platform.

---

# PART 2: THE THREE-LEVEL ARCHITECTURE

---

## 2.1 Overview

The architecture has three levels.
The same design principle applies at every level.
This makes it fractal — consistent, predictable, learnable.

```
LEVEL 3: GOVERNANCE LAYER
         Unified compliance posture
         Cross-module rules
         One audit trail. One truth.
                ↑
────────────────────────────────────────
LEVEL 2: MODULE LAYER
         Domain-complete units
         [Income Tax | GST | TDS | MCA ...]
         Inter-module contracts
         Directed dependencies only
────────────────────────────────────────
                ↑
LEVEL 1: PRIMITIVE LAYER
         Self-contained rule units
         Complete. Immutable. Share-nothing.
         Rules → Primitives → Module
```

---

## 2.2 Level 1 — Primitives

### What Is a Primitive?
A primitive is the atomic unit of the rule system.
It owns all rules relevant to a single, self-contained question.
It is complete, immutable once approved, and trusted by everything above it.

### Primitive Completeness
A primitive is complete when:
1. Every rule that affects its output lives INSIDE it
2. Every possible input state produces a defined output
3. No input state falls through unhandled
4. No rule inside it depends on another primitive's output

An incomplete primitive cannot be approved.
An incomplete primitive cannot be activated.
Completeness is a hard gate, not a suggestion.

### The Share-Nothing Policy
Primitives do not depend on other primitives.
Each primitive owns all rules it needs — including rules
that may duplicate logic from other primitives.

**Duplication is acceptable at primitive level.**

Why:
```
Rules are CHECKS, not resource-hungry computations.
Cost of duplication: negligible [cheap boolean evaluation]
Cost of dependency: significant [coordination, cascading changes,
                                 evaluation order, version conflicts]

Completeness > Elegance. Always.
```

### Primitive Immutability
Once a primitive is approved, it is immutable.
If a rule within it must change:
→ A NEW VERSION of the primitive is created
→ New version goes through completeness check
→ New version goes through approval
→ Old version is permanently retained
→ Assessment context determines which version is active

### The Rule Object Inside a Primitive
Every rule inside a primitive has this structure:
```
RULE {
  id:             unique identifier
  name:           human readable
  source:         document reference or manual entry
  natural_lang:   plain language statement
  structured:     machine-executable logic
  mode:           [observer|alert|control|designer]
  scope:          {context this rule applies to}
  trigger:        {event|schedule|manual|data_condition}
  consequence:    {alert_to|block_until|escalate_to|generate_step}
  severity:       {info|warning|critical|absolute}
  version:        version number + history
  approved_by:    stakeholder sign-off
  status:         {draft|under_review|approved|active|superseded}
}
```

### Primitive Types
```
IDENTITY/STATUS PRIMITIVES
  Answer who/what the subject is.
  Example: RESIDENTIAL_STATUS, TAXPAYER_CATEGORY

PROFILE PRIMITIVES
  Answer what the subject has or does.
  Example: CAPITAL_GAINS_PROFILE, BUSINESS_INCOME_STATUS

COMPUTATION PRIMITIVES
  Produce calculated values from inputs.
  Example: TAX_SLAB_RATE, HOUSE_PROPERTY_INCOME
  Pure functions: same input always produces same output.

DEDUCTION/ELIGIBILITY PRIMITIVES
  Answer whether something is claimable and how much.
  Example: DEDUCTION_80C, HRA_EXEMPTION

PROCESS PRIMITIVES
  Answer whether a process action is valid.
  Example: FILING_TIMELINE_STATUS, RETURN_VALIDITY

VERIFICATION PRIMITIVES
  Answer whether identity/documents are valid.
  Example: IDENTITY_VERIFICATION, EVERIFICATION_STATUS
```

---

## 2.3 Level 2 — Modules

### What Is a Module?
A module is a complete, self-contained governance unit
for a specific compliance domain.
It is composed of approved primitives.
It is complete, immutable once approved, and trusted by Level 3.

### Module Completeness
A module is complete when:
1. All primitives within it are approved and active
2. All decisions within it have complete primitive inputs
3. All computations are fully defined
4. The module's domain is fully covered — no gaps
5. The module's inter-module contract is defined

### Module = Primitives + Decisions + Computations

```
MODULE STRUCTURE:

  PRIMITIVES [owned by module]
  ↓ outputs feed into ↓
  DECISION TABLES [one per governance decision]
  ↓ outcomes feed into ↓
  COMPUTATION FUNCTIONS [pure mathematical functions]
  ↓ all results feed into ↓
  MODULE OUTPUT [exposed via contract]
```

#### Decision Tables
One table per governance decision.
Collapses multiple conditions into a single outcome.
Conditions are primitive outputs — not raw data.
```
EXAMPLE: ITR Form Selection Decision Table
  INPUTS:  outputs from 11 primitives
  OUTPUTS: ITR1 | ITR2 | ITR3 | ITR4
  FORMAT:  rows = condition combinations
           columns = possible outcomes
           cells = condition values
```

Benefits:
- N conditions → 1 table [not N rules]
- Condition change → 1 cell update [not N rule updates]
- Complete coverage visible at a glance
- Conflict detection is trivial

#### Computation Functions
Pure functions — same input always produces same output.
No side effects. No state. No branching on external conditions.
```
EXAMPLE: Tax Slab Calculation
  INPUT:  taxable_income, regime, age_category
  OUTPUT: tax_amount
  LOGIC:  apply correct slab table
  PURE:   no external lookups, no state
```

### The Inter-Module Contract
Every module explicitly declares:

```
MODULE CONTRACT {
  module_id:      unique identifier
  version:        contract version
  domain:         what this module governs

  PROVIDES: [
    {output_id, description, data_type, conditions}
    ...outputs available to other modules
  ]

  CONSUMES: [
    {from_module, output_id, version, fallback_behaviour}
    ...inputs needed from other modules
  ]

  approved_by:    domain expert sign-off
  effective_from: assessment period / date
  status:         draft|approved|active|superseded
}
```

Contract changes trigger cross-module impact analysis.
No module can consume what another module has not explicitly declared.
No module can reach into another module's internals.

### Module Dependency Policies
```
POLICY 1: DIRECTED ONLY
  If Module A consumes from Module B,
  Module B cannot consume from Module A.
  No circular dependencies. Ever.

POLICY 2: CONTRACT-BOUND ONLY
  A module consumes only what is in another's contract.
  No access to internal primitives or decisions of other modules.

POLICY 3: VERSION-TOLERANT
  A module declares which VERSION of another's contract it needs.
  Module upgrades don't silently break dependents.

POLICY 4: FAILURE-SAFE
  If a consumed module is unavailable,
  consuming module defines its fallback behaviour explicitly.
  No silent failures.
```

### Module Approval Process
```
STEP 1: PRIMITIVE COMPLETENESS
        All primitives approved. None in DRAFT.

STEP 2: MODULE COMPLETENESS
        All decisions have complete primitive inputs.
        All computations fully defined.
        No domain gaps.

STEP 3: CONTRACT DEFINITION
        Module declares PROVIDES and CONSUMES explicitly.
        Contract reviewed and approved.

STEP 4: DOMAIN EXPERT APPROVAL
        Subject matter expert signs off.
        [Tax expert for Income Tax module]
        [GST expert for GST module]
        Immutable once approved.

STEP 5: CROSS-MODULE RULE REGISTRATION
        Inter-module rules referencing this module
        registered in dependency layer.
```

---

## 2.4 Level 3 — Governance Layer

### What Lives Here
Cross-module rules — rules that span more than one module.
These rules cannot live inside any single module.
They own the inter-module space.

```
EXAMPLES OF CROSS-MODULE RULES:
  "If GST turnover > ₹1Cr, Income Tax audit required"
  [GST module output → Income Tax module constraint]

  "TDS deducted must match GST invoice value within tolerance"
  [TDS module + GST module → compliance flag]

  "Disallowed expenses in Income Tax → ITC ineligible in GST"
  [Income Tax module output → GST module constraint]
```

### What Else Lives Here
```
UNIFIED COMPLIANCE POSTURE
  Aggregated view across all modules
  One compliance score per entity
  One risk heatmap

SINGLE AUDIT TRAIL
  Every rule evaluation from every module
  Immutable. Append-only. Never deleted.
  Each entry stamped with:
    rule_id + version
    module_id + version
    assessment_context
    input_data_hash [not raw data — hash]
    outcome
    timestamp [trusted source]

BENCHMARK ENGINE
  Compliance trends over time
  Rule effectiveness metrics
  Violation patterns and frequency

STAKEHOLDER DASHBOARDS
  Compliance officer: coverage, violations, audit readiness
  Process owner: what is blocked, what needs resolution
  Executive: posture, risk exposure
  Auditor: read-only, full trace, rule-to-evidence
```

### What Does NOT Live Here
```
The governance layer must not develop its own
primitives, decisions, or module structure.

The moment it does, a fourth level exists.
Four levels is too many.
Resist this. Always.

Governance layer = cross-module rules + unified view.
Nothing more.
```

---

# PART 3: KEY SYSTEM POLICIES

---

## POLICY SET 1: Versioning

```
P1.1  Rules are never modified. They are superseded.
      Every change creates a new version.
      Old versions are permanently retained.

P1.2  Primitives are never modified once approved.
      Rule changes within a primitive create
      a new primitive version.

P1.3  Modules are never modified once approved.
      Primitive or contract changes create
      a new module version.

P1.4  Assessment context [year/period] determines
      which version of every rule/primitive/module
      is active for any given evaluation.
      Historical evaluations always use the version
      that was active at the time — forever.

P1.5  No version is ever deleted.
      The system grows by addition only.
```

---

## POLICY SET 2: Completeness

```
P2.1  A primitive cannot be approved unless complete.
      Complete = all inputs produce defined outputs.
      Completeness is verified at setup. Not assumed.

P2.2  A module cannot be approved unless all its
      primitives are approved and complete.

P2.3  A cross-module rule cannot be activated unless
      all modules it references are approved and active.

P2.4  Completeness is a hard gate at every level.
      Partial activation is never permitted.
```

---

## POLICY SET 3: Change Management

```
P3.1  CHANGE SETS
      When one real-world rule change affects
      multiple primitives or modules,
      they are grouped into a change set.
      Change sets activate atomically — all or nothing.
      Consistency is always guaranteed.

P3.2  IMPACT ANALYSIS BEFORE ACTIVATION
      Every rule/primitive/module change triggers
      automatic impact analysis before activation:
        - What objects are affected?
        - What other primitives/modules are affected?
        - What is the change set?
        - What is the activation risk?
      Human reviews impact analysis. Human approves.

P3.3  RULE CHANGE LIFECYCLE
      Draft → Completeness Check → Conflict Check
      → Impact Analysis → Approval → Activation
      → Previous version archived → Audit logged

P3.4  NO AMBIGUITY IN APPROVED ITEMS
      If something is ambiguous, it is not approved.
      If it is approved, it is unambiguous.
      Ambiguity discovered post-approval → new version.
```

---

## POLICY SET 4: Runtime

```
P4.1  Setup-time intelligence. Runtime simplicity.
      All complexity [completeness, conflicts, order]
      resolved at setup. Runtime only executes.

P4.2  Async by default. Sync by exception.
      Rules evaluate asynchronously unless
      explicitly marked CONTROL mode.
      Processes never wait for observer/alert rules.

P4.3  Rules are compiled at approval time.
      Not interpreted at evaluation time.
      Evaluation = function execution. Fast.

P4.4  AI suggests. Humans decide.
      Every AI output affecting rule definition,
      activation, or consequence requires
      human approval before taking effect.
```

---

## POLICY SET 5: Audit and Data

```
P5.1  Immutable audit trail.
      Every evaluation logged. Never deleted. Never modified.
      Hash-chained entries prevent tampering.

P5.2  Personal data separation.
      Personal identifiers stored separately
      from rule evaluation logs.
      Audit log stores: data hashes, categories, outcomes.
      Not: names, PAN, Aadhaar in raw form.
      [Satisfies right-to-erasure without destroying audit trail]

P5.3  Every computation result stores its rule version.
      Not just the answer — the rules that produced it.
      Full reproducibility guaranteed.

P5.4  Assessment context is immutable on a filed record.
      A record filed under AY 2025-26 is always
      evaluated under AY 2025-26 rules.
      No retroactive rule application.
```

---

# PART 4: MANAGING COMPLEXITY

---

## 4.1 The Two Types of Complexity

```
ESSENTIAL COMPLEXITY
  Exists because the problem is complex.
  Cannot be eliminated.
  Must be managed and contained.

ACCIDENTAL COMPLEXITY
  Introduced by the solution, not the problem.
  Can and should be eliminated.
```

This architecture eliminates accidental complexity.
It contains essential complexity inside bounded units.

---

## 4.2 The Explosion Index

Rule/primitive/module explosion is the primary
long-term complexity risk.

**Explosion Index = Average Change Set Size**

```
LOW RISK:     Change set ≤ 5    [routine changes]
MEDIUM RISK:  Change set 6-15   [significant policy changes]
HIGH RISK:    Change set > 15   [paradigm changes]
```

**Why this architecture prevents explosion:**

```
PRIMITIVE LEVEL:
  Share-nothing → changes are local → change sets stay small
  Duplication accepted → no cascading dependency updates

MODULE LEVEL:
  Contract-bound dependencies → changes are explicit
  Directed only → no circular cascade
  Version-tolerant → modules upgrade independently

GOVERNANCE LEVEL:
  Few cross-module rules → small change sets
  Each rule is high-value → justified complexity
```

**Growth projection [illustrative]:**
```
                  Primitives  Modules  Cross-Rules  Explosion Risk
Income Tax only       35          1         0            LOW
+ GST                 50          2         5            LOW
+ TDS                 65          3         8            LOW
+ MCA                 75          4        12            LOW-MEDIUM
Full compliance       90          6        20            MEDIUM
```

Primitive count grows sub-linearly as domains are added.
Existing primitives are reused across modules.
The architecture scales without explosion.

---

## 4.3 The Safe Zone

```
SAFE:     < 150 primitives, < 30 cross-module rules
WATCH:    150-300 primitives, 30-60 cross-module rules
DANGER:   > 300 primitives, > 60 cross-module rules
```

Stay in the safe zone by:
1. Enforcing share-nothing at primitive level
2. Keeping cross-module rules at governance level only
3. Never adding a fourth architectural level
4. Ruthlessly applying the "govern what matters" filter

---

## 4.4 The Abstraction Tax

Every level of abstraction adds:
- Indirection [harder to trace causality]
- Governance overhead [more approvals, more contracts]
- Onboarding complexity [more to learn]

Three levels is correct for this problem.
Four levels is too many.

**The governance layer must remain a rule layer —
not develop into a fourth structured level.**

---

# PART 5: THE SETUP PROCESS

---

## 5.1 What Setup Does

Setup is where intelligence lives.
Runtime is where speed lives.

```
SETUP [runs at rule registration and system initialisation]:

PHASE 1: COMPLETENESS VERIFICATION
  For each primitive:
    Do all inputs produce defined outputs?
    Are all required rules present?
    Are there gaps?
  FAIL → reject. Primitive not activated.
  PASS → mark as complete.

PHASE 2: CONFLICT DETECTION
  Within each primitive:
    Do any rules produce contradictory outputs
    for the same input?
  FAIL → reject. Return to author with conflict report.
  PASS → proceed.

PHASE 3: APPROVAL GATE
  Human domain expert reviews.
  Approves or rejects with reason.
  REJECT → back to author.
  APPROVE → primitive is immutable from this point.

PHASE 4: MODULE ASSEMBLY
  All primitives for module are approved?
  All decisions have complete inputs?
  Contract defined?
  FAIL → module not activated.
  PASS → module completeness confirmed.

PHASE 5: MODULE APPROVAL
  Domain expert approves module.
  Contract locked.
  Module immutable from this point.

PHASE 6: CROSS-MODULE RULE REGISTRATION
  Inter-module rules validated against contracts.
  Circular dependency check [must be acyclic].
  FAIL → rule rejected.
  PASS → rule registered in governance layer.

PHASE 7: ACTIVATION
  Change set assembled [all affected items].
  All items in change set approved?
  FAIL [any one] → none activate.
  PASS [all] → atomic activation.
  Audit entry written.
```

---

## 5.2 Runtime Flow

After clean setup, runtime is simple:

```
RUNTIME:

1. Event received [from any connected system]
2. Assessment context identified [year/period]
3. Correct primitive versions loaded [pre-indexed]
4. Primitives evaluated [each self-contained]
5. Primitive outputs fed to decision tables
6. Decision tables produce outcomes
7. Outcomes fed to computation functions
8. Consequences determined
9. Cross-module rules checked [if cross-domain event]
10. Consequences executed [alert/block/escalate/generate]
11. Evaluation logged [immutably]

No conflict detection at runtime.
No version resolution at runtime.
No dependency ordering at runtime.
No duplication handling at runtime.

All of that happened at setup.
Runtime is fast. Predictable. Simple.
```

---

# PART 6: THE COMPETITIVE POSITION

---

## What This Is Not

```
NOT a rules engine [Drools, OPA]
  Those require developers to program every rule.
  Rules live inside code, not above it.

NOT a process automation platform [Camunda, Pega]
  Those automate processes.
  This governs them.

NOT a compliance reporting tool
  Those report what happened.
  This prevents what should not happen.

NOT a data validation tool
  That lives at the data layer.
  This lives above all systems.
```

## What This Is

```
GOVERNANCE INFRASTRUCTURE

The same way the internet is communication infrastructure
and cloud is compute infrastructure —

This is rule infrastructure for the enterprise.

Rules above code.
Systems as data sources.
Processes derived from rules.
Compliance structurally guaranteed.
One truth. Everywhere.
```

## The Differentiation

```
1. Rules come from documents, not developers
   Upload a policy PDF → AI extracts rules →
   Human approves → System enforces

2. Rules actively govern — not just audit
   Real-time intervention, not post-mortem reporting
   Alert → Block → Escalate → Design

3. Industry-agnostic by design
   Same platform: tax, GST, pharma, banking, HR

4. Non-technical stakeholders own the rules
   No developer needed to change a rule

5. Cross-system governance from one rule definition
   Rule doesn't know or care which system data came from

6. Four-mode rule spectrum
   Observer → Alert → Controller → Designer
```

---

# PART 7: KNOWN PROBLEMS AND MITIGATIONS

---

These problems are documented honestly.
They are not solved — they are managed.

```
PROBLEM 1: Rule Completeness Limits
  Rules from documents cover explicit rules only.
  Interpretive and tacit rules are not captured.
  MITIGATION: Clearly communicate coverage scope.
              Mark rules by source and certainty level.
              Never claim complete coverage.

PROBLEM 2: Interpretive Rule Conflicts
  Two valid rules, context-dependent resolution.
  Algorithm cannot resolve — human must.
  MITIGATION: Flag as INTERPRETIVE_CONFLICT.
              Route to human resolution queue.
              Never silently pick one.

PROBLEM 3: Data Quality
  Rules evaluate data. Bad data → wrong evaluation.
  MITIGATION: Data quality layer at connectors.
              Flag low-confidence data sources.
              Never treat source data as authoritative
              without validation signal.

PROBLEM 4: DPDP Act vs Audit Trail
  Right to erasure conflicts with immutable audit.
  MITIGATION: Personal data stored separately.
              Audit log stores hashes and categories.
              Erasure deletes personal data.
              Audit log retains anonymised record.

PROBLEM 5: Seasonal Scaling
  Peak load concentrated in filing periods.
  MITIGATION: Design for elasticity from day one.
              Tier architecture [edge/stream/core]
              distributes load.
              Stateless where possible.
              Pre-computed state for stateful rules.

PROBLEM 6: Dual Evaluation [Regime Comparison]
  Same subject, two contradictory rule states.
  MITIGATION: Branching evaluation context.
              Evaluate twice in parallel.
              Present comparison. User chooses.
              Chosen regime becomes the evaluation context.

PROBLEM 7: Human Approval Speed
  Bulk rule changes under time pressure.
  MITIGATION: Change set grouping for efficiency.
              Fast-track process for time-critical changes
              with elevated approval authority.
              Risk-tiered approval [low risk = faster path].

PROBLEM 8: Partial Compliance
  Full compliance temporarily impossible.
  MITIGATION: PROVISIONAL state for filings.
              Declared exceptions. Flagged for resolution.
              Not a hard block — a tracked exception.

PROBLEM 9: Rule Explosion
  SOLVED by this architecture.
  Primitives + decision tables + share-nothing policy.
  Explosion index remains LOW at scale.

PROBLEM 10: Rule Ownership and Liability
  Who is liable when an enforced rule is wrong?
  MITIGATION: Rule source always recorded.
              Approved-by always recorded.
              Platform enforces — does not author.
              Legal framework required before
              customer-defined rules are enabled.
```

---

# PART 8: INSTRUCTIONS FOR CONTINUING IN A NEW THREAD

---

When pasting this document to continue work:

**State clearly which of these you want to work on next:**

```
OPTION A: Define primitives for a specific domain
          [e.g. "Define all primitives for ITR1/ITR2"]

OPTION B: Build a decision table for a specific decision
          [e.g. "Build ITR form selection decision table"]

OPTION C: Define a module contract
          [e.g. "Define the Income Tax module contract"]

OPTION D: Define cross-module rules
          [e.g. "Define cross-module rules between IT and GST"]

OPTION E: Move to tech stack and implementation
          [e.g. "Define tech stack for MVP"]

OPTION F: Work on a specific known problem
          [e.g. "Solve the DPDP vs audit trail problem"]

OPTION G: Extend to a new domain
          [e.g. "Apply this architecture to GST compliance"]
```

**Critical instructions for Claude in next session:**
- Do not re-derive decisions already made in this document
- Challenge assumptions — do not just agree
- If something conflicts with a policy in this document, flag it
- Ask for domain clarification before assuming
- Be specific — no generic answers
- Build forward from here

---

*Developed through structured architectural reasoning*
*Domain-agnostic. Reusable. Extensible.*
*Version 1.0 — May 2026*
