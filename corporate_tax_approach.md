# Corporate Tax Compliance — India
## Rules-First Architecture Approach
## Tax Year 2026-27 | Income-tax Act 2025
### Built on: approach.md v1.0

---

## How to Use This Document

This document applies the Rule Governance Platform architecture
defined in approach.md to Indian Corporate Tax compliance.

Read approach.md first. This document assumes full familiarity
with the three-level architecture, system policies, and
primitive/module/governance concepts defined there.

This document defines:
- The corporate tax module structure
- All primitives with their complete rule ownership
- Decision tables for key governance decisions
- Computation functions
- Inter-module contract
- Cross-module rules with ITR individual module
- Known complexity risks specific to this domain

---

# PART 1: DOMAIN OVERVIEW

---

## 1.1 What Corporate Tax Covers

Corporate tax in India governs the income tax liability
of companies and certain other entities. It is fundamentally
different from individual tax [ITR1/ITR2] in these ways:

```
INDIVIDUAL TAX:          CORPORATE TAX:
One taxpayer type        Multiple entity types
[individual/HUF]         [domestic/foreign/LLP/cooperative]

One regime choice        Multiple regime tracks
[old/new]                [30%/25%/22%/15%/35%]

Self-assessed            Audit-mandatory above thresholds
Simple income heads      Complex income computation
                         [book profit vs taxable profit]

No MAT for individuals   MAT mandatory [unless concessional]
Simple TDS               Complex TDS obligations [payer + payee]
No transfer pricing      Transfer pricing mandatory
                         [international + specified domestic]
```

---

## 1.2 Entity Types in Scope

```
DOMESTIC COMPANY
  Incorporated under Indian Companies Act
  Global income taxable in India
  Four rate tracks available

FOREIGN COMPANY
  Not incorporated under Indian Companies Act
  Only India-sourced income taxable
  Higher rate structure
  PE [Permanent Establishment] determination critical

LLP [Limited Liability Partnership]
  Taxed at 30% flat
  AMT [Alternate Minimum Tax] instead of MAT
  Partner remuneration subject to TDS [Section 194T equivalent]

COOPERATIVE SOCIETY
  Separate rate structure
  Out of scope for this version — Phase 2

IFSC UNIT [International Financial Services Centre]
  Special MAT rate [9%]
  Separate treatment required
```

---

## 1.3 The Regime Decision — Central to Everything

Unlike individual tax [two regimes], corporate tax has
a regime decision that determines the ENTIRE compliance
posture of the company. Getting it wrong is expensive
and sometimes irreversible.

```
REGIME TRACKS FOR DOMESTIC COMPANIES:

TRACK 1: DEFAULT 30%
  Largest companies [turnover > ₹400Cr]
  All deductions available
  MAT applicable [15% of book profit]
  All exemptions available

TRACK 2: CONCESSIONAL 25%
  Turnover ≤ ₹400Cr in previous year
  All deductions available
  MAT applicable [15% of book profit]
  [Not a separate regime — just a lower rate]

TRACK 3: CONCESSIONAL 22% [Section 115BAA equivalent]
  Any domestic company — optional
  Most deductions FORFEITED
  MAT NOT applicable
  Surcharge fixed at 10%
  Once opted: CANNOT REVERT [permanent]
  MAT credit expires on switching

TRACK 4: NEW MANUFACTURING 15% [Section 115BAB equivalent]
  Incorporated on or after 1 October 2019
  Manufacturing activity only
  Most deductions FORFEITED
  MAT NOT applicable
  Surcharge fixed at 10%
  Once opted: CANNOT REVERT [permanent]
  2026 eligibility: new incorporations generally ineligible

FOREIGN COMPANY:
  35% base rate [reduced from 40% by Finance Act 2024]
  Royalties/FTS from pre-1976 agreements: 50%
  MAT: applicable only if PE in India
  Surcharge: 2% [₹1Cr-₹10Cr income] / 5% [>₹10Cr]
```

---

## 1.4 The MAT/AMT Layer

The most complex aspect of corporate tax.
MAT [Minimum Alternate Tax] ensures companies with
large book profits but low taxable income still pay tax.

```
MAT APPLIES TO:
  Domestic companies on Track 1 or Track 2
  Foreign companies with PE in India
  MAT rate: 14% of book profit [Finance Act 2026]
  IFSC units: 9% MAT rate

MAT DOES NOT APPLY TO:
  Companies on Track 3 [22%] or Track 4 [15%]
  Foreign companies without PE in India

MAT CREDIT:
  When MAT paid > Normal tax:
  Excess = MAT credit
  Carried forward: 15 years
  Used when normal tax > MAT in future years

  Finance Act 2026 changes:
  Track 1/2 companies: no NEW MAT credit
                        no utilisation of existing credit going forward
  Track 3/4 companies switching: MAT credit usable
                                  but capped at 25% of normal tax per year
                                  remaining carried forward 15 years

AMT [Alternate Minimum Tax]:
  Applies to LLPs and specified non-corporate entities
  claiming profit-linked deductions
  Rate: 18.5% of adjusted total income
```

---

# PART 2: PRIMITIVES

---

## Primitive Design Principles [Reminder from approach.md]

```
Each primitive:
  → Owns ALL rules relevant to its question
  → Is complete [all inputs → defined outputs]
  → Is immutable once approved
  → Is share-nothing [no dependency on other primitives]
  → May duplicate logic from other primitives [acceptable]

Duplication is the price of independence.
Completeness is non-negotiable.
```

---

## PRIMITIVE GROUP 1: ENTITY CLASSIFICATION

---

### PRIMITIVE: CORP.ENTITY_TYPE
**Question:** What type of entity is this taxpayer?
**Owns rules about:** Entity classification under Income-tax Act 2025

```
INPUTS:
  registration.country: string
  registration.act: [Companies_Act | LLP_Act | Other]
  management_control.in_india: boolean
  income.arrangement_for_dividend_in_india: boolean

RULES OWNED:
  Rule 1: IF registration.country = INDIA
             AND registration.act = Companies_Act
           THEN entity_type = DOMESTIC_COMPANY

  Rule 2: IF registration.country != INDIA
             OR registration.act != Companies_Act
           THEN entity_type = FOREIGN_COMPANY
           [Section 2(23A) definition]

  Rule 3: IF registration.act = LLP_Act
           THEN entity_type = LLP
           [separate rate and MAT treatment]

  Rule 4: IF entity_type = FOREIGN_COMPANY
             AND management_control.in_india = TRUE
           THEN entity_type = DEEMED_DOMESTIC
           [residential status of company]

OUTPUTS: DOMESTIC_COMPANY | FOREIGN_COMPANY |
         DEEMED_DOMESTIC | LLP

COMPLETENESS CHECK: All registration combinations handled.
                    Default: FOREIGN_COMPANY if no India registration.
```

---

### PRIMITIVE: CORP.PE_STATUS
**Question:** Does the foreign company have a Permanent Establishment in India?
**Owns rules about:** PE determination — critical for MAT and tax base

```
INPUTS:
  entity_type: [from own classification — internal]
  office.fixed_place_in_india: boolean
  agents.dependent_in_india: boolean
  construction.project_duration_days: integer
  service.days_in_india: integer

RULES OWNED:
  Rule 1: IF entity_type = DOMESTIC_COMPANY
           THEN pe_status = NOT_APPLICABLE

  Rule 2: IF entity_type = FOREIGN_COMPANY
             AND office.fixed_place_in_india = TRUE
           THEN pe_status = PE_EXISTS

  Rule 3: IF entity_type = FOREIGN_COMPANY
             AND agents.dependent_in_india = TRUE
           THEN pe_status = PE_EXISTS

  Rule 4: IF entity_type = FOREIGN_COMPANY
             AND construction.project_duration_days > 183
           THEN pe_status = PE_EXISTS

  Rule 5: IF entity_type = FOREIGN_COMPANY
             AND ALL above conditions = FALSE
           THEN pe_status = NO_PE
           [MAT not applicable, limited India tax base]

  Note: DTAA provisions may override — flag for human review
        DTAA_OVERRIDE_FLAG if applicable treaty exists

OUTPUTS: PE_EXISTS | NO_PE | NOT_APPLICABLE | DTAA_REVIEW_REQUIRED
```

---

### PRIMITIVE: CORP.TURNOVER_CATEGORY
**Question:** What is the company's turnover classification?
**Owns rules about:** Turnover thresholds that determine rate eligibility

```
INPUTS:
  turnover.previous_year: decimal [FY 2024-25 for AY 2026-27]
  entity_type: [classified internally]

RULES OWNED:
  Rule 1: IF entity_type = LLP
           THEN turnover_category = LLP_FLAT_30
           [turnover irrelevant for LLP rate]

  Rule 2: IF entity_type = DOMESTIC_COMPANY
             AND turnover.previous_year <= 400_00_00_000 [₹400Cr]
           THEN turnover_category = BELOW_400CR
           [eligible for 25% rate on Track 2]

  Rule 3: IF entity_type = DOMESTIC_COMPANY
             AND turnover.previous_year > 400_00_00_000
           THEN turnover_category = ABOVE_400CR
           [only 30% or concessional regimes available]

  Rule 4: IF entity_type = FOREIGN_COMPANY
           THEN turnover_category = FOREIGN
           [35% flat — turnover irrelevant for rate]

OUTPUTS: BELOW_400CR | ABOVE_400CR | LLP_FLAT_30 | FOREIGN
```

---

### PRIMITIVE: CORP.INCORPORATION_DATE_STATUS
**Question:** Does the company meet incorporation date criteria for 15% regime?
**Owns rules about:** 115BAB eligibility based on incorporation date

```
INPUTS:
  incorporation.date: date
  incorporation.country: string
  business.activity: [MANUFACTURING | SERVICES | MIXED]

RULES OWNED:
  Rule 1: IF incorporation.date >= DATE(2019, 10, 01)
             AND incorporation.country = INDIA
             AND business.activity = MANUFACTURING
           THEN incorporation_status = ELIGIBLE_FOR_15PCT

  Rule 2: IF incorporation.date < DATE(2019, 10, 01)
           THEN incorporation_status = INELIGIBLE_FOR_15PCT
           [15% regime requires post-Oct 2019 incorporation]

  Rule 3: IF business.activity != MANUFACTURING
           THEN incorporation_status = INELIGIBLE_FOR_15PCT
           [15% regime: manufacturing only]

  Rule 4: IF incorporation_status = ELIGIBLE_FOR_15PCT
             AND DATE(TODAY) > DATE(2026, 03, 31)
           THEN incorporation_status = INELIGIBLE_2026_ONWARD
           [2026: new incorporations generally ineligible]

OUTPUTS: ELIGIBLE_FOR_15PCT | INELIGIBLE_FOR_15PCT |
         INELIGIBLE_2026_ONWARD
```

---

### PRIMITIVE: CORP.IFSC_STATUS
**Question:** Is this company an IFSC unit?
**Owns rules about:** IFSC unit determination for special MAT rate

```
INPUTS:
  location.ifsc_zone: boolean
  income.foreign_exchange_only: boolean
  sebi.ifsc_registration: boolean

RULES OWNED:
  Rule 1: IF location.ifsc_zone = TRUE
             AND income.foreign_exchange_only = TRUE
             AND sebi.ifsc_registration = TRUE
           THEN ifsc_status = IFSC_UNIT
           [MAT at 9% applies]

  Rule 2: IF ANY above condition = FALSE
           THEN ifsc_status = NOT_IFSC
           [standard MAT rates apply]

OUTPUTS: IFSC_UNIT | NOT_IFSC
```

---

## PRIMITIVE GROUP 2: REGIME DETERMINATION

---

### PRIMITIVE: CORP.REGIME_TRACK
**Question:** Which tax regime track applies to this company?
**Owns rules about:** All conditions for each regime track

```
INPUTS:
  entity_type: [classified internally]
  turnover_category: [classified internally]
  incorporation_status: [classified internally]
  regime.opted_22pct: boolean [company declaration]
  regime.opted_15pct: boolean [company declaration]
  regime.previously_opted: string [historical record]

RULES OWNED:
  Rule 1: IF entity_type = FOREIGN_COMPANY
           THEN regime_track = FOREIGN_35PCT

  Rule 2: IF entity_type = LLP
           THEN regime_track = LLP_30PCT

  Rule 3: IF entity_type IN [DOMESTIC_COMPANY, DEEMED_DOMESTIC]
             AND regime.opted_15pct = TRUE
             AND incorporation_status = ELIGIBLE_FOR_15PCT
           THEN regime_track = NEW_MANUFACTURING_15PCT
           [MAT not applicable]

  Rule 4: IF entity_type IN [DOMESTIC_COMPANY, DEEMED_DOMESTIC]
             AND regime.opted_22pct = TRUE
             AND regime.opted_15pct = FALSE
           THEN regime_track = CONCESSIONAL_22PCT
           [MAT not applicable]
           [IRREVERSIBLE — flag on first election]

  Rule 5: IF entity_type IN [DOMESTIC_COMPANY, DEEMED_DOMESTIC]
             AND regime.opted_22pct = FALSE
             AND regime.opted_15pct = FALSE
             AND turnover_category = BELOW_400CR
           THEN regime_track = STANDARD_25PCT
           [MAT applicable]

  Rule 6: IF entity_type IN [DOMESTIC_COMPANY, DEEMED_DOMESTIC]
             AND regime.opted_22pct = FALSE
             AND regime.opted_15pct = FALSE
             AND turnover_category = ABOVE_400CR
           THEN regime_track = STANDARD_30PCT
           [MAT applicable]

  Rule 7: IF regime.previously_opted IN [CONCESSIONAL_22PCT,
             NEW_MANUFACTURING_15PCT]
             AND regime.opted_22pct = FALSE
             AND regime.opted_15pct = FALSE
           THEN regime_track = PREVIOUSLY_OPTED_CONCESSIONAL
           consequence = ALERT_IRREVERSIBLE_REGIME_ELECTED
           [cannot revert — compliance violation if attempted]

OUTPUTS: STANDARD_30PCT | STANDARD_25PCT | CONCESSIONAL_22PCT |
         NEW_MANUFACTURING_15PCT | FOREIGN_35PCT | LLP_30PCT |
         PREVIOUSLY_OPTED_CONCESSIONAL [error state]

IRREVERSIBILITY FLAG: Must be stored permanently
                      once concessional regime elected.
                      Human approval required before
                      any regime change attempt.
```

---

### PRIMITIVE: CORP.MAT_APPLICABILITY
**Question:** Does MAT/AMT apply and at what rate?
**Owns rules about:** MAT/AMT determination including Finance Act 2026 changes

```
INPUTS:
  regime_track: [determined internally]
  entity_type: [determined internally]
  ifsc_status: [determined internally]
  pe_status: [determined internally]

RULES OWNED:
  Rule 1: IF regime_track IN [CONCESSIONAL_22PCT,
             NEW_MANUFACTURING_15PCT]
           THEN mat_applicability = MAT_EXEMPT
           [concessional regime companies exempt from MAT]

  Rule 2: IF regime_track IN [STANDARD_30PCT, STANDARD_25PCT]
             AND entity_type = DOMESTIC_COMPANY
             AND ifsc_status = IFSC_UNIT
           THEN mat_applicability = MAT_APPLICABLE
                mat_rate = 0.09 [9% for IFSC]

  Rule 3: IF regime_track IN [STANDARD_30PCT, STANDARD_25PCT]
             AND entity_type = DOMESTIC_COMPANY
             AND ifsc_status = NOT_IFSC
           THEN mat_applicability = MAT_APPLICABLE
                mat_rate = 0.14 [14% from Finance Act 2026]

  Rule 4: IF entity_type = FOREIGN_COMPANY
             AND pe_status = PE_EXISTS
           THEN mat_applicability = MAT_APPLICABLE
                mat_rate = 0.14

  Rule 5: IF entity_type = FOREIGN_COMPANY
             AND pe_status = NO_PE
           THEN mat_applicability = MAT_EXEMPT
           [no PE = no MAT]

  Rule 6: IF entity_type = LLP
           THEN mat_applicability = AMT_APPLICABLE
                amt_rate = 0.185 [18.5%]
           [AMT not MAT for LLPs]

OUTPUTS: {
  applicability: MAT_APPLICABLE | MAT_EXEMPT | AMT_APPLICABLE,
  rate: decimal,
  credit_eligible: boolean
}
```

---

### PRIMITIVE: CORP.DEDUCTION_ELIGIBILITY
**Question:** Which deductions are available under the elected regime?
**Owns rules about:** Deduction forfeiture under concessional regimes

```
INPUTS:
  regime_track: [determined internally]

RULES OWNED:
  Rule 1: IF regime_track IN [CONCESSIONAL_22PCT,
             NEW_MANUFACTURING_15PCT]
           THEN deductions.chapter_via = FORFEITED
                deductions.section_10_exemptions = FORFEITED
                deductions.80IA_series = FORFEITED
                deductions.80JJAA = RETAINED [exception]
                deductions.80M = RETAINED [exception — inter-company dividend]
                deductions.standard_depreciation = RETAINED

  Rule 2: IF regime_track IN [STANDARD_30PCT, STANDARD_25PCT,
             FOREIGN_35PCT, LLP_30PCT]
           THEN deductions.all = AVAILABLE
                [subject to individual section conditions]

  Rule 3: IF regime_track = CONCESSIONAL_22PCT
             AND deduction.80JJAA.claimed = TRUE
           THEN REQUIRE: employment_increase.evidence IS NOT NULL
                REQUIRE: form_details.new_employees IS NOT NULL

OUTPUTS: {
  chapter_via: AVAILABLE | FORFEITED,
  section_10: AVAILABLE | FORFEITED,
  80IA_series: AVAILABLE | FORFEITED,
  80JJAA: AVAILABLE,  [always — even in concessional]
  80M: AVAILABLE,     [always — even in concessional]
  depreciation: AVAILABLE  [always]
}
```

---

## PRIMITIVE GROUP 3: INCOME COMPUTATION

---

### PRIMITIVE: CORP.TAXABLE_INCOME
**Question:** What is the company's total taxable income?
**Owns rules about:** Income heads, set-off rules, carry-forward

```
INPUTS:
  income.business_profession: decimal
  income.house_property: decimal
  income.capital_gains: decimal
  income.other_sources: decimal
  deductions.eligible: [from DEDUCTION_ELIGIBILITY — internal]
  losses.brought_forward: {type, amount, years_remaining}[]

RULES OWNED:
  Rule 1: Gross Total Income =
          SUM(business_profession + house_property +
              capital_gains + other_sources)

  Rule 2: Intra-head set-off first
          [losses within same head]

  Rule 3: Inter-head set-off next
          [subject to restrictions — capital loss
           cannot be set off against other heads]

  Rule 4: Business loss carry-forward: 8 years
          [only if return filed on time]
          REQUIRE: original_return.filed_on_time = TRUE
          IF filed_late: loss.carry_forward = BLOCKED
          consequence = ALERT_LOSS_FORFEITURE

  Rule 5: Unabsorbed depreciation: indefinite carry-forward
          No time limit. No filing condition.

  Rule 6: Capital loss carry-forward: 8 years
          Long-term capital loss: only against LTCG
          Short-term capital loss: against any capital gain

  Rule 7: Total Income = Gross Total Income
                         - eligible deductions
                         - brought forward losses [where allowed]

OUTPUTS: {
  gross_total_income: decimal,
  total_income: decimal,
  losses_utilized: decimal,
  losses_carried_forward: {type, amount}[]
}
```

---

### PRIMITIVE: CORP.BOOK_PROFIT
**Question:** What is the company's book profit for MAT purposes?
**Owns rules about:** Book profit computation under MAT provisions

```
INPUTS:
  accounts.net_profit_per_books: decimal
  adjustments.additions[]: {item, amount}
  adjustments.deductions[]: {item, amount}
  mat_applicability: MAT_APPLICABLE [internal check]

RULES OWNED:
  Rule 1: IF mat_applicability = MAT_EXEMPT
           THEN book_profit = NOT_APPLICABLE

  Rule 2: Book profit starts with net profit per P&L account
          [as per Companies Act / applicable accounting standards]

  Rule 3: ADDITIONS to book profit [increases MAT base]:
          + Income tax paid/payable [added back]
          + Dividend paid/proposed
          + Provision for losses of subsidiary
          + Depreciation [per books — replaced by IT Act depreciation]
          + Deferred tax [net debit]
          + Expenditure debited but not deductible u/s 37
          + Other specified items

  Rule 4: DEDUCTIONS from book profit [reduces MAT base]:
          - Depreciation u/s 32 [IT Act depreciation]
          - Amount withdrawn from reserves [if added in earlier year]
          - Income not chargeable under IT Act
          - Deferred tax [net credit]
          - Brought forward losses or unabsorbed depreciation
            [whichever is lower — important election]
          - Other specified items

  Rule 5: Book Profit = Net profit [per books]
                        + All additions
                        - All deductions

OUTPUTS: {
  book_profit: decimal,
  mat_liability: decimal [book_profit × mat_rate],
  mat_credit_this_year: decimal [if mat > normal tax]
}
```

---

### PRIMITIVE: CORP.MAT_CREDIT_POSITION
**Question:** What is the company's MAT credit balance and usability?
**Owns rules about:** MAT credit carry-forward, utilisation, and Finance Act 2026 caps

```
INPUTS:
  mat_credit.opening_balance: decimal
  mat_credit.years_remaining[]: {year, amount, years_left}
  tax.normal_liability: decimal
  tax.mat_liability: decimal
  regime_track: [internal]
  finance_act_2026.applicable: boolean

RULES OWNED:
  Rule 1: IF mat_credit.opening_balance = 0
           THEN mat_credit.usable_this_year = 0

  Rule 2: IF regime_track IN [STANDARD_30PCT, STANDARD_25PCT]
             AND finance_act_2026.applicable = TRUE
           THEN mat_credit.new_credit_this_year = 0
                mat_credit.utilisation = BLOCKED
                consequence = ALERT_FA2026_MAT_CREDIT_BLOCKED
           [Finance Act 2026: no new credit, no utilisation
            for companies remaining in old regime]

  Rule 3: IF regime_track IN [CONCESSIONAL_22PCT,
             NEW_MANUFACTURING_15PCT]
             AND mat_credit.opening_balance > 0
           THEN mat_credit.usable_this_year =
                MIN(mat_credit.opening_balance,
                    tax.normal_liability * 0.25)
                [25% cap per Finance Act 2026]
                mat_credit.carried_forward =
                mat_credit.opening_balance - mat_credit.usable_this_year

  Rule 4: IF entity_type = FOREIGN_COMPANY
             AND pe_status = PE_EXISTS
             AND mat_credit.opening_balance > 0
           THEN mat_credit.usable_this_year =
                MAX(tax.normal_liability - tax.mat_liability, 0)
                [foreign company: credit = normal tax - MAT when normal > MAT]

  Rule 5: MAT credit expires after 15 years
          FOR each credit_year IN mat_credit.years_remaining:
            IF credit_year.years_left = 0
            THEN credit_year.status = EXPIRED
                 consequence = ALERT_MAT_CREDIT_EXPIRING

OUTPUTS: {
  usable_this_year: decimal,
  new_credit_generated: decimal,
  closing_balance: decimal,
  expiry_alerts: []
}
```

---

## PRIMITIVE GROUP 4: TAX COMPUTATION

---

### PRIMITIVE: CORP.BASE_TAX_RATE
**Question:** What is the applicable base tax rate?
**Owns rules about:** Rate determination for each track and income type

```
INPUTS:
  regime_track: [internal]
  income.royalty_pre_1976: decimal [for foreign companies]

RULES OWNED:
  Rule 1: IF regime_track = STANDARD_30PCT
           THEN base_rate = 0.30

  Rule 2: IF regime_track = STANDARD_25PCT
           THEN base_rate = 0.25

  Rule 3: IF regime_track = CONCESSIONAL_22PCT
           THEN base_rate = 0.22

  Rule 4: IF regime_track = NEW_MANUFACTURING_15PCT
           THEN base_rate = 0.15

  Rule 5: IF regime_track = FOREIGN_35PCT
           THEN base_rate = 0.35
                [general income]

  Rule 6: IF regime_track = FOREIGN_35PCT
             AND income.royalty_pre_1976 > 0
           THEN base_rate_royalty = 0.50
                [special rate for pre-1976 agreements]

  Rule 7: IF regime_track = LLP_30PCT
           THEN base_rate = 0.30

OUTPUTS: {base_rate: decimal, special_rates: {type: rate}}
```

---

### PRIMITIVE: CORP.SURCHARGE_RATE
**Question:** What surcharge rate applies?
**Owns rules about:** All surcharge conditions including marginal relief

```
INPUTS:
  regime_track: [internal]
  entity_type: [internal]
  total_income: decimal

RULES OWNED:
  Rule 1: IF regime_track IN [CONCESSIONAL_22PCT,
             NEW_MANUFACTURING_15PCT]
           THEN surcharge_rate = 0.10 [flat 10% regardless of income]

  Rule 2: IF entity_type = DOMESTIC_COMPANY
             AND regime_track IN [STANDARD_30PCT, STANDARD_25PCT]
           THEN:
             IF total_income <= 1_00_00_000 [₹1Cr]
             THEN surcharge_rate = 0.00
             IF total_income > 1_00_00_000
                AND total_income <= 10_00_00_000 [₹10Cr]
             THEN surcharge_rate = 0.07 [7%]
             IF total_income > 10_00_00_000
             THEN surcharge_rate = 0.12 [12%]

  Rule 3: IF entity_type = FOREIGN_COMPANY
           THEN:
             IF total_income <= 1_00_00_000
             THEN surcharge_rate = 0.00
             IF total_income > 1_00_00_000
                AND total_income <= 10_00_00_000
             THEN surcharge_rate = 0.02 [2%]
             IF total_income > 10_00_00_000
             THEN surcharge_rate = 0.05 [5%]

  Rule 4: MARGINAL RELIEF
          IF income slightly exceeds surcharge threshold:
          Tax + Surcharge shall not exceed:
          Tax on threshold amount + excess income above threshold
          [Marginal relief computation required]
          consequence = COMPUTE_MARGINAL_RELIEF

  Rule 5: LLP surcharge:
          IF total_income > 1_00_00_000
          THEN surcharge_rate = 0.12

OUTPUTS: {surcharge_rate: decimal, marginal_relief_applicable: boolean}
```

---

### PRIMITIVE: CORP.FINAL_TAX_LIABILITY
**Question:** What is the company's total tax payable?
**Owns rules about:** Final computation integrating normal tax, MAT, credit, cess

```
INPUTS:
  taxable_income: decimal [from CORP.TAXABLE_INCOME]
  book_profit: decimal [from CORP.BOOK_PROFIT]
  base_rate: decimal [from CORP.BASE_TAX_RATE]
  surcharge_rate: decimal [from CORP.SURCHARGE_RATE]
  mat_applicability: [from CORP.MAT_APPLICABILITY]
  mat_credit_usable: decimal [from CORP.MAT_CREDIT_POSITION]
  tds.advance_tax_paid: decimal

RULES OWNED:
  Rule 1: Normal Tax = taxable_income × base_rate

  Rule 2: Normal Tax with Surcharge =
          Normal Tax × [1 + surcharge_rate]

  Rule 3: Cess = Normal Tax with Surcharge × 0.04
          [4% Health and Education Cess — always]

  Rule 4: Normal Tax Liability =
          Normal Tax with Surcharge + Cess

  Rule 5: IF mat_applicability = MAT_APPLICABLE
             AND mat_liability > normal_tax_liability
           THEN tax_payable = mat_liability
                mat_credit.generated = mat_liability - normal_tax_liability

  Rule 6: IF mat_applicability = MAT_APPLICABLE
             AND mat_liability <= normal_tax_liability
           THEN tax_payable = normal_tax_liability
                mat_credit.utilised = MIN(mat_credit_usable,
                                          normal_tax_liability - mat_liability)
                tax_payable = tax_payable - mat_credit.utilised

  Rule 7: IF mat_applicability = MAT_EXEMPT
           THEN tax_payable = normal_tax_liability

  Rule 8: Self Assessment Tax Due =
          tax_payable - tds.advance_tax_paid
          IF self_assessment_tax_due < 0:
          THEN refund_due = ABS(self_assessment_tax_due)

OUTPUTS: {
  normal_tax: decimal,
  mat_liability: decimal,
  final_tax_payable: decimal,
  mat_credit_generated: decimal,
  mat_credit_utilised: decimal,
  self_assessment_due: decimal,
  refund_due: decimal
}
```

---

## PRIMITIVE GROUP 5: AUDIT AND COMPLIANCE

---

### PRIMITIVE: CORP.TAX_AUDIT_OBLIGATION
**Question:** Is tax audit mandatory and under which section?
**Owns rules about:** All Section 44AB triggers and thresholds

```
INPUTS:
  business.turnover: decimal
  profession.gross_receipts: decimal
  transactions.digital_percent: decimal [% of total transactions]
  entity_type: [internal]
  presumptive.opted: boolean

RULES OWNED:
  Rule 1: IF business.turnover > 10_00_00_000 [₹10Cr]
           THEN tax_audit.required = TRUE
                tax_audit.reason = TURNOVER_EXCEEDS_10CR

  Rule 2: IF business.turnover > 1_00_00_000 [₹1Cr]
             AND business.turnover <= 10_00_00_000
             AND transactions.digital_percent < 0.95
           THEN tax_audit.required = TRUE
                tax_audit.reason = TURNOVER_EXCEEDS_1CR_CASH

  Rule 3: IF business.turnover > 1_00_00_000
             AND transactions.digital_percent >= 0.95
           THEN tax_audit.required = FALSE
                [95% digital exemption]

  Rule 4: IF profession.gross_receipts > 50_00_000 [₹50L]
           THEN tax_audit.required = TRUE
                tax_audit.reason = PROFESSIONAL_RECEIPTS_EXCEED_50L

  Rule 5: IF presumptive.opted = TRUE
             AND business.turnover <= 3_00_00_000 [₹3Cr]
           THEN tax_audit.required = FALSE
                [presumptive scheme exemption]

  Rule 6: IF tax_audit.required = TRUE
           THEN audit.form = 3CA [if statutory audit done]
                           OR 3CB [if no statutory audit]
                audit.report_form = 3CD [always]
                audit.due_date = DATE(AY, 09, 30)
                [30 September of AY]

OUTPUTS: {
  required: boolean,
  reason: string,
  form: [3CA | 3CB],
  report: 3CD,
  due_date: date
}
```

---

### PRIMITIVE: CORP.TRANSFER_PRICING_OBLIGATION
**Question:** Is transfer pricing documentation and reporting required?
**Owns rules about:** TP thresholds, documentation, Form 3CEB

```
INPUTS:
  transactions.international[]: {type, value, related_party}
  transactions.specified_domestic[]: {type, value, related_party}
  entity_type: [internal]

RULES OWNED:
  Rule 1: IF transactions.international IS NOT EMPTY
           THEN tp.documentation_required = TRUE
                tp.form = 3CEB
                tp.due_date = DATE(AY, 10, 31)
                [31 October of AY]
                tp.ca_certification = REQUIRED

  Rule 2: IF transactions.specified_domestic.total > 20_00_00_000 [₹20Cr]
           THEN tp.specified_domestic_reporting = TRUE
                tp.form = 3CEB [same form]

  Rule 3: IF tp.documentation_required = TRUE
           THEN tp.filing_precedes_itr = TRUE
                [3CEB must be filed before ITR-6]
                consequence = SEQUENCE_GATE

  Rule 4: Country-by-Country Reporting [CbCR]:
          IF entity_type = DOMESTIC_COMPANY
             AND consolidated_group_revenue >= 5500_00_00_000 [₹5,500Cr]
           THEN cbcr.required = TRUE
                cbcr.form = 3CEAD
                cbcr.due_date = DATE(AY, 11, 30)

OUTPUTS: {
  tp_required: boolean,
  cbcr_required: boolean,
  form_3ceb_due: date,
  ca_certification: boolean
}
```

---

### PRIMITIVE: CORP.TDS_OBLIGATION
**Question:** What TDS obligations does the company have as a deductor?
**Owns rules about:** Key TDS sections applicable to companies

```
INPUTS:
  payments.salary[]: {employee, amount}
  payments.contractor[]: {vendor, amount}
  payments.rent[]: {landlord, amount}
  payments.professional[]: {payee, amount}
  payments.interest[]: {payee, amount}
  payments.partner_remuneration[]: {partner, amount}
  entity_type: [internal]

RULES OWNED:
  Rule 1: Salary TDS [Section 192]:
          Every employer must deduct TDS on salary
          at applicable slab rates
          Quarterly return: Form 24Q
          Certificate: Form 16

  Rule 2: Contractor TDS [Section 194C]:
          IF single_payment > 30000
             OR annual_aggregate > 100000
          THEN tds_rate = 0.01 [individual/HUF]
                        OR 0.02 [others]

  Rule 3: Rent TDS [Section 194I]:
          IF rent.annual > 240000
          THEN tds_rate = 0.10 [land/building/furniture]
                        OR 0.02 [plant/machinery]

  Rule 4: Professional/Technical TDS [Section 194J]:
          IF payment > 30000 per year
          THEN tds_rate = 0.10 [professional]
                        OR 0.02 [technical services]

  Rule 5: Partner Remuneration TDS [Section 194T equivalent]:
          IF entity_type = LLP
             AND payments.partner_remuneration > 0
          THEN tds_rate = 0.10
               tds.quarterly_run = REQUIRED

  Rule 6: TDS deposit: by 7th of following month
          March deposits: by 30 April
          Quarterly return: due dates per schedule

  Rule 7: IF tds.not_deducted = TRUE
           THEN expense.disallowance = 30% of payment
                [Section 40a(ia) — important compliance consequence]
                consequence = ALERT_EXPENSE_DISALLOWANCE_RISK

OUTPUTS: {
  obligations[]: {section, rate, threshold, due_date},
  quarterly_returns: [24Q | 26Q | 27Q | 27EQ],
  disallowance_risk: boolean
}
```

---

## PRIMITIVE GROUP 6: PROCESS COMPLIANCE

---

### PRIMITIVE: CORP.FILING_TIMELINE
**Question:** What are the applicable filing deadlines?
**Owns rules about:** All ITR-6 filing deadlines and conditions

```
INPUTS:
  tax_audit.required: boolean [internal]
  tp.required: boolean [internal]
  entity_type: [internal]
  assessment_year: string

RULES OWNED:
  Rule 1: IF tax_audit.required = FALSE
             AND tp.required = FALSE
           THEN itr6.due_date = DATE(AY, 10, 31)
                [31 October — companies always have Oct deadline]

  Rule 2: IF tax_audit.required = TRUE
             AND tp.required = FALSE
           THEN audit.due_date = DATE(AY, 09, 30)
                itr6.due_date = DATE(AY, 10, 31)
                [audit before ITR — sequence gate]

  Rule 3: IF tp.required = TRUE
           THEN form_3ceb.due_date = DATE(AY, 10, 31)
                itr6.due_date = DATE(AY, 11, 30)
                [transfer pricing cases: November 30]

  Rule 4: Belated return: up to DATE(AY, 12, 31)
          With penalty under Section 234F:
          ₹5,000 [always — no ₹1,000 option for companies]

  Rule 5: Loss carry-forward condition:
          IF return.filed_after = itr6.due_date
             AND loss.business > 0
           THEN loss.carry_forward = BLOCKED
                consequence = ALERT_LOSS_FORFEITURE_RISK

  Rule 6: Digital Signature Certificate [DSC]:
          ITR-6 MUST be e-filed with DSC
          No other verification method accepted
          IF dsc.valid = FALSE
          THEN filing = BLOCKED

OUTPUTS: {
  audit_due: date,
  tp_due: date,
  itr6_due: date,
  belated_last_date: date,
  dsc_required: boolean
}
```

---

### PRIMITIVE: CORP.ADVANCE_TAX_SCHEDULE
**Question:** What advance tax must be paid and when?
**Owns rules about:** Corporate advance tax schedule and interest implications

```
INPUTS:
  tax.estimated_annual: decimal
  tax.tds_expected: decimal
  entity_type: [internal]

RULES OWNED:
  Rule 1: IF (tax.estimated_annual - tax.tds_expected) < 10000
           THEN advance_tax.required = FALSE

  Rule 2: IF advance_tax.required = TRUE
           THEN schedule = [
             {date: DATE(FY, 06, 15), cumulative_pct: 0.15},
             {date: DATE(FY, 09, 15), cumulative_pct: 0.45},
             {date: DATE(FY, 12, 15), cumulative_pct: 0.75},
             {date: DATE(FY, 03, 15), cumulative_pct: 1.00}
           ]

  Rule 3: IF advance_tax.paid_cumulative < schedule.due_cumulative
           THEN interest.234C.applicable = TRUE
                rate = 1% per month on shortfall
                [simple interest for each quarter]

  Rule 4: IF advance_tax.total_paid < 0.90 × tax.assessed
           THEN interest.234B.applicable = TRUE
                rate = 1% per month from April 1 of AY
                [on shortfall from 90% threshold]

OUTPUTS: {
  required: boolean,
  schedule[]: {due_date, amount},
  interest_234B_risk: boolean,
  interest_234C_risk: boolean
}
```

---

### PRIMITIVE: CORP.IDENTITY_VERIFICATION
**Question:** Are the company's identity and registration details valid?
**Owns rules about:** PAN, CIN, DSC, and registration verification

```
[Note: Duplicates individual IDENTITY_VERIFICATION
 primitive intentionally — share-nothing policy.
 Corporate identity requirements differ significantly.]

INPUTS:
  company.PAN: string
  company.CIN: string [Corporate Identity Number]
  company.TAN: string [Tax Deduction Account Number]
  dsc.valid: boolean
  dsc.expiry: date
  gst.registration: string [if applicable]

RULES OWNED:
  Rule 1: IF company.PAN IS NULL
           THEN filing.blocked = TRUE
                consequence = ALERT_PAN_REQUIRED

  Rule 2: IF company.CIN IS NULL
             AND entity_type = DOMESTIC_COMPANY
           THEN filing.blocked = TRUE
                consequence = ALERT_CIN_REQUIRED

  Rule 3: IF company.TAN IS NULL
             AND tds_obligation.exists = TRUE
           THEN tds.filing.blocked = TRUE
                consequence = ALERT_TAN_REQUIRED

  Rule 4: IF dsc.valid = FALSE
             OR dsc.expiry < filing.due_date
           THEN itr6.filing.blocked = TRUE
                consequence = ALERT_DSC_INVALID_OR_EXPIRING

OUTPUTS: {
  pan_valid: boolean,
  cin_valid: boolean,
  tan_valid: boolean,
  dsc_valid: boolean,
  filing_cleared: boolean
}
```

---

# PART 3: DECISION TABLES

---

## DECISION TABLE 1: Tax Rate Determination

```
ONE TABLE — replaces 7 separate rate rules

INPUT PRIMITIVES:
  CORP.ENTITY_TYPE → entity_type
  CORP.REGIME_TRACK → regime_track
  CORP.TURNOVER_CATEGORY → turnover_category

┌──────────────────┬──────────────┬──────────────┬──────────┐
│  entity_type     │ regime_track │ turnover_cat  │ base_rate│
├──────────────────┼──────────────┼──────────────┼──────────┤
│ DOMESTIC_COMPANY │ STANDARD_30  │ ABOVE_400CR  │  30%     │
│ DOMESTIC_COMPANY │ STANDARD_25  │ BELOW_400CR  │  25%     │
│ DOMESTIC_COMPANY │ CONCESS_22   │ ANY          │  22%     │
│ DOMESTIC_COMPANY │ NEW_MFG_15   │ ANY          │  15%     │
│ FOREIGN_COMPANY  │ FOREIGN_35   │ FOREIGN      │  35%     │
│ LLP              │ LLP_30       │ LLP_FLAT_30  │  30%     │
│ DEEMED_DOMESTIC  │ ANY          │ ANY          │ [same as │
│                  │              │              │  domestic]│
└──────────────────┴──────────────┴──────────────┴──────────┘
```

---

## DECISION TABLE 2: Filing Form and Sequence

```
INPUT PRIMITIVES:
  CORP.ENTITY_TYPE → entity_type
  CORP.TAX_AUDIT_OBLIGATION → audit_required
  CORP.TRANSFER_PRICING_OBLIGATION → tp_required

┌──────────────┬───────────────┬─────────────┬──────────────────────┐
│ entity_type  │ audit_required│ tp_required │ sequence             │
├──────────────┼───────────────┼─────────────┼──────────────────────┤
│ ANY COMPANY  │ FALSE         │ FALSE       │ ITR-6 [Oct 31]       │
│ ANY COMPANY  │ TRUE          │ FALSE       │ 3CA/3CB+3CD [Sep 30] │
│              │               │             │ → ITR-6 [Oct 31]     │
│ ANY COMPANY  │ TRUE or FALSE │ TRUE        │ 3CEB [Oct 31]        │
│              │               │             │ → ITR-6 [Nov 30]     │
│ ANY COMPANY  │ TRUE          │ TRUE        │ 3CA/3CB+3CD [Sep 30] │
│              │               │             │ → 3CEB [Oct 31]      │
│              │               │             │ → ITR-6 [Nov 30]     │
└──────────────┴───────────────┴─────────────┴──────────────────────┘

SEQUENCE RULE: Each step is a CONTROL mode gate.
               Next step cannot begin until previous is filed.
               Verified against income tax portal status.
```

---

## DECISION TABLE 3: MAT vs Normal Tax Decision

```
INPUT PRIMITIVES:
  CORP.MAT_APPLICABILITY → mat_status
  CORP.FINAL_TAX_LIABILITY → {normal_tax, mat_liability}

┌──────────────────┬─────────────────────┬────────────────────────┐
│ mat_status       │ comparison          │ outcome                │
├──────────────────┼─────────────────────┼────────────────────────┤
│ MAT_EXEMPT       │ N/A                 │ Pay normal tax         │
│ MAT_APPLICABLE   │ normal > MAT        │ Pay normal tax         │
│                  │                     │ utilise MAT credit     │
│ MAT_APPLICABLE   │ MAT >= normal       │ Pay MAT                │
│                  │                     │ generate MAT credit    │
│ AMT_APPLICABLE   │ normal > AMT        │ Pay normal tax         │
│ AMT_APPLICABLE   │ AMT >= normal       │ Pay AMT                │
│                  │                     │ generate AMT credit    │
└──────────────────┴─────────────────────┴────────────────────────┘
```

---

# PART 4: MODULE CONTRACT

---

## CORPORATE TAX MODULE CONTRACT

```
MODULE_ID:      INDIA_CORPORATE_TAX
VERSION:        1.0
DOMAIN:         Corporate income tax — India
EFFECTIVE_FROM: Tax Year 2026-27 [1 April 2026]
APPROVED_BY:    [Chartered Accountant / Tax Expert sign-off required]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROVIDES [outputs available to other modules]:

  corp.entity_type
    Type: enum [DOMESTIC|FOREIGN|DEEMED_DOMESTIC|LLP]
    Used by: GST module, TDS module, MCA module

  corp.regime_track
    Type: enum [STANDARD_30|STANDARD_25|CONCESS_22|NEW_MFG_15|FOREIGN_35|LLP_30]
    Used by: Transfer Pricing module

  corp.tax_audit.required
    Type: boolean
    Used by: Audit Compliance module

  corp.tp.required
    Type: boolean
    Used by: Transfer Pricing module

  corp.tds.obligations[]
    Type: array [{section, rate, threshold}]
    Used by: TDS Compliance module

  corp.final_tax_liability
    Type: decimal
    Used by: Advance Tax module, Payment module

  corp.turnover
    Type: decimal
    Used by: GST module [for GST registration threshold check]

  corp.compliance_status
    Type: enum [COMPLIANT|PARTIAL|NON_COMPLIANT]
    Used by: Governance Layer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONSUMES [inputs needed from other modules]:

  FROM: GST Module [when available]
    gst.turnover
    Purpose: Cross-verify with corp.turnover for consistency
    Fallback: Use self-reported turnover if GST module unavailable
    Version dependency: GST_MODULE >= 1.0

  FROM: TDS Module [when available]
    tds.total_deducted_on_company
    Purpose: Offset against advance tax liability
    Fallback: Use Form 26AS data if TDS module unavailable
    Version dependency: TDS_MODULE >= 1.0

  FROM: MCA Module [when available]
    mca.incorporation_date
    mca.company_status [active/struck_off/dormant]
    Purpose: Validate entity type and 15% regime eligibility
    Fallback: Use self-declared data with alert
    Version dependency: MCA_MODULE >= 1.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FAILURE BEHAVIOUR:
  If GST Module unavailable:
    → Use self-reported turnover
    → Flag: CROSS_VERIFICATION_PENDING
    → Allow filing with alert

  If TDS Module unavailable:
    → Use Form 26AS data [portal fetch]
    → Flag: TDS_MODULE_OFFLINE
    → Allow filing with alert

  If MCA Module unavailable:
    → Use self-declared entity data
    → Flag: MCA_VERIFICATION_PENDING
    → Allow filing with alert
    → Post-filing verification required
```

---

# PART 5: CROSS-MODULE RULES

---

These rules live in the Governance Layer.
Not inside any single module.

```
CROSS-RULE 1: Turnover Consistency
  IF corp.turnover ≠ gst.turnover
     WITHIN tolerance of 5%
  THEN compliance.flag = TURNOVER_MISMATCH
       ALERT: both Corp Tax and GST teams
       BLOCK: ITR-6 filing until resolved or explained
  [Most common reconciliation issue in practice]

CROSS-RULE 2: TDS Expense Disallowance
  IF corp.tds.not_deducted_on_payment = TRUE
     AND payment.type IN [contractor, professional, rent]
  THEN corp.expense.disallowance_risk = TRUE
       corp.taxable_income += [30% of non-TDS payment]
       ALERT: finance team
  [Section 40a(ia) — significant tax impact]

CROSS-RULE 3: Loss Carry-Forward Filing Condition
  IF corp.loss.business > 0
     AND itr6.filed_date > itr6.due_date
  THEN corp.loss.carry_forward = BLOCKED
       consequence = ALERT_CRITICAL + ESCALATE
  [Irreversible — loss forfeited if return filed late]

CROSS-RULE 4: GST Audit Trigger from Corporate Turnover
  IF corp.turnover > 200_00_00_000 [₹200Cr]
  THEN gst.reconciliation_audit.recommended = TRUE
       ALERT: GST compliance team
  [Large corporates should reconcile GSTR-9C]

CROSS-RULE 5: Director's Tax Status vs Company Filing
  IF corp.director.income_tax_return.status = NOT_FILED
     AND itr6.filing.attempted = TRUE
  THEN compliance.flag = DIRECTOR_DEFAULT_FLAG
       ALERT: company secretary
  [Director default can affect company compliance status]
```

---

# PART 6: PRIMITIVE COUNT AND EXPLOSION INDEX

---

## Primitive Summary

```
GROUP                           COUNT
─────────────────────────────────────
Entity Classification               5
  [ENTITY_TYPE, PE_STATUS,
   TURNOVER_CATEGORY,
   INCORPORATION_DATE_STATUS,
   IFSC_STATUS]

Regime Determination                3
  [REGIME_TRACK,
   MAT_APPLICABILITY,
   DEDUCTION_ELIGIBILITY]

Income Computation                  2
  [TAXABLE_INCOME, BOOK_PROFIT]

MAT Credit                          1
  [MAT_CREDIT_POSITION]

Tax Computation                     3
  [BASE_TAX_RATE, SURCHARGE_RATE,
   FINAL_TAX_LIABILITY]

Audit and Compliance                3
  [TAX_AUDIT_OBLIGATION,
   TRANSFER_PRICING_OBLIGATION,
   TDS_OBLIGATION]

Process Compliance                  3
  [FILING_TIMELINE,
   ADVANCE_TAX_SCHEDULE,
   IDENTITY_VERIFICATION]
─────────────────────────────────────
TOTAL:                             20 primitives
```

---

## Combined System Explosion Index

```
                    Primitives   Change Set Risk
                    ──────────   ───────────────
ITR1 + ITR2             35           LOW
Corporate Tax           20           LOW-MEDIUM
─────────────────────────────────────────────────
Combined:               55 total

Shared primitives:       0
[Share-nothing policy — each module owns its own]

Cross-module rules:      5
[All live in governance layer]

EXPLOSION INDEX:
  Corporate-only change:     affects ~3-5 primitives   LOW
  Regime rate change:        affects ~4 primitives      LOW
  MAT rule change [FA2026]:  affects ~3 primitives      LOW
  TP threshold change:       affects ~1 primitive       LOW
  Cross-domain change:       affects ~8 primitives      MEDIUM
  [e.g. PAN rules change — both modules update]
```

---

## Why Corporate Tax Has Fewer Primitives Than ITR

```
ITR1/ITR2: 35 primitives for 2 forms, 2 regimes
Corporate:  20 primitives for more complexity

REASON: Corporate tax has fewer but deeper primitives.
        Each primitive owns more rules.
        Example:
          CORP.MAT_CREDIT_POSITION owns 6 complex rules
          vs
          ITR.DEDUCTION_80C owns 4 simpler rules

        Primitive COUNT is not the complexity measure.
        Rules per primitive is.

        Corporate tax primitives are individually
        more complex — but there are fewer of them
        because the decision structure is simpler:
        One form [ITR-6], one regime decision [irreversible],
        fewer personal variation factors.
```

---

# PART 7: KNOWN RISKS SPECIFIC TO CORPORATE TAX

---

## RISK 1: Regime Irreversibility
**Severity: CRITICAL**

Once a company opts for 22% or 15% regime,
it cannot revert. This is permanent.

The system must:
```
→ Warn explicitly before regime election
→ Require elevated approval [CFO/Board resolution]
→ Store election permanently and immutably
→ Block any future reversion attempt with escalation
→ Alert on all subsequent filings that regime is elected
```

This is not a rule problem — it is a governance problem.
The rule is simple. The consequence of getting it wrong is permanent.

---

## RISK 2: MAT Credit Expiry Management
**Severity: HIGH**

MAT credit expires after 15 years.
Finance Act 2026 changed utilisation rules mid-stream.
Companies with large MAT credit balances may
lose them if they switch regimes at the wrong time.

The system must:
```
→ Track MAT credit vintage [year-wise]
→ Alert 2-3 years before expiry
→ Model regime switch impact on MAT credit
→ Provide comparative analysis before regime decision
```

This is a planning decision, not just a compliance check.
The system should support the decision, not just enforce the rule.

---

## RISK 3: Transfer Pricing — Judgment-Dependent Rules
**Severity: HIGH**

Transfer pricing arm's length price determination
requires professional judgment. No algorithm can
determine if a related-party price is arm's length.

The system can:
```
→ Flag that TP documentation is required
→ Enforce filing sequence [3CEB before ITR-6]
→ Alert on threshold crossings
→ Track TP audit history
```

The system CANNOT:
```
→ Determine if the TP price is correct
→ Assess arm's length compliance
→ Replace CA certification
```

This boundary must be explicit in the product.

---

## RISK 4: DTAA Override
**Severity: MEDIUM**

Double Taxation Avoidance Agreements [DTAAs] with
specific countries can override domestic tax rules
for foreign companies. There are 90+ DTAAs.

The system must:
```
→ Flag when DTAA may apply [foreign company + specific income types]
→ Route to human review
→ Never apply DTAA provisions automatically
→ Store DTAA treaty used as part of audit trail
```

DTAA determination is always a human decision.
The system can trigger the question — not answer it.

---

## RISK 5: Finance Act 2026 Transition Complexity
**Severity: HIGH — Immediate**

Finance Act 2026 changed MAT from 15% to 14%.
It also changed MAT credit utilisation rules
with different implications for different company types.

This means for Tax Year 2026-27:
```
→ Some companies compute MAT at 14% [new rate]
→ Some need to evaluate MAT credit blocks [old regime companies]
→ Some need to model the 25% credit cap [switching companies]
→ All of this must coexist correctly in one system
```

Change set required:
```
CHANGE SET: FA2026_MAT_CHANGES
  CORP.MAT_APPLICABILITY v2 [14% rate]
  CORP.MAT_CREDIT_POSITION v2 [new utilisation rules]
  CORP.FINAL_TAX_LIABILITY v2 [updated computation]
  Activate atomically for Tax Year 2026-27
  Retain v1 for Tax Year 2025-26 revised returns
```

---

# PART 8: INSTRUCTIONS FOR CONTINUING

---

## What Has Been Defined
```
✅ Domain overview and entity types
✅ Full primitive set [20 primitives]
✅ Three decision tables
✅ Module contract [PROVIDES + CONSUMES]
✅ Five cross-module rules
✅ Explosion index
✅ Known risks
```

## What Comes Next

```
OPTION A: Build computation functions
          [Tax slab calculation, book profit computation,
           advance tax schedule generation]

OPTION B: Define the TDS module
          [Corporate TDS has its own module —
           CORP.TDS_OBLIGATION is just the obligation check.
           Actual TDS compliance is a separate module.]

OPTION C: Define the Transfer Pricing module
          [Separate module with own primitives]

OPTION D: Extend cross-module rules
          [Deeper integration with GST module]

OPTION E: Move to tech stack and implementation
          [Design database schema from objects]

OPTION F: Define objects from primitives
          [Rules-first → objects derivation,
           same as ITR system]
```

## Files Required to Continue

```
1. approach.md          [the architectural framework]
2. This file            [corporate tax approach]
3. ITR_Rule_System.md   [for cross-module context]
```

---

*Source: Income-tax Act 2025 [30 of 2025], Finance Act 2026,*
*CBDT notifications, PwC India Tax Summaries, incometax.gov.in*
*Applicable: Tax Year 2026-27 [1 April 2026 onwards]*
*Version 1.0 — May 2026*
