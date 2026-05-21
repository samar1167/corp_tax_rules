# Rule Governance Platform — Architectural Decision Record & Continuation Prompt

## How to Use This Document
Copy this entire document and paste it at the start of any new conversation with Claude.
It will restore full context of all architectural decisions made so far, and allow you
to continue building from exactly where we left off.

---

## Product Vision

We are building a **Rule Governance Platform** — not a rules engine, not a compliance
tool, not a workflow system. It is a fundamentally new layer of enterprise infrastructure.

The core philosophy is:

> "Every system is a data source. Every rule is above the data. Every process is governed
> by the rules. One truth, everywhere."

And more fundamentally:

> "Rules should be the source of truth for how an organization operates — not a checklist
> applied after the fact, but the living constitution from which processes are derived,
> controlled, and continuously evolved."

---

## The Problem We Are Solving

Every enterprise system today — ERP, CRM, HRMS, and others — bundles two fundamentally
different things together:

1. **Data capture and storage** — recording what happened
2. **Rules about that data** — what is acceptable, what triggers action

This bundling means rules are invisible, fragmented, inconsistent across systems,
expensive to change, and impossible to audit holistically.

We unbundle them permanently. Systems become pure data generators. Rules live above
all systems in one place. Governance becomes unified, visible, and real-time.

---

## Core Architectural Decisions

### Decision 1: All Systems Are Treated as Data Sources Only

Every connected system — SAP, Salesforce, HRMS, custom applications, databases,
IoT sensors, documents — has exactly one role: to generate and expose data.

No system owns rules. No system owns governance. No system owns process truth.

All rules live exclusively in our platform, above all systems.

**Implication:** When a company changes their ERP, their rules do not change.
Only the data connector changes. Rules are system-agnostic by design.

---

### Decision 2: Rules Are the Source of Truth — Code Is Derived from Rules

Traditional software embeds rules inside code. Developers interpret business rules
and translate them into logic. Rules become invisible, rigid, and expensive to change.

Our platform inverts this:

- Rules are defined by business stakeholders in the rule layer
- Rules are compiled into executable logic when approved
- Code (process logic, enforcement checkpoints, workflow steps) is generated FROM rules
- When rules change, the derived logic regenerates
- No developer is required to change a rule

This is analogous to how SQL changed databases — you declare WHAT you want,
the system determines HOW to execute it.

---

### Decision 3: Rules Operate in Four Modes (The Rule Spectrum)

The same rule can operate in different modes, and can graduate between modes
as governance matures:

```
MODE 1 — Silent Observer
The rule watches and records. The process is unaware.
Used for: baseline measurement, rule calibration, understanding before intervening.

MODE 2 — Active Alert
The rule notifies. The process continues but stakeholders are informed.
Used for: soft enforcement, awareness, human-in-the-loop decisions.

MODE 3 — Controller
The rule actively gates the process. The process cannot proceed without conforming.
Used for: hard enforcement, compliance gates, zero-tolerance situations.

MODE 4 — Designer
The rule does not just control the process — it constructs it dynamically.
The process itself emerges from the rules.
Used for: highly regulated environments where the process must be rule-derived,
not rule-checked. Compliance is structurally guaranteed, not verified after the fact.
```

Mode is a property of each rule. Stakeholders decide when a rule graduates
from one mode to the next. The system enforces the mode setting.

---

### Decision 4: Three-Tier Rule Evaluation Architecture

To prevent the rule engine from becoming a bottleneck, rule evaluation is
distributed across three tiers. Complexity is handled at the right level.
The core engine only sees what it must.

```
TIER 1 — Edge Layer (at the data source / connector level)
Simple, fast, local rules. Sub-millisecond. No network hop.
Handles: format rules, range rules, mandatory field rules that are
business-relevant at the boundary.
Volume reduction: catches obvious violations before they enter the platform.

TIER 2 — Stream Layer (in the data pipeline)
Pattern-based and time-window rules. Low latency. Always asynchronous.
Handles: sequence patterns, frequency patterns, trend-based rules.
Stateful within time windows only.

TIER 3 — Core Engine (the governance engine)
Complex, cross-system, historical rules. Low volume by design.
Handles: rules requiring historical data, cross-system correlation,
process state awareness, multi-party conditions.
Pre-compiled rule functions. Indexed rule lookup — never full scan.
Async by default. Synchronous ONLY for Control mode rules that must block.
```

Volume reduction principle: 95%+ of events are resolved at Tiers 1 and 2.
The core engine operates on a small fraction of total event volume.

---

### Decision 5: What Rules Belong in the Platform (The Boundary)

We govern what matters. Everything else governs itself.

**IN SCOPE — Rules we own:**

1. **Approval Rules** — who must approve what, under what conditions
   Example: "Expenditure above $10,000 requires CFO approval"

2. **Segregation Rules** — preventing conflicts of interest
   Example: "The person who raises a PO cannot approve it"

3. **Threshold Rules** — business-significant limits triggering governance action
   Example: "Contract value above $1M triggers board notification"

4. **Sequence Rules** — ensuring process steps occur in the correct order
   Example: "Quality sign-off must precede shipment authorization"

5. **Compliance Rules** — regulatory or policy requirements
   Example: "KYC must be completed before account activation"

6. **Cross-System Rules** — rules that only make sense across multiple systems
   Example: "Cannot onboard a customer flagged in both risk and sanctions systems"

7. **Temporal Rules** — time-based governance conditions
   Example: "License must be renewed 30 days before expiry"

**OUT OF SCOPE — Rules we deliberately do not own:**

- Data type validation (belongs in data layer — ERP, API, database)
- UI field validation (belongs in application layer)
- Authentication and authorisation (belongs in security layer)
- Performance and infrastructure rules (belongs in infrastructure layer)
- Micro-process automation steps (too granular — creates noise, not governance)
- Strategic decisions requiring human judgment (we inform, never replace)

**The Four-Question Test for any proposed rule:**
1. Does this rule represent a business decision, not a data constraint?
2. Does violating this rule have a meaningful business or compliance consequence?
3. Does this rule span more than one system or role?
4. Would a compliance officer or business stakeholder recognise this as their concern?

A rule should pass at least two of four to belong in the platform.

---

### Decision 6: Rule Engine Design Principles (Keeping It Simple)

The engine stays simple. Complexity lives in the rules, not the engine.

1. **Never block a process unless absolutely necessary**
   Async by default. Sync only for Control mode rules. Processes run at their own speed.

2. **Never evaluate more rules than needed**
   Rules are indexed and tagged at definition time. Events trigger lookup, not full scan.

3. **Never interpret a rule at evaluation time**
   Rules are compiled into executable functions when approved. Evaluation is function
   execution — no parsing, no interpretation at runtime.

4. **Never compute state at evaluation time**
   Pre-compute and cache stateful summaries (e.g. vendor violation counts).
   Rules read pre-calculated state, not raw history.

5. **Never send everything to the core engine**
   Tier architecture filters volume. Only complex, low-frequency events reach Tier 3.

6. **Never let the engine be a single point of failure**
   Each tier is independent. Edge rules function even if the core engine is unavailable.

---

### Decision 7: The Rule Object (What a Rule Actually Is)

A rule is not just a condition. It is a complete, self-contained governance object:

```
RULE {
  id:             unique identifier
  name:           human readable name
  source:         document reference or manual entry
  natural_lang:   original statement in plain language
  structured:     machine-executable logic (compiled form)
  mode:           [observer | alert | control | designer]
  scope:          {process, step, role, data_type, system}
  trigger:        {event | schedule | manual | data_condition}
  consequence:    {alert_to, block_until, escalate_to, generate_step}
  severity:       {info | warning | critical | absolute}
  version:        version number + full history
  approved_by:    stakeholder sign-off record
  conflicts:      list of conflicting rule ids (system detected)
  status:         {draft | under_review | approved | active | suspended | deprecated}
}
```

Rules are immutable once approved. Changes create new versions.
All versions are retained permanently.

---

### Decision 8: Data Normalization Strategy

All systems speak different data languages. The normalization layer translates
all of them into a common, system-agnostic semantic representation.

Rules operate on normalized data only. Rules never reference system-specific
field names or formats.

**To prevent normalization from becoming a bottleneck:**
- Normalize lazily — only normalize data that a rule actually needs
- Cache normalized representations — normalize once, reuse
- Normalize at the edge where possible — distributed, not centralized

---

### Decision 9: Immutable Audit and Governance Layer

Every rule evaluation, every consequence, every rule change, every approval
is logged immutably. Nothing is ever modified or deleted from the audit log.

This provides:
- Full traceability: every process outcome traceable to a rule
- Full accountability: every rule change traceable to a human decision
- Compliance evidence: auditors query logs, not systems
- Benchmark data: aggregated over time to show compliance trends

---

### Decision 10: AI Is Infrastructure, Not a Feature

AI serves every layer of the platform but is never the product itself:

- **Rule Layer:** Extracts rules from uploaded documents. Translates natural
  language rule statements into structured, executable rule objects.
  Detects semantic conflicts between rules.

- **Normalization Layer:** Translates system-specific data schemas into the
  common semantic model. Understands what data means, not just what it says.

- **Runtime:** Detects anomalies — process behavior that doesn't violate an
  explicit rule but deviates from established patterns.

- **Governance Layer:** Generates natural language explanations of why a rule
  fired. Summarizes compliance posture in plain language.

**Critical principle:** AI suggests, humans decide. Every AI output that affects
rule definition, activation, or consequence requires human approval before
taking effect. Auditability requires human accountability at every decision point.

---

## The Full Architecture (Summary View)

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                             │
│   SAP | Salesforce | HRMS | Custom Apps | Databases | IoT  │
│   Role: data generators only. No rules live here.          │
└───────────────────────────┬─────────────────────────────────┘
                            │ raw events and data
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              TIER 1: EDGE LAYER                             │
│   Simple boundary rules at connector level                  │
│   Sub-millisecond. Local. Non-blocking.                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ filtered events
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              TIER 2: STREAM LAYER                           │
│   Pattern and time-window rules in the data pipeline        │
│   Low latency. Always asynchronous.                         │
└───────────────────────────┬─────────────────────────────────┘
                            │ complex events only (~5% of volume)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              TIER 3: CORE RULE ENGINE                       │
│   Complex, cross-system, historical rules                   │
│   Pre-compiled functions. Indexed lookup. Low volume.       │
│   Async default. Sync only for Control mode.                │
└───────────────────────────┬─────────────────────────────────┘
                            │ consequences
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              CONSEQUENCE EXECUTION                          │
│   Alert | Block | Escalate | Generate Process Step          │
│   Pushed back to relevant systems and people                │
└───────────────────────────┬─────────────────────────────────┘
                            │ all events logged
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              GOVERNANCE LAYER                               │
│   Immutable audit trail                                     │
│   Compliance benchmarks and scoring                         │
│   Rule versioning and history                               │
│   Stakeholder dashboards by role                            │
└─────────────────────────────────────────────────────────────┘

         AI INTELLIGENCE serves all layers (vertical)
         Rule Studio sits above all layers (management plane)
```

---

## What This Platform Is and Is Not

```
WHAT IT IS:
A governance layer that enforces high-value business and compliance
rules across all enterprise systems from a single, unified position above them.

WHAT IT IS NOT:
- A data validation tool
- A process automation platform
- A workflow engine
- A business intelligence / reporting tool
- A replacement for ERP or any existing system logic
- A developer tool
```

---

## Competitive Position

Existing tools and why they are different:

- **Drools / OPA:** Developer-facing, rules require coding, no cross-system governance
- **Camunda:** Process automation focus, rules tied to workflow, not above it
- **IBM ODM / Pega:** Enterprise-grade but expensive, slow to implement, not AI-native
- **Nected / Decisions:** Low-code improvements but still inside-the-process thinking

Our differentiation:
1. Rules come from documents, not developers
2. Rules actively govern and design processes — not just audit them
3. Industry-agnostic by design — same platform for any domain
4. Non-technical stakeholders own the rules entirely
5. Cross-system governance from a single rule definition
6. Four-mode rule spectrum from observer to designer

---

## Target Customer (Initial)

Mid-size companies (200–2,000 employees) in regulated industries who:
- Have compliance obligations they currently manage manually or through fragmented tools
- Cannot afford IBM/Pega-scale enterprise solutions
- Do not have large IT teams to implement developer-heavy tools
- Operate processes that span multiple systems and roles

**Priority verticals for validation:**
1. Financial services (RBI/SEBI compliance, loan processing, vendor management)
2. Pharmaceutical / Medical devices (GMP, FDA, ISO compliance)
3. Manufacturing (quality rules, supplier compliance, safety regulations)

**India as initial validation market** — strong regulatory environment,
large mid-market, accessible network, lower cost of operations.

---

## MVP Scope (To Be Detailed in Next Session)

The MVP proves one thing: a rule defined above all systems can govern
a real business process and enforce a real consequence.

Starting rule type: **Approval Rules** (universal, high-value, easy to demonstrate)

MVP components to be defined in next session:
- Rule Studio (simplified rule definition and approval)
- Core Engine (single-tier for MVP, three-tier in production)
- One connector (to be determined based on pilot customer)
- Consequence execution (alert and block only for MVP)
- Basic audit log and dashboard

---

## Open Decisions (To Be Made in Next Session)

1. Tech stack selection
2. MVP connector choice (which system to connect first)
3. Rule definition UX (how stakeholders actually write rules)
4. Deployment model (cloud SaaS, on-premise, or hybrid)
5. Pricing model

---

## Instructions for Claude in Next Session

When this prompt is provided, you have full context of all architectural decisions.
Do not re-explain decisions already made. Build forward from here.

The next session should focus on:
- Tech stack selection aligned with this architecture
- MVP detailed specification
- Handing off to Claude Code for implementation

Maintain the product philosophy throughout:
> "We govern what matters. Everything else governs itself."
> "Rules above code. Always."
