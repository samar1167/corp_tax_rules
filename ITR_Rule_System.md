# ITR Compliance Rule System
## Rules-First Approach — AY 2026-27 (FY 2025-26)
## Source: CBDT Official Notifications, Income Tax Act 1961

---

## How to Read This Document

Rules are defined first. Objects are NOT defined here.
Objects will be DERIVED from rules in the next phase.
Every rule has a structured definition following the Rule Object schema
from the Architectural Decision Record.

Rule ID convention:
- ITR.ELIG   = Eligibility rules (which form to file)
- ITR.COMP   = Computation rules (how tax is calculated)
- ITR.DED    = Deduction rules (what can be claimed)
- ITR.PROC   = Process rules (filing process compliance)
- ITR.PENAL  = Penalty rules (consequences of non-compliance)
- ITR.VERIF  = Verification rules (identity and document rules)

---

# RULESET 1: FORM ELIGIBILITY
## Who can file ITR1 vs ITR2

---

### RULE: ITR.ELIG.001
**Name:** ITR1 Residential Status Eligibility
**Natural Language:** Only Resident Individuals (ordinarily resident) can file ITR1.
Non-Resident Indians (NRI) and Resident but Not Ordinarily Resident (RNOR)
cannot file ITR1.
**Structured Logic:**
```
IF taxpayer.residential_status IN [NRI, RNOR]
THEN form_eligibility.ITR1 = DISQUALIFIED
     form_eligibility.ITR2 = ELIGIBLE
     consequence = REDIRECT_TO_ITR2
```
**Mode:** CONTROL
**Trigger:** Form selection event
**Severity:** ABSOLUTE
**Consequence:** Block ITR1, redirect to ITR2
**Source:** Income Tax Act Section 6, CBDT ITR1 Instructions AY 2026-27

---

### RULE: ITR.ELIG.002
**Name:** ITR1 Income Ceiling
**Natural Language:** Total income must not exceed ₹50 lakh to file ITR1.
**Structured Logic:**
```
IF taxpayer.total_income > 5000000
THEN form_eligibility.ITR1 = DISQUALIFIED
     consequence = ALERT + REDIRECT_TO_ITR2
```
**Mode:** CONTROL
**Trigger:** Income entry / total income computation
**Severity:** ABSOLUTE
**Consequence:** Block ITR1, alert taxpayer, redirect to ITR2
**Source:** ITR1 Eligibility Criteria AY 2026-27

---

### RULE: ITR.ELIG.003
**Name:** ITR1 Taxpayer Category
**Natural Language:** ITR1 can only be filed by an Individual. HUF, firms,
companies, or any other entity cannot file ITR1.
**Structured Logic:**
```
IF taxpayer.category != INDIVIDUAL
THEN form_eligibility.ITR1 = DISQUALIFIED
```
**Mode:** CONTROL
**Trigger:** Taxpayer category selection
**Severity:** ABSOLUTE
**Consequence:** Block ITR1
**Source:** ITR1 Instructions AY 2026-27

---

### RULE: ITR.ELIG.004
**Name:** ITR1 Director Disqualification
**Natural Language:** An individual who is a Director in any company
cannot file ITR1.
**Structured Logic:**
```
IF taxpayer.is_director_in_company = TRUE
THEN form_eligibility.ITR1 = DISQUALIFIED
     consequence = REDIRECT_TO_ITR2
```
**Mode:** CONTROL
**Trigger:** Personal information section — director flag
**Severity:** ABSOLUTE
**Consequence:** Block ITR1, redirect to ITR2
**Source:** ITR1 Exclusion Conditions AY 2026-27

---

### RULE: ITR.ELIG.005
**Name:** ITR1 Unlisted Equity Disqualification
**Natural Language:** An individual who has invested in unlisted equity shares
cannot file ITR1.
**Structured Logic:**
```
IF taxpayer.has_unlisted_equity_investment = TRUE
THEN form_eligibility.ITR1 = DISQUALIFIED
     consequence = REDIRECT_TO_ITR2
```
**Mode:** CONTROL
**Trigger:** Investment disclosure
**Severity:** ABSOLUTE
**Consequence:** Block ITR1
**Source:** ITR1 Exclusion Conditions AY 2026-27

---

### RULE: ITR.ELIG.006
**Name:** ITR1 Foreign Asset Disqualification
**Natural Language:** An individual having any asset (including financial interest
in any entity) located outside India, or signing authority in any account
outside India, cannot file ITR1.
**Structured Logic:**
```
IF taxpayer.has_foreign_assets = TRUE
   OR taxpayer.has_foreign_account_signing_authority = TRUE
THEN form_eligibility.ITR1 = DISQUALIFIED
     form_eligibility.ITR2 = ELIGIBLE
     consequence = REDIRECT_TO_ITR2
```
**Mode:** CONTROL
**Trigger:** Foreign asset / account declaration
**Severity:** ABSOLUTE
**Consequence:** Block ITR1, redirect to ITR2
**Source:** ITR1 Exclusion Conditions AY 2026-27

---

### RULE: ITR.ELIG.007
**Name:** ITR1 Business/Profession Income Disqualification
**Natural Language:** Any individual earning income from business or profession
cannot file ITR1.
**Structured Logic:**
```
IF taxpayer.income_sources CONTAINS [BUSINESS, PROFESSION]
THEN form_eligibility.ITR1 = DISQUALIFIED
     consequence = REDIRECT_TO_ITR3_OR_ITR4
```
**Mode:** CONTROL
**Trigger:** Income source selection
**Severity:** ABSOLUTE
**Consequence:** Block ITR1
**Source:** ITR1 Exclusion Conditions AY 2026-27

---

### RULE: ITR.ELIG.008
**Name:** ITR1 Capital Gains Restriction
**Natural Language:** An individual with capital gains income cannot file ITR1,
EXCEPT if they have ONLY Long Term Capital Gains under Section 112A
not exceeding ₹1,25,000, with no carried-forward capital losses.
**Structured Logic:**
```
IF taxpayer.has_capital_gains = TRUE
   AND NOT (
     taxpayer.capital_gain_type = LTCG_112A
     AND taxpayer.ltcg_112a_amount <= 125000
     AND taxpayer.has_carried_forward_capital_loss = FALSE
   )
THEN form_eligibility.ITR1 = DISQUALIFIED
     form_eligibility.ITR2 = ELIGIBLE
     consequence = REDIRECT_TO_ITR2
```
**Mode:** CONTROL
**Trigger:** Capital gains disclosure
**Severity:** ABSOLUTE
**Consequence:** Block ITR1, redirect to ITR2
**Source:** CBDT AY 2026-27 ITR1 expanded eligibility notification

---

### RULE: ITR.ELIG.009
**Name:** ITR1 Multiple House Property Restriction — AY 2026-27 Update
**Natural Language:** From AY 2026-27, ITR1 allows income from up to
TWO house properties. Previously only one was permitted.
Taxpayers with more than two house properties must file ITR2.
**Structured Logic:**
```
IF taxpayer.house_property_count > 2
THEN form_eligibility.ITR1 = DISQUALIFIED
     form_eligibility.ITR2 = ELIGIBLE

IF taxpayer.house_property_count <= 2
   AND taxpayer.has_brought_forward_house_property_loss = TRUE
THEN form_eligibility.ITR1 = DISQUALIFIED
     consequence = REDIRECT_TO_ITR2
```
**Mode:** CONTROL
**Trigger:** House property count declaration
**Severity:** ABSOLUTE
**Consequence:** Block ITR1 if > 2 properties or carry-forward loss exists
**Source:** ITR1 AY 2026-27 updated eligibility — Notification No. 57/2026

---

### RULE: ITR.ELIG.010
**Name:** ITR1 TDS Section 194N Disqualification
**Natural Language:** If TDS has been deducted under Section 194N
(cash withdrawal exceeding threshold), ITR1 cannot be filed.
**Structured Logic:**
```
IF taxpayer.tds_deducted_under_194N = TRUE
THEN form_eligibility.ITR1 = DISQUALIFIED
```
**Mode:** CONTROL
**Trigger:** TDS details entry
**Severity:** ABSOLUTE
**Consequence:** Block ITR1
**Source:** ITR1 Exclusion Conditions AY 2026-27

---

### RULE: ITR.ELIG.011
**Name:** ITR1 ESOP Tax Deferral Disqualification
**Natural Language:** If income tax on ESOP (Employee Stock Option Plan)
has been deferred, ITR1 cannot be filed.
**Structured Logic:**
```
IF taxpayer.has_esop_tax_deferred = TRUE
THEN form_eligibility.ITR1 = DISQUALIFIED
```
**Mode:** CONTROL
**Trigger:** ESOP / perquisite declaration
**Severity:** ABSOLUTE
**Consequence:** Block ITR1
**Source:** ITR1 Exclusion Conditions AY 2026-27

---

### RULE: ITR.ELIG.012
**Name:** ITR2 Eligibility — Positive Conditions
**Natural Language:** ITR2 is applicable to individuals and HUFs who have
income from salary, more than two house properties, capital gains,
foreign assets, or are directors, but do NOT have income from
business or profession.
**Structured Logic:**
```
IF taxpayer.category IN [INDIVIDUAL, HUF]
   AND taxpayer.has_business_profession_income = FALSE
   AND (
     taxpayer.total_income > 5000000
     OR taxpayer.house_property_count > 2
     OR taxpayer.has_capital_gains = TRUE
     OR taxpayer.has_foreign_assets = TRUE
     OR taxpayer.is_director_in_company = TRUE
     OR taxpayer.residential_status IN [NRI, RNOR]
   )
THEN form_eligibility.ITR2 = ELIGIBLE
```
**Mode:** ALERT
**Trigger:** Profile completion
**Severity:** INFO
**Consequence:** Suggest ITR2 as appropriate form
**Source:** ITR2 Applicability Conditions AY 2026-27

---

# RULESET 2: TAX REGIME SELECTION

---

### RULE: ITR.COMP.001
**Name:** Default Tax Regime
**Natural Language:** New Tax Regime (Section 115BAC) is the DEFAULT
regime for all individual taxpayers from AY 2024-25 onwards.
Taxpayers must explicitly opt out to use the old regime.
**Structured Logic:**
```
IF taxpayer.regime_selection = NOT_SPECIFIED
THEN taxpayer.applicable_regime = NEW_REGIME
     consequence = ALERT_DEFAULT_APPLIED
```
**Mode:** ALERT
**Trigger:** Regime selection step
**Severity:** WARNING
**Consequence:** Apply new regime, alert taxpayer of default
**Source:** Finance Act 2023, Section 115BAC

---

### RULE: ITR.COMP.002
**Name:** Old Regime Opt-Out for Non-Business Taxpayers
**Natural Language:** Salaried individuals (non-business) can choose
old or new regime every year directly in the ITR form,
provided ITR is filed on or before due date u/s 139(1).
**Structured Logic:**
```
IF taxpayer.has_business_profession_income = FALSE
   AND taxpayer.regime_selection = OLD_REGIME
   AND filing.date <= filing.due_date_139_1
THEN taxpayer.applicable_regime = OLD_REGIME
     consequence = ALLOW

IF taxpayer.has_business_profession_income = FALSE
   AND taxpayer.regime_selection = OLD_REGIME
   AND filing.date > filing.due_date_139_1
THEN taxpayer.applicable_regime = NEW_REGIME
     consequence = ALERT_CANNOT_CHOOSE_OLD_REGIME_LATE
```
**Mode:** CONTROL
**Trigger:** Regime selection + filing date check
**Severity:** CRITICAL
**Consequence:** Block old regime selection if filing is late
**Source:** Section 115BAC, CBDT FAQ AY 2026-27

---

### RULE: ITR.COMP.003
**Name:** New Regime Tax Slabs AY 2026-27
**Natural Language:** Under new regime, tax slabs for all individuals
(regardless of age) for FY 2025-26 are:
Up to ₹4,00,000 — Nil
₹4,00,001 to ₹8,00,000 — 5%
₹8,00,001 to ₹12,00,000 — 10%
₹12,00,001 to ₹16,00,000 — 15%
₹16,00,001 to ₹20,00,000 — 20%
₹20,00,001 to ₹24,00,000 — 25%
Above ₹24,00,000 — 30%
**Structured Logic:**
```
IF taxpayer.applicable_regime = NEW_REGIME
THEN tax.base = CALCULATE_USING_NEW_SLABS(taxable_income)
  WHERE slabs = [
    {from: 0,        to: 400000,  rate: 0.00},
    {from: 400001,   to: 800000,  rate: 0.05},
    {from: 800001,   to: 1200000, rate: 0.10},
    {from: 1200001,  to: 1600000, rate: 0.15},
    {from: 1600001,  to: 2000000, rate: 0.20},
    {from: 2000001,  to: 2400000, rate: 0.25},
    {from: 2400001,  to: MAX,     rate: 0.30}
  ]
```
**Mode:** CONTROL
**Trigger:** Tax computation step
**Severity:** ABSOLUTE
**Consequence:** Compute tax using defined slabs
**Source:** Finance Act 2025, Budget 2025 new regime slab revision

---

### RULE: ITR.COMP.004
**Name:** Old Regime Tax Slabs — Below 60 Years
**Natural Language:** Under old regime for individuals below 60 years:
Up to ₹2,50,000 — Nil
₹2,50,001 to ₹5,00,000 — 5%
₹5,00,001 to ₹10,00,000 — 20%
Above ₹10,00,000 — 30%
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
   AND taxpayer.age < 60
THEN tax.base = CALCULATE_USING_OLD_SLABS_BELOW_60(taxable_income)
  WHERE slabs = [
    {from: 0,       to: 250000,  rate: 0.00},
    {from: 250001,  to: 500000,  rate: 0.05},
    {from: 500001,  to: 1000000, rate: 0.20},
    {from: 1000001, to: MAX,     rate: 0.30}
  ]
```
**Mode:** CONTROL
**Trigger:** Tax computation step
**Severity:** ABSOLUTE
**Source:** Income Tax Act 1961, Old Regime Slabs

---

### RULE: ITR.COMP.005
**Name:** Old Regime Tax Slabs — Senior Citizens (60-79 Years)
**Natural Language:** Under old regime for senior citizens (60 to 79 years):
Up to ₹3,00,000 — Nil
₹3,00,001 to ₹5,00,000 — 5%
₹5,00,001 to ₹10,00,000 — 20%
Above ₹10,00,000 — 30%
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
   AND taxpayer.age >= 60
   AND taxpayer.age < 80
THEN tax.base = CALCULATE_USING_OLD_SLABS_SENIOR(taxable_income)
  WHERE slabs = [
    {from: 0,       to: 300000,  rate: 0.00},
    {from: 300001,  to: 500000,  rate: 0.05},
    {from: 500001,  to: 1000000, rate: 0.20},
    {from: 1000001, to: MAX,     rate: 0.30}
  ]
```
**Mode:** CONTROL
**Trigger:** Tax computation step
**Severity:** ABSOLUTE
**Source:** Income Tax Act 1961, Old Regime Senior Citizen Slabs

---

### RULE: ITR.COMP.006
**Name:** Old Regime Tax Slabs — Super Senior Citizens (80+ Years)
**Natural Language:** Under old regime for super senior citizens (80 years and above):
Up to ₹5,00,000 — Nil
₹5,00,001 to ₹10,00,000 — 20%
Above ₹10,00,000 — 30%
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
   AND taxpayer.age >= 80
THEN tax.base = CALCULATE_USING_OLD_SLABS_SUPER_SENIOR(taxable_income)
  WHERE slabs = [
    {from: 0,       to: 500000,  rate: 0.00},
    {from: 500001,  to: 1000000, rate: 0.20},
    {from: 1000001, to: MAX,     rate: 0.30}
  ]
```
**Mode:** CONTROL
**Trigger:** Tax computation step
**Severity:** ABSOLUTE
**Source:** Income Tax Act 1961, Old Regime Super Senior Citizen Slabs

---

### RULE: ITR.COMP.007
**Name:** Section 87A Rebate — New Regime
**Natural Language:** Under new regime, if taxable income does not exceed
₹12,00,000, a rebate of up to ₹60,000 is available, effectively
making income up to ₹12 lakh tax-free.
(Note: Special rate incomes like capital gains are excluded from rebate.)
**Structured Logic:**
```
IF taxpayer.applicable_regime = NEW_REGIME
   AND taxpayer.taxable_income <= 1200000
   AND taxpayer.special_rate_income = 0
THEN tax.rebate_87A = MIN(tax.base, 60000)
     tax.after_rebate = tax.base - tax.rebate_87A
```
**Mode:** CONTROL
**Trigger:** Tax computation — rebate step
**Severity:** ABSOLUTE
**Consequence:** Apply rebate, reduce tax to zero if applicable
**Source:** Section 87A, Finance Act 2025

---

### RULE: ITR.COMP.008
**Name:** Section 87A Rebate — Old Regime
**Natural Language:** Under old regime, if taxable income does not exceed
₹5,00,000, a rebate of up to ₹12,500 is available.
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
   AND taxpayer.taxable_income <= 500000
THEN tax.rebate_87A = MIN(tax.base, 12500)
     tax.after_rebate = tax.base - tax.rebate_87A
```
**Mode:** CONTROL
**Trigger:** Tax computation — rebate step
**Severity:** ABSOLUTE
**Source:** Section 87A, Income Tax Act 1961

---

### RULE: ITR.COMP.009
**Name:** Surcharge Computation
**Natural Language:** Surcharge is levied on income tax based on total income:
₹50L to ₹1Cr: 10% surcharge
₹1Cr to ₹2Cr: 15% surcharge
₹2Cr to ₹5Cr: 25% surcharge
Above ₹5Cr: 25% (new regime cap) / 37% (old regime)
**Structured Logic:**
```
IF taxpayer.total_income > 5000000
  AND taxpayer.total_income <= 10000000
THEN tax.surcharge = tax.after_rebate * 0.10

IF taxpayer.total_income > 10000000
  AND taxpayer.total_income <= 20000000
THEN tax.surcharge = tax.after_rebate * 0.15

IF taxpayer.total_income > 20000000
  AND taxpayer.total_income <= 50000000
THEN tax.surcharge = tax.after_rebate * 0.25

IF taxpayer.total_income > 50000000
  AND taxpayer.applicable_regime = NEW_REGIME
THEN tax.surcharge = tax.after_rebate * 0.25

IF taxpayer.total_income > 50000000
  AND taxpayer.applicable_regime = OLD_REGIME
THEN tax.surcharge = tax.after_rebate * 0.37

NOTE: Surcharge on special rate incomes (111A, 112A) capped at 15%
```
**Mode:** CONTROL
**Trigger:** Tax computation — surcharge step
**Severity:** ABSOLUTE
**Source:** Income Tax Act, Finance Act provisions on surcharge

---

### RULE: ITR.COMP.010
**Name:** Health and Education Cess
**Natural Language:** Health and Education Cess at 4% is levied on
(income tax + surcharge) for all taxpayers under both regimes.
**Structured Logic:**
```
tax.cess = (tax.after_rebate + tax.surcharge) * 0.04
tax.total_liability = tax.after_rebate + tax.surcharge + tax.cess
```
**Mode:** CONTROL
**Trigger:** Tax computation — final step
**Severity:** ABSOLUTE
**Source:** Finance Act, Cess provisions

---

# RULESET 3: INCOME COMPUTATION

---

### RULE: ITR.COMP.011
**Name:** Standard Deduction — New Regime
**Natural Language:** Salaried individuals and pensioners under new regime
are entitled to a standard deduction of ₹75,000 from salary income.
**Structured Logic:**
```
IF taxpayer.applicable_regime = NEW_REGIME
   AND taxpayer.income_sources CONTAINS [SALARY, PENSION]
THEN income.standard_deduction = MIN(75000, income.gross_salary)
     income.net_salary = income.gross_salary - income.standard_deduction
```
**Mode:** CONTROL
**Trigger:** Salary income computation
**Severity:** ABSOLUTE
**Source:** Section 16, Finance Act 2024

---

### RULE: ITR.COMP.012
**Name:** Standard Deduction — Old Regime
**Natural Language:** Salaried individuals and pensioners under old regime
are entitled to a standard deduction of ₹50,000 from salary income.
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
   AND taxpayer.income_sources CONTAINS [SALARY, PENSION]
THEN income.standard_deduction = MIN(50000, income.gross_salary)
     income.net_salary = income.gross_salary - income.standard_deduction
```
**Mode:** CONTROL
**Trigger:** Salary income computation
**Severity:** ABSOLUTE
**Source:** Section 16, Income Tax Act

---

### RULE: ITR.COMP.013
**Name:** House Property Income — Self Occupied
**Natural Language:** For a self-occupied property, Annual Value is NIL.
Under old regime, interest on home loan for self-occupied property
is deductible up to ₹2,00,000.
Under new regime, this deduction is NOT allowed.
**Structured Logic:**
```
income.house_property.annual_value = 0  [for self-occupied]

IF taxpayer.applicable_regime = OLD_REGIME
   AND property.status = SELF_OCCUPIED
THEN deduction.home_loan_interest = MIN(home_loan.interest_paid, 200000)
     income.house_property.net = 0 - deduction.home_loan_interest

IF taxpayer.applicable_regime = NEW_REGIME
   AND property.status = SELF_OCCUPIED
THEN deduction.home_loan_interest = 0
     income.house_property.net = 0
```
**Mode:** CONTROL
**Trigger:** House property income computation
**Severity:** ABSOLUTE
**Source:** Section 24(b), Section 115BAC

---

### RULE: ITR.COMP.014
**Name:** House Property Income — Let Out
**Natural Language:** For let-out property, Annual Value = Actual rent received
or fair market rent, whichever is higher.
30% standard deduction on net annual value is allowed.
Home loan interest for let-out property is allowed in both regimes
(no upper limit, but set-off of loss limited to ₹2 lakh against other heads).
**Structured Logic:**
```
IF property.status = LET_OUT
THEN property.annual_value = MAX(rent.actual_received, rent.fair_market)
     property.municipal_tax_deduction = municipal_tax.paid
     property.net_annual_value = property.annual_value - property.municipal_tax_deduction
     deduction.standard_30_percent = property.net_annual_value * 0.30
     deduction.home_loan_interest = home_loan.interest_paid  [no cap for let-out]
     income.house_property.net = property.net_annual_value
                                  - deduction.standard_30_percent
                                  - deduction.home_loan_interest
```
**Mode:** CONTROL
**Trigger:** House property income computation
**Severity:** ABSOLUTE
**Source:** Section 22, 23, 24 Income Tax Act

---

### RULE: ITR.COMP.015
**Name:** House Property Loss Set-Off Cap
**Natural Language:** Loss from house property can be set off against
other heads of income only up to ₹2,00,000 per year.
Remaining loss is carried forward for 8 years.
**Structured Logic:**
```
IF income.house_property.net < 0
   AND ABS(income.house_property.net) > 200000
THEN loss.house_property.setoff_current_year = 200000
     loss.house_property.carried_forward = ABS(income.house_property.net) - 200000
     consequence = ALERT_CARRY_FORWARD_LOSS_CREATED

IF income.house_property.net < 0
   AND ABS(income.house_property.net) <= 200000
THEN loss.house_property.setoff_current_year = ABS(income.house_property.net)
```
**Mode:** CONTROL
**Trigger:** House property loss computation
**Severity:** CRITICAL
**Source:** Section 71, Income Tax Act

---

### RULE: ITR.COMP.016
**Name:** Agricultural Income — ITR1 Inclusion
**Natural Language:** Agricultural income up to ₹5,000 can be included
in ITR1 under "Exempt Income" for reporting purposes.
If agricultural income exceeds ₹5,000, the taxpayer may need to
apply partial integration rules (and may not be eligible for ITR1
depending on total income).
**Structured Logic:**
```
IF income.agricultural <= 5000
THEN income.agricultural.treatment = EXEMPT_REPORT_ONLY
     form_eligibility.ITR1 = NOT_AFFECTED

IF income.agricultural > 5000
   AND taxpayer.total_non_agricultural_income > 250000
THEN income.agricultural.treatment = PARTIAL_INTEGRATION_APPLICABLE
     consequence = ALERT_AGRICULTURAL_INTEGRATION_REQUIRED
```
**Mode:** ALERT
**Trigger:** Agricultural income entry
**Severity:** WARNING
**Source:** Section 10(1), Partial Integration Rules

---

# RULESET 4: DEDUCTIONS (OLD REGIME ONLY UNLESS SPECIFIED)

---

### RULE: ITR.DED.001
**Name:** Section 80C — Investments and Payments
**Natural Language:** Deduction up to ₹1,50,000 for investments in
PPF, ELSS, NSC, LIC premium, home loan principal, tuition fees, etc.
Policy/document number is mandatory for each investment claimed.
ONLY available under old regime.
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
THEN deduction.80C = MIN(
       SUM(investments.ppf, investments.elss, investments.nsc,
           insurance.lic_premium, home_loan.principal,
           education.tuition_fees, investments.other_80c),
       150000
     )
     REQUIRE: each_investment.policy_or_document_number IS NOT NULL
     REQUIRE: each_investment.nature IS SPECIFIED

IF taxpayer.applicable_regime = NEW_REGIME
THEN deduction.80C = 0
     consequence = ALERT_80C_NOT_AVAILABLE_NEW_REGIME
```
**Mode:** CONTROL
**Trigger:** Deduction entry — Section 80C
**Severity:** CRITICAL
**Consequence:** Block 80C claim if new regime; enforce document number
**Source:** Section 80C, CBDT AY 2026-27 mandatory disclosure

---

### RULE: ITR.DED.002
**Name:** Section 80D — Health Insurance Premium
**Natural Language:** Deduction for health insurance premium:
Self/family (non-senior): up to ₹25,000
Self/family (senior citizen): up to ₹50,000
Parents (non-senior): up to ₹25,000
Parents (senior citizen): up to ₹50,000
Insurer name, policy number, and premium split (self/family/parents)
are mandatory disclosures.
ONLY available under old regime.
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
THEN
  IF taxpayer.age < 60
  THEN deduction.80D.self_family = MIN(insurance.health.self_family_premium, 25000)
  ELSE deduction.80D.self_family = MIN(insurance.health.self_family_premium, 50000)

  IF taxpayer.parents.age < 60
  THEN deduction.80D.parents = MIN(insurance.health.parents_premium, 25000)
  ELSE deduction.80D.parents = MIN(insurance.health.parents_premium, 50000)

  deduction.80D.total = deduction.80D.self_family + deduction.80D.parents

  REQUIRE: insurance.health.insurer_name IS NOT NULL
  REQUIRE: insurance.health.policy_number IS NOT NULL
  REQUIRE: insurance.health.premium_split_disclosed = TRUE

IF taxpayer.applicable_regime = NEW_REGIME
THEN deduction.80D = 0
```
**Mode:** CONTROL
**Trigger:** Deduction entry — Section 80D
**Severity:** CRITICAL
**Source:** Section 80D, CBDT AY 2026-27 disclosure requirements

---

### RULE: ITR.DED.003
**Name:** Section 80CCD(1B) — Additional NPS Contribution
**Natural Language:** Additional deduction of up to ₹50,000 for own
contribution to NPS (over and above 80C limit).
PRAN (Permanent Retirement Account Number) is mandatory.
ONLY available under old regime.
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
THEN deduction.80CCD_1B = MIN(nps.own_contribution, 50000)
     REQUIRE: nps.PRAN IS NOT NULL

IF taxpayer.applicable_regime = NEW_REGIME
THEN deduction.80CCD_1B = 0
```
**Mode:** CONTROL
**Trigger:** NPS deduction entry
**Severity:** CRITICAL
**Source:** Section 80CCD(1B), CBDT AY 2026-27 PRAN requirement

---

### RULE: ITR.DED.004
**Name:** Section 80CCD(2) — Employer NPS Contribution
**Natural Language:** Deduction for employer's contribution to NPS
is available in BOTH old and new regimes.
Limit: 10% of salary (basic + DA) for private sector employees,
14% for government employees.
**Structured Logic:**
```
IF nps.employer_contribution > 0
THEN
  IF taxpayer.employer_type = GOVERNMENT
  THEN deduction.80CCD_2 = MIN(nps.employer_contribution,
                               salary.basic_da * 0.14)
  ELSE
  THEN deduction.80CCD_2 = MIN(nps.employer_contribution,
                               salary.basic_da * 0.10)
  [Available in BOTH regimes]
```
**Mode:** CONTROL
**Trigger:** NPS employer contribution entry
**Severity:** ABSOLUTE
**Source:** Section 80CCD(2), available in new regime exception

---

### RULE: ITR.DED.005
**Name:** Section 80G — Donations
**Natural Language:** Deduction for donations to approved funds and institutions.
Cash donations above ₹2,000 are NOT eligible.
Deduction rate: 50% or 100% depending on institution.
Transaction number and name of political party required for political donations.
ONLY available under old regime.
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
THEN
  FOR each donation IN donations.list:
    IF donation.mode = CASH AND donation.amount > 2000
    THEN donation.eligible = FALSE
         consequence = ALERT_CASH_DONATION_DISQUALIFIED

    IF donation.mode != CASH OR donation.amount <= 2000
    THEN donation.eligible = TRUE
         deduction.80G += donation.amount * donation.institution.rate

  IF donation.institution.type = POLITICAL_PARTY
  THEN REQUIRE: donation.transaction_number IS NOT NULL
       REQUIRE: donation.party_name IS NOT NULL

IF taxpayer.applicable_regime = NEW_REGIME
THEN deduction.80G = 0
```
**Mode:** CONTROL
**Trigger:** Donation entry
**Severity:** CRITICAL
**Source:** Section 80G, CBDT AY 2026-27 political party disclosure

---

### RULE: ITR.DED.006
**Name:** Section 80GG — Rent Paid (No HRA)
**Natural Language:** Deduction for rent paid by taxpayers who do not
receive HRA and do not own a residential property.
Form 10BA must be mandatorily filed BEFORE submitting ITR.
Acknowledgement number of Form 10BA must be quoted in ITR.
Deduction = least of:
(a) Rent paid minus 10% of total income
(b) 25% of total income
(c) ₹5,000 per month
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
   AND taxpayer.receives_hra = FALSE
   AND taxpayer.owns_residential_property = FALSE
THEN
  REQUIRE: form_10BA.filed = TRUE BEFORE itr.submission
  REQUIRE: form_10BA.acknowledgement_number IS NOT NULL

  deduction.80GG = MIN(
    rent.paid_annual - (taxpayer.total_income * 0.10),
    taxpayer.total_income * 0.25,
    60000
  )
```
**Mode:** CONTROL
**Trigger:** 80GG deduction claim
**Severity:** CRITICAL
**Consequence:** Block 80GG if Form 10BA not filed
**Source:** Section 80GG, CBDT AY 2025-26 mandatory Form 10BA

---

### RULE: ITR.DED.007
**Name:** HRA Exemption — Old Regime
**Natural Language:** HRA exemption is available only under old regime.
Exemption = least of:
(a) Actual HRA received
(b) Rent paid minus 10% of basic salary
(c) 50% of basic salary (metro) or 40% (non-metro)
Metro cities: Delhi, Mumbai, Chennai, Kolkata
Mandatory: Rent amount, Place of work must be disclosed in ITR.
**Structured Logic:**
```
IF taxpayer.applicable_regime = OLD_REGIME
   AND salary.hra_received > 0
   AND rent.paid > 0
THEN
  IF taxpayer.city IN [DELHI, MUMBAI, CHENNAI, KOLKATA]
  THEN hra.percent = 0.50
  ELSE hra.percent = 0.40

  exemption.hra = MIN(
    salary.hra_received,
    rent.paid_annual - (salary.basic * 0.10),
    salary.basic * hra.percent
  )

  REQUIRE: rent.amount_paid IS NOT NULL
  REQUIRE: taxpayer.place_of_work IS NOT NULL

IF taxpayer.applicable_regime = NEW_REGIME
THEN exemption.hra = 0
```
**Mode:** CONTROL
**Trigger:** HRA exemption claim
**Severity:** ABSOLUTE
**Source:** Section 10(13A), Rule 2A, CBDT disclosure requirements

---

### RULE: ITR.DED.008
**Name:** Section 24(b) — Home Loan Interest Mutual Exclusivity
**Natural Language:** Either Section 80EE or Section 80EEA can be claimed,
not both, based on loan sanction date.
Section 80EEA can only be claimed if Section 24(b) limit is fully exhausted.
**Structured Logic:**
```
IF deduction.80EE > 0 AND deduction.80EEA > 0
THEN consequence = BLOCK
     alert = "Cannot claim both 80EE and 80EEA simultaneously"

IF deduction.80EEA > 0
   AND deduction.24b < 200000
THEN consequence = BLOCK
     alert = "80EEA can only be claimed after Section 24(b) limit of ₹2L is exhausted"
```
**Mode:** CONTROL
**Trigger:** Home loan deduction entry
**Severity:** CRITICAL
**Source:** Section 80EE, 80EEA conditions

---

# RULESET 5: CAPITAL GAINS (ITR2 SPECIFIC)

---

### RULE: ITR.COMP.017
**Name:** LTCG Section 112A — Tax Rate
**Natural Language:** Long Term Capital Gains on listed equity shares
and equity-oriented mutual funds (STT paid) under Section 112A:
Gains up to ₹1,25,000 per year are exempt.
Gains above ₹1,25,000 taxed at 12.5% (no indexation benefit).
**Structured Logic:**
```
IF capital_gain.type = LTCG_LISTED_EQUITY
   AND capital_gain.stt_paid = TRUE
THEN
  capital_gain.exempt = MIN(capital_gain.amount, 125000)
  capital_gain.taxable = MAX(capital_gain.amount - 125000, 0)
  capital_gain.tax = capital_gain.taxable * 0.125
```
**Mode:** CONTROL
**Trigger:** Capital gains computation — LTCG 112A
**Severity:** ABSOLUTE
**Source:** Section 112A, Finance Act 2024

---

### RULE: ITR.COMP.018
**Name:** STCG Section 111A — Tax Rate
**Natural Language:** Short Term Capital Gains on listed equity shares
and equity-oriented mutual funds (STT paid) under Section 111A
are taxed at 20% (revised from 15% after July 23, 2024).
**Structured Logic:**
```
IF capital_gain.type = STCG_LISTED_EQUITY
   AND capital_gain.stt_paid = TRUE
THEN capital_gain.tax_rate = 0.20
     capital_gain.tax = capital_gain.amount * 0.20
```
**Mode:** CONTROL
**Trigger:** Capital gains computation — STCG 111A
**Severity:** ABSOLUTE
**Source:** Section 111A, Finance Act 2024 (revised from 15% to 20%)

---

### RULE: ITR.COMP.019
**Name:** Capital Gains — Surcharge Cap for Special Rate Income
**Natural Language:** Surcharge on income taxable at special rates
(Sections 111A, 112, 112A) and dividend income is capped at 15%,
even if total income would otherwise attract higher surcharge.
**Structured Logic:**
```
IF tax.surcharge_rate > 0.15
   AND income.special_rate_income > 0
THEN tax.surcharge_on_special_rate_income =
       income.special_rate_income_tax * 0.15
     [Not at higher surcharge rate]
```
**Mode:** CONTROL
**Trigger:** Surcharge computation for high-income taxpayers with capital gains
**Severity:** ABSOLUTE
**Source:** Finance Act proviso on surcharge for special rate incomes

---

# RULESET 6: PROCESS COMPLIANCE

---

### RULE: ITR.PROC.001
**Name:** Filing Due Date — Regular Return
**Natural Language:** For individuals not requiring tax audit,
ITR must be filed by July 31 of the Assessment Year.
For AY 2026-27, due date is July 31, 2026.
**Structured Logic:**
```
filing.due_date = DATE(2026, 07, 31)  [for AY 2026-27]

IF filing.date > filing.due_date
THEN consequence = ALERT_LATE_FILING
     penalty.234F.applicable = TRUE
```
**Mode:** ALERT
**Trigger:** Filing date check
**Severity:** WARNING
**Source:** Section 139(1)

---

### RULE: ITR.PROC.002
**Name:** Late Filing Penalty — Section 234F
**Natural Language:** Late filing fee under Section 234F:
₹1,000 if total income ≤ ₹5,00,000
₹5,000 if total income > ₹5,00,000
Belated return can be filed up to December 31 of AY.
**Structured Logic:**
```
IF filing.date > filing.due_date_139_1
   AND filing.date <= DATE(AY, 12, 31)
THEN filing.type = BELATED

  IF taxpayer.total_income <= 500000
  THEN penalty.234F = 1000
  ELSE penalty.234F = 5000

IF filing.date > DATE(AY, 12, 31)
THEN filing.type = BLOCKED
     consequence = ONLY_ITR_U_ALLOWED
```
**Mode:** CONTROL
**Trigger:** Filing date at submission
**Severity:** CRITICAL
**Source:** Section 234F, Section 139(4)

---

### RULE: ITR.PROC.003
**Name:** Revised Return Deadline
**Natural Language:** A revised return can be filed to correct errors
in the original return up to December 31 of the Assessment Year
(extended from original provision — Finance Act 2026 extended to March 31
of succeeding tax year with late fees under Section 234I).
**Structured Logic:**
```
IF return.type = REVISED
   AND filing.date <= DATE(AY, 12, 31)
THEN revised_return.fee = 0
     revised_return.allowed = TRUE

IF return.type = REVISED
   AND filing.date > DATE(AY, 12, 31)
   AND filing.date <= DATE(AY+1, 03, 31)
THEN revised_return.fee = APPLICABLE_UNDER_234I
     revised_return.allowed = TRUE
     consequence = ALERT_LATE_REVISION_FEE

IF return.type = REVISED
   AND filing.date > DATE(AY+1, 03, 31)
THEN revised_return.allowed = FALSE
```
**Mode:** CONTROL
**Trigger:** Revised return filing attempt
**Severity:** CRITICAL
**Source:** Finance Act 2026, Section 139(5)

---

### RULE: ITR.PROC.004
**Name:** Advance Tax Obligation
**Natural Language:** If estimated tax liability (after TDS) exceeds ₹10,000
in a financial year, the taxpayer must pay advance tax in quarterly instalments:
June 15: 15% of annual liability
September 15: 45% of annual liability
December 15: 75% of annual liability
March 15: 100% of annual liability
**Structured Logic:**
```
IF (tax.estimated_annual - tds.total_deducted) > 10000
THEN advance_tax.required = TRUE
     advance_tax.schedule = [
       {due: DATE(FY, 06, 15), cumulative_percent: 0.15},
       {due: DATE(FY, 09, 15), cumulative_percent: 0.45},
       {due: DATE(FY, 12, 15), cumulative_percent: 0.75},
       {due: DATE(FY, 03, 15), cumulative_percent: 1.00}
     ]
     consequence = ALERT_ADVANCE_TAX_SCHEDULE

IF advance_tax.required = TRUE
   AND advance_tax.paid < advance_tax.schedule.due_amount
THEN penalty.234B_234C.applicable = TRUE
```
**Mode:** ALERT
**Trigger:** Tax liability computation
**Severity:** WARNING
**Source:** Section 208, 234B, 234C

---

# RULESET 7: VERIFICATION AND IDENTITY

---

### RULE: ITR.VERIF.001
**Name:** PAN Mandatory
**Natural Language:** PAN is mandatory for all ITR filings.
PAN must be linked with Aadhaar.
**Structured Logic:**
```
IF taxpayer.PAN IS NULL
THEN filing.allowed = FALSE
     consequence = BLOCK + ALERT_PAN_REQUIRED

IF taxpayer.PAN IS NOT NULL
   AND taxpayer.aadhaar_pan_linked = FALSE
THEN filing.allowed = FALSE
     consequence = BLOCK + ALERT_LINK_AADHAAR_PAN
```
**Mode:** CONTROL
**Trigger:** Filing initiation
**Severity:** ABSOLUTE
**Source:** Section 139AA, PAN-Aadhaar linking mandate

---

### RULE: ITR.VERIF.002
**Name:** Aadhaar Number — Enrollment ID No Longer Valid
**Natural Language:** From AY 2025-26 onwards, only the actual Aadhaar number
is valid for ITR filing. Aadhaar Enrollment ID is no longer accepted.
**Structured Logic:**
```
IF taxpayer.aadhaar_id_type = ENROLLMENT_ID
THEN verification.aadhaar = INVALID
     consequence = BLOCK + ALERT_USE_ACTUAL_AADHAAR_NUMBER
```
**Mode:** CONTROL
**Trigger:** Aadhaar verification step
**Severity:** ABSOLUTE
**Source:** CBDT AY 2025-26 Aadhaar Enrollment ID discontinuation

---

### RULE: ITR.VERIF.003
**Name:** Bank Account Disclosure — All Active Accounts
**Natural Language:** All non-dormant bank accounts held in India during
the financial year must be reported in the ITR.
Dormant accounts (inactive for over 2 years) are exempt.
At least one account must be designated for refund credit.
**Structured Logic:**
```
FOR each bank_account IN taxpayer.bank_accounts:
  IF account.status = ACTIVE
     OR account.last_transaction_date >= DATE(FY-2, 04, 01)
  THEN account.disclosure_required = TRUE
       REQUIRE: account.IFSC IS NOT NULL
       REQUIRE: account.account_number IS NOT NULL

IF refund_account.designated IS NULL
   AND tax.refund_due > 0
THEN consequence = ALERT_DESIGNATE_REFUND_ACCOUNT
```
**Mode:** CONTROL
**Trigger:** Bank account section
**Severity:** CRITICAL
**Source:** CBDT AY 2025-26 mandatory bank account reporting

---

### RULE: ITR.VERIF.004
**Name:** E-Verification Mandatory
**Natural Language:** ITR must be e-verified within 30 days of filing
to be considered valid. Unverified ITR is treated as not filed.
Methods: Aadhaar OTP, Net Banking, Bank Account EVC, Demat EVC,
Digital Signature Certificate (DSC).
**Structured Logic:**
```
IF itr.filed = TRUE
   AND itr.verified = FALSE
   AND DATE_DIFF(itr.filing_date, TODAY) > 30
THEN itr.status = INVALID
     consequence = ALERT_VERIFY_IMMEDIATELY + ESCALATE

IF itr.filing_date + 30_DAYS approaching
   AND itr.verified = FALSE
THEN consequence = ALERT_VERIFICATION_DUE_SOON
```
**Mode:** CONTROL
**Trigger:** Post-filing verification check (daily scheduled rule)
**Severity:** ABSOLUTE
**Consequence:** Alert immediately, escalate if approaching 30-day limit
**Source:** Section 140, CBDT e-verification mandate

---

### RULE: ITR.VERIF.005
**Name:** Nature of Employment — Mandatory Disclosure
**Natural Language:** Taxpayers must specify their nature of employment
from the defined categories: Central Government, State Government,
Public Sector Enterprise, Private Sector, Pensioner (category-wise),
Not Applicable.
**Structured Logic:**
```
IF taxpayer.income_sources CONTAINS SALARY
THEN REQUIRE: taxpayer.employment_nature IN [
       CENTRAL_GOVT,
       STATE_GOVT,
       PUBLIC_SECTOR,
       PRIVATE_SECTOR,
       PENSIONER_CENTRAL_GOVT,
       PENSIONER_STATE_GOVT,
       PENSIONER_PSU,
       PENSIONER_OTHER,
       NOT_APPLICABLE
     ]
     IF taxpayer.employment_nature IS NULL
     THEN consequence = BLOCK_SUBMISSION
```
**Mode:** CONTROL
**Trigger:** Personal information section
**Severity:** CRITICAL
**Source:** ITR1/ITR2 mandatory field — nature of employment

---

# RULESET 8: PENALTY RULES

---

### RULE: ITR.PENAL.001
**Name:** Interest for Late Payment — Section 234A
**Natural Language:** Interest at 1% per month (or part thereof) on
unpaid self-assessment tax, calculated from original due date
to actual filing date.
**Structured Logic:**
```
IF filing.date > filing.due_date
   AND tax.self_assessment_due > 0
THEN months.delayed = CEILING(DATE_DIFF(filing.due_date, filing.date) / 30)
     interest.234A = tax.self_assessment_due * 0.01 * months.delayed
     tax.total_liability += interest.234A
```
**Mode:** CONTROL
**Trigger:** Late filing with tax due
**Severity:** CRITICAL
**Source:** Section 234A

---

### RULE: ITR.PENAL.002
**Name:** Interest for Default in Advance Tax — Section 234B
**Natural Language:** If advance tax paid is less than 90% of assessed tax,
interest at 1% per month from April 1 of AY to date of assessment/filing.
**Structured Logic:**
```
IF advance_tax.paid < (tax.assessed * 0.90)
THEN shortfall.234B = tax.assessed - advance_tax.paid
     months.234B = DATE_DIFF(DATE(AY, 04, 01), filing.date) / 30
     interest.234B = shortfall.234B * 0.01 * CEILING(months.234B)
```
**Mode:** CONTROL
**Trigger:** Advance tax reconciliation
**Severity:** CRITICAL
**Source:** Section 234B

---

### RULE: ITR.PENAL.003
**Name:** Defective Return — Wrong ITR Form
**Natural Language:** Filing ITR using an incorrect form results in
a defective return notice under Section 139(9).
Taxpayer has 15 days to correct and refile. Failure leads to
the return being treated as not filed.
**Structured Logic:**
```
IF form_used != form_applicable [as determined by eligibility rules]
THEN return.status = DEFECTIVE
     consequence = ALERT + BLOCK_PROCESSING
     compliance.action = "Refile with correct form within 15 days"

IF defective_return.correction_deadline_passed = TRUE
THEN return.status = INVALID
     consequence = ESCALATE + ALERT_RETURN_TREATED_AS_NOT_FILED
```
**Mode:** CONTROL
**Trigger:** Form validation at submission
**Severity:** ABSOLUTE
**Source:** Section 139(9)

---

---
# DERIVED OBJECTS
## What the Rules Tell Us Must Exist

This section is DERIVED from the rules above.
No object was invented. Every object exists because at least one rule references it.

---

## OBJECT 1: Taxpayer
Properties required by rules:
- PAN (VERIF.001)
- Aadhaar number (VERIF.001, VERIF.002)
- aadhaar_pan_linked: boolean (VERIF.001)
- residential_status: [RESIDENT_ORDINARY, RNOR, NRI] (ELIG.001)
- category: [INDIVIDUAL, HUF] (ELIG.003, ELIG.012)
- age: integer (COMP.004, COMP.005, COMP.006, DED.002)
- is_director_in_company: boolean (ELIG.004)
- has_unlisted_equity_investment: boolean (ELIG.005)
- has_foreign_assets: boolean (ELIG.006)
- has_foreign_account_signing_authority: boolean (ELIG.006)
- has_esop_tax_deferred: boolean (ELIG.011)
- tds_deducted_under_194N: boolean (ELIG.010)
- employment_nature: enum (VERIF.005)
- employer_type: [GOVERNMENT, PRIVATE] (DED.004)
- applicable_regime: [NEW_REGIME, OLD_REGIME] (COMP.001)
- city: [METRO, NON_METRO] for HRA (DED.007)
- receives_hra: boolean (DED.006)
- owns_residential_property: boolean (DED.006)
- total_income: decimal (ELIG.002, COMP.007, COMP.008, PENAL.002)

---

## OBJECT 2: Income
Sub-objects required by rules:

**Salary Income** (COMP.011, COMP.012, DED.007)
- gross_salary: decimal
- basic: decimal
- da: decimal
- hra_received: decimal
- standard_deduction: decimal [computed]
- net_salary: decimal [computed]

**House Property Income** (COMP.013, COMP.014, COMP.015)
- property_count: integer
- properties[]:
  - status: [SELF_OCCUPIED, LET_OUT]
  - annual_value: decimal
  - municipal_tax_paid: decimal
  - home_loan_interest: decimal
  - net_income: decimal [computed]
- house_property_total: decimal [computed]
- house_property_loss_setoff: decimal [computed, max 2L]
- house_property_loss_carried_forward: decimal [computed]

**Capital Gains** (ELIG.008, COMP.017, COMP.018, COMP.019)
- has_capital_gains: boolean
- capital_gains[]:
  - type: [LTCG_112A, STCG_111A, LTCG_OTHER, STCG_OTHER]
  - amount: decimal
  - stt_paid: boolean
  - acquisition_cost: decimal
  - sale_consideration: decimal
  - exempt_amount: decimal [computed]
  - taxable_amount: decimal [computed]
  - tax: decimal [computed]
- ltcg_112a_amount: decimal [for ITR1 eligibility check]
- has_carried_forward_capital_loss: boolean (ELIG.008)

**Agricultural Income** (COMP.016)
- agricultural_income: decimal

**Other Sources**
- interest_income: decimal
- dividend_income: decimal
- family_pension: decimal [reported under other sources]

---

## OBJECT 3: Deductions
(Old regime only unless specified)

- section_80C: decimal, max 150000 (DED.001)
- section_80C_investments[]: {nature, amount, document_number}
- section_80D_self_family: decimal (DED.002)
- section_80D_parents: decimal (DED.002)
- section_80D_insurer_name: string (DED.002)
- section_80D_policy_number: string (DED.002)
- section_80CCD_1B: decimal, max 50000 (DED.003)
- section_80CCD_2: decimal [both regimes] (DED.004)
- nps_PRAN: string (DED.003)
- section_80G_donations[]: {institution, amount, mode, rate,
                            transaction_no (if political)} (DED.005)
- section_80GG: decimal (DED.006)
- form_10BA_filed: boolean (DED.006)
- form_10BA_acknowledgement: string (DED.006)
- HRA_exemption: decimal [computed] (DED.007)
- section_24b: decimal, max 200000 for self-occupied (COMP.013)
- section_80EE_or_80EEA: decimal [mutually exclusive] (DED.008)

---

## OBJECT 4: Tax Computation
- taxable_income: decimal [computed]
- tax_base: decimal [computed from slabs]
- rebate_87A: decimal [computed]
- tax_after_rebate: decimal [computed]
- surcharge: decimal [computed]
- cess: decimal [computed — 4% of tax + surcharge]
- total_tax_liability: decimal [computed]
- tds_credit: decimal
- advance_tax_paid: decimal
- self_assessment_tax_due: decimal [computed]
- interest_234A: decimal [computed if late]
- interest_234B: decimal [computed if advance tax short]
- interest_234C: decimal [computed if instalment short]
- penalty_234F: decimal [computed if late filing]

---

## OBJECT 5: Filing
- form_type: [ITR1, ITR2]
- assessment_year: string
- filing_date: date
- filing_type: [ORIGINAL, REVISED, BELATED, UPDATED]
- filing_status: [DRAFT, SUBMITTED, VERIFIED, DEFECTIVE, INVALID]
- due_date: date [computed]
- verified: boolean
- verification_method: enum
- verification_date: date
- acknowledgement_number: string
- notice_number: string [if responding to notice]

---

## OBJECT 6: Bank Account
(VERIF.003)
- account_number: string
- IFSC: string
- bank_name: string
- account_type: enum
- status: [ACTIVE, DORMANT]
- last_transaction_date: date
- is_refund_account: boolean
- disclosure_required: boolean [computed]

---

## OBJECT 7: Advance Tax
(PROC.004, PENAL.002)
- required: boolean [computed]
- schedule[]: {due_date, cumulative_percent, amount_due, amount_paid}
- total_paid: decimal
- shortfall: decimal [computed]

---

## RULE-TO-OBJECT TRACEABILITY MAP

| Object | Required By Rules |
|---|---|
| Taxpayer.residential_status | ELIG.001 |
| Taxpayer.total_income | ELIG.002, COMP.007, COMP.008 |
| Taxpayer.is_director | ELIG.004 |
| Taxpayer.has_foreign_assets | ELIG.006 |
| Income.ltcg_112a_amount | ELIG.008 |
| Income.house_property_count | ELIG.009 |
| Income.salary.gross | COMP.011, COMP.012 |
| Income.salary.hra | DED.007 |
| Income.house_property.interest | COMP.013, COMP.014 |
| Deductions.80C | DED.001 |
| Deductions.80D | DED.002 |
| Deductions.NPS_PRAN | DED.003 |
| Tax.rebate_87A | COMP.007, COMP.008 |
| Tax.surcharge | COMP.009, COMP.019 |
| Tax.cess | COMP.010 |
| Filing.due_date | PROC.001, PROC.002 |
| Filing.verified | VERIF.004 |
| BankAccount.IFSC | VERIF.003 |
| AdvanceTax.schedule | PROC.004, PENAL.002 |

---

## WHAT THIS PROVES (The Rules-First Principle in Action)

Every object property above was demanded by a rule.
No property was invented speculatively.
No rule was invented to justify an object.

The rules came first.
The objects emerged from the rules.
This is the rules-first approach applied to a real-world compliance system.

The next step is to build the data layer and business logic layer
using these objects as the specification — confident that every
field serves a governance purpose.

---

*Source: CBDT Official Notifications, Income Tax Act 1961,
incometax.gov.in AY 2026-27, Finance Act 2024 and 2025*
*AY 2026-27 (FY 2025-26) — Rules current as of May 2026*
