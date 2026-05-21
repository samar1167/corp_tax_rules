from django.core.management.base import BaseCommand
from django.utils import timezone

from core_rules.models import (
    AssessmentContext,
    ChangeSet,
    DecisionTableDefinition,
    DecisionTableVersion,
    ModuleDefinition,
    ModuleStatusChoices,
    ModuleVersion,
    PrimitiveDefinition,
    PrimitiveVersion,
    RuleDefinition,
    RuleVersion,
    ScopeChoices,
    StatusChoices,
)


RULES = [
    {
        "rule_id": "ITR.ELIG.001",
        "name": "ITR1 Residential Status Eligibility",
        "source_reference": "Income Tax Act Section 6, CBDT ITR1 Instructions AY 2026-27",
        "natural_language": "Only Resident Individuals (ordinarily resident) can file ITR1. NRI and RNOR cannot file ITR1.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "form_selection"},
        "consequence": {"action": ["BLOCK_ITR1", "REDIRECT_TO_ITR2"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {
                            "field": "residential_status",
                            "operator": "in",
                            "value": ["NRI", "RNOR"],
                        }
                    ],
                }
            ],
            "then": {
                "form_eligibility": {
                    "ITR1": "DISQUALIFIED",
                    "ITR2": "ELIGIBLE",
                }
            },
        },
    },
    {
        "rule_id": "ITR.ELIG.002",
        "name": "ITR1 Income Ceiling",
        "source_reference": "ITR1 Eligibility Criteria AY 2026-27",
        "natural_language": "Total income must not exceed Rs 50 lakh to file ITR1.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "income_entry"},
        "consequence": {"action": ["BLOCK_ITR1", "ALERT", "REDIRECT_TO_ITR2"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "total_income", "operator": "gt", "value": 5000000}
                    ],
                }
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED", "ITR2": "ELIGIBLE"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.003",
        "name": "ITR1 Taxpayer Category",
        "source_reference": "ITR1 Instructions AY 2026-27",
        "natural_language": "ITR1 can only be filed by an Individual.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "category_selection"},
        "consequence": {"action": ["BLOCK_ITR1"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "category", "operator": "not_equals", "value": "INDIVIDUAL"}
                    ],
                }
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.004",
        "name": "ITR1 Director Disqualification",
        "source_reference": "ITR1 Exclusion Conditions AY 2026-27",
        "natural_language": "An individual who is a Director in any company cannot file ITR1.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "director_flag"},
        "consequence": {"action": ["BLOCK_ITR1", "REDIRECT_TO_ITR2"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "is_director_in_company", "operator": "equals", "value": True}
                    ],
                }
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED", "ITR2": "ELIGIBLE"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.005",
        "name": "ITR1 Unlisted Equity Disqualification",
        "source_reference": "ITR1 Exclusion Conditions AY 2026-27",
        "natural_language": "An individual who has invested in unlisted equity shares cannot file ITR1.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "investment_disclosure"},
        "consequence": {"action": ["BLOCK_ITR1", "REDIRECT_TO_ITR2"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {
                            "field": "has_unlisted_equity_investment",
                            "operator": "equals",
                            "value": True,
                        }
                    ],
                }
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED", "ITR2": "ELIGIBLE"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.006",
        "name": "ITR1 Foreign Asset Disqualification",
        "source_reference": "ITR1 Exclusion Conditions AY 2026-27",
        "natural_language": "Foreign assets or foreign account signing authority disqualify ITR1.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "foreign_asset_declaration"},
        "consequence": {"action": ["BLOCK_ITR1", "REDIRECT_TO_ITR2"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "any",
                    "conditions": [
                        {"field": "has_foreign_assets", "operator": "equals", "value": True},
                        {
                            "field": "has_foreign_account_signing_authority",
                            "operator": "equals",
                            "value": True,
                        },
                    ],
                }
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED", "ITR2": "ELIGIBLE"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.007",
        "name": "ITR1 Business or Profession Income Disqualification",
        "source_reference": "ITR1 Exclusion Conditions AY 2026-27",
        "natural_language": "Any individual earning income from business or profession cannot file ITR1.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "income_source_selection"},
        "consequence": {"action": ["BLOCK_ITR1", "REDIRECT_TO_ITR3_OR_ITR4"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {
                            "field": "income_sources",
                            "operator": "contains_any",
                            "value": ["BUSINESS", "PROFESSION"],
                        }
                    ],
                }
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.008",
        "name": "ITR1 Capital Gains Restriction",
        "source_reference": "CBDT AY 2026-27 ITR1 expanded eligibility notification",
        "natural_language": "Capital gains disqualify ITR1 except limited LTCG 112A cases.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "capital_gains_disclosure"},
        "consequence": {"action": ["BLOCK_ITR1", "REDIRECT_TO_ITR2"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "has_capital_gains", "operator": "equals", "value": True},
                        {
                            "field": "capital_gain_type",
                            "operator": "not_equals",
                            "value": "LTCG_112A",
                        },
                    ],
                },
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "has_capital_gains", "operator": "equals", "value": True},
                        {"field": "capital_gain_type", "operator": "equals", "value": "LTCG_112A"},
                        {"field": "ltcg_112a_amount", "operator": "gt", "value": 125000},
                    ],
                },
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "has_capital_gains", "operator": "equals", "value": True},
                        {"field": "capital_gain_type", "operator": "equals", "value": "LTCG_112A"},
                        {
                            "field": "has_carried_forward_capital_loss",
                            "operator": "equals",
                            "value": True,
                        },
                    ],
                },
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED", "ITR2": "ELIGIBLE"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.009",
        "name": "ITR1 Multiple House Property Restriction",
        "source_reference": "ITR1 AY 2026-27 updated eligibility - Notification No. 57/2026",
        "natural_language": "More than two house properties or brought-forward house property loss disqualifies ITR1.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "house_property_declaration"},
        "consequence": {"action": ["BLOCK_ITR1", "REDIRECT_TO_ITR2"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "house_property_count", "operator": "gt", "value": 2}
                    ],
                },
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "house_property_count", "operator": "lte", "value": 2},
                        {
                            "field": "has_brought_forward_house_property_loss",
                            "operator": "equals",
                            "value": True,
                        },
                    ],
                },
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED", "ITR2": "ELIGIBLE"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.010",
        "name": "ITR1 TDS Section 194N Disqualification",
        "source_reference": "ITR1 Exclusion Conditions AY 2026-27",
        "natural_language": "If TDS has been deducted under Section 194N, ITR1 cannot be filed.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "tds_entry"},
        "consequence": {"action": ["BLOCK_ITR1"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {
                            "field": "tds_deducted_under_194N",
                            "operator": "equals",
                            "value": True,
                        }
                    ],
                }
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.011",
        "name": "ITR1 ESOP Tax Deferral Disqualification",
        "source_reference": "ITR1 Exclusion Conditions AY 2026-27",
        "natural_language": "If income tax on ESOP has been deferred, ITR1 cannot be filed.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "esop_declaration"},
        "consequence": {"action": ["BLOCK_ITR1"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "has_esop_tax_deferred", "operator": "equals", "value": True}
                    ],
                }
            ],
            "then": {"form_eligibility": {"ITR1": "DISQUALIFIED"}},
        },
    },
    {
        "rule_id": "ITR.ELIG.012",
        "name": "ITR2 Eligibility Positive Conditions",
        "source_reference": "ITR2 Applicability Conditions AY 2026-27",
        "natural_language": "ITR2 is applicable to individuals and HUFs without business/profession income in specified cases.",
        "mode": "ALERT",
        "severity": "INFO",
        "trigger": {"event": "profile_completion"},
        "consequence": {"action": ["SUGGEST_ITR2"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "category", "operator": "in", "value": ["INDIVIDUAL", "HUF"]},
                        {
                            "field": "has_business_profession_income",
                            "operator": "equals",
                            "value": False,
                        },
                        {"field": "total_income", "operator": "gt", "value": 5000000},
                    ],
                },
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "category", "operator": "in", "value": ["INDIVIDUAL", "HUF"]},
                        {
                            "field": "has_business_profession_income",
                            "operator": "equals",
                            "value": False,
                        },
                        {"field": "house_property_count", "operator": "gt", "value": 2},
                    ],
                },
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "category", "operator": "in", "value": ["INDIVIDUAL", "HUF"]},
                        {
                            "field": "has_business_profession_income",
                            "operator": "equals",
                            "value": False,
                        },
                        {"field": "has_capital_gains", "operator": "equals", "value": True},
                    ],
                },
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "category", "operator": "in", "value": ["INDIVIDUAL", "HUF"]},
                        {
                            "field": "has_business_profession_income",
                            "operator": "equals",
                            "value": False,
                        },
                        {"field": "has_foreign_assets", "operator": "equals", "value": True},
                    ],
                },
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "category", "operator": "in", "value": ["INDIVIDUAL", "HUF"]},
                        {
                            "field": "has_business_profession_income",
                            "operator": "equals",
                            "value": False,
                        },
                        {"field": "is_director_in_company", "operator": "equals", "value": True},
                    ],
                },
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "category", "operator": "in", "value": ["INDIVIDUAL", "HUF"]},
                        {
                            "field": "has_business_profession_income",
                            "operator": "equals",
                            "value": False,
                        },
                        {
                            "field": "residential_status",
                            "operator": "in",
                            "value": ["NRI", "RNOR"],
                        },
                    ],
                }
            ],
            "then": {"form_eligibility": {"ITR2": "ELIGIBLE"}},
        },
    },
]

REGIME_RULES = [
    {
        "rule_id": "ITR.COMP.001",
        "name": "Default Tax Regime",
        "source_reference": "Finance Act 2023, Section 115BAC",
        "natural_language": "New Tax Regime is the default when regime selection is not specified.",
        "mode": "ALERT",
        "severity": "WARNING",
        "trigger": {"event": "regime_selection_step"},
        "consequence": {"action": ["ALERT_DEFAULT_APPLIED"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "regime_selection", "operator": "in", "value": ["", "NOT_SPECIFIED"]},
                    ],
                }
            ],
            "then": {"taxpayer": {"applicable_regime": "NEW_REGIME"}},
        },
    },
    {
        "rule_id": "ITR.COMP.002",
        "name": "Old Regime Opt-Out for Non-Business Taxpayers",
        "source_reference": "Section 115BAC, CBDT FAQ AY 2026-27",
        "natural_language": "Non-business taxpayers can choose the old regime if filing on or before due date.",
        "mode": "CONTROL",
        "severity": "CRITICAL",
        "trigger": {"event": "regime_selection_and_filing_date_check"},
        "consequence": {"action": ["ALLOW_OLD_REGIME"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "has_business_profession_income", "operator": "equals", "value": False},
                        {"field": "regime_selection", "operator": "equals", "value": "OLD_REGIME"},
                        {"field": "filing_date", "operator": "lte", "value": "DUE_DATE_FIELD"},
                    ],
                }
            ],
            "then": {"taxpayer": {"applicable_regime": "OLD_REGIME"}},
        },
    },
    {
        "rule_id": "ITR.COMP.002.LATE",
        "name": "Old Regime Late Filing Fallback",
        "source_reference": "Section 115BAC, CBDT FAQ AY 2026-27",
        "natural_language": "If a non-business taxpayer files late, old regime cannot be chosen and new regime applies.",
        "mode": "CONTROL",
        "severity": "CRITICAL",
        "trigger": {"event": "regime_selection_and_filing_date_check"},
        "consequence": {"action": ["ALERT_CANNOT_CHOOSE_OLD_REGIME_LATE"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "has_business_profession_income", "operator": "equals", "value": False},
                        {"field": "regime_selection", "operator": "equals", "value": "OLD_REGIME"},
                        {"field": "filing_date", "operator": "gt", "value": "DUE_DATE_FIELD"},
                    ],
                }
            ],
            "then": {"taxpayer": {"applicable_regime": "NEW_REGIME"}},
        },
    },
]

TAX_COMPUTATION_RULES = [
    {
        "rule_id": "ITR.COMP.003",
        "name": "New Regime Tax Slabs AY 2026-27",
        "source_reference": "Finance Act 2025, Budget 2025 new regime slab revision",
        "natural_language": "Under new regime, tax is computed using AY 2026-27 slabs.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "tax_computation_step"},
        "consequence": {"action": ["COMPUTE_BASE_TAX_NEW_REGIME"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "applicable_regime", "operator": "equals", "value": "NEW_REGIME"},
                    ],
                }
            ],
            "then": {"tax": {"base": "CALCULATE_USING_NEW_SLABS"}},
        },
    },
    {
        "rule_id": "ITR.COMP.007",
        "name": "Section 87A Rebate - New Regime",
        "source_reference": "Section 87A, Finance Act 2025",
        "natural_language": "Under new regime, taxable income up to Rs 12,00,000 with no special rate income gets rebate up to Rs 60,000.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "tax_computation_rebate_step"},
        "consequence": {"action": ["APPLY_87A_REBATE_NEW_REGIME"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "applicable_regime", "operator": "equals", "value": "NEW_REGIME"},
                        {"field": "taxable_income", "operator": "lte", "value": 1200000},
                        {"field": "special_rate_income", "operator": "equals", "value": 0},
                    ],
                }
            ],
            "then": {"tax": {"rebate_87a": "MIN_BASE_OR_60000"}},
        },
    },
    {
        "rule_id": "ITR.COMP.010",
        "name": "Health and Education Cess",
        "source_reference": "Finance Act, Cess provisions",
        "natural_language": "Health and Education Cess at 4% is levied on post-rebate tax plus surcharge.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "tax_computation_final_step"},
        "consequence": {"action": ["APPLY_4_PERCENT_CESS"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "applicable_regime", "operator": "equals", "value": "NEW_REGIME"},
                    ],
                }
            ],
            "then": {"tax": {"cess": "APPLY_4_PERCENT"}},
        },
    },
]


class Command(BaseCommand):
    help = "Seed AY 2026-27 ITR form eligibility rules and primitive metadata."

    def handle(self, *args, **options):
        context, _ = AssessmentContext.objects.update_or_create(
            code="AY_2026_27",
            defaults={
                "assessment_year": "2026-27",
                "financial_year": "2025-26",
                "effective_from": "2026-04-01",
                "effective_to": "2027-03-31",
                "is_active": True,
                "metadata": {"domain": "ITR"},
            },
        )

        primitive, _ = PrimitiveDefinition.objects.update_or_create(
            code="ITR.FORM_ELIGIBILITY",
            defaults={
                "name": "ITR Form Eligibility",
                "module_scope": ScopeChoices.ITR,
                "question": "Which ITR form is this taxpayer eligible to file?",
                "description": "Initial primitive containing AY 2026-27 ITR1 and ITR2 eligibility logic.",
            },
        )

        rule_versions = []
        for item in RULES:
            rule, _ = RuleDefinition.objects.update_or_create(
                rule_id=item["rule_id"],
                defaults={
                    "name": item["name"],
                    "scope": ScopeChoices.ITR,
                    "description": item["natural_language"],
                },
            )
            version, _ = RuleVersion.objects.update_or_create(
                rule=rule,
                version="1.0",
                defaults={
                    "status": StatusChoices.ACTIVE,
                    "source_reference": item["source_reference"],
                    "natural_language": item["natural_language"],
                    "structured_logic": item["structured_logic"],
                    "mode": item["mode"],
                    "trigger": item["trigger"],
                    "consequence": item["consequence"],
                    "severity": item["severity"],
                    "approved_by": "SeedCommand",
                    "approved_at": timezone.now(),
                    "metadata": {"assessment_context": context.code},
                },
            )
            rule_versions.append(version)

        primitive_version, _ = PrimitiveVersion.objects.update_or_create(
            primitive=primitive,
            version="1.0",
            defaults={
                "status": StatusChoices.ACTIVE,
                "input_schema": {
                    "type": "object",
                    "required": [
                        "residential_status",
                        "total_income",
                        "category",
                        "income_sources",
                        "house_property_count",
                    ],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "selected_form": {"type": "string"},
                        "suggested_forms": {"type": "array"},
                    },
                },
                "completeness_report": {
                    "seeded_from": "ITR_Rule_System.md",
                    "rules_seeded": len(RULES),
                },
                "approved_by": "SeedCommand",
                "approved_at": timezone.now(),
            },
        )
        primitive_version.rules.set(rule_versions)

        regime_primitive, _ = PrimitiveDefinition.objects.update_or_create(
            code="ITR.REGIME_SELECTION",
            defaults={
                "name": "ITR Regime Selection",
                "module_scope": ScopeChoices.ITR,
                "question": "Which tax regime applies to this taxpayer for the filing?",
                "description": "Initial primitive containing AY 2026-27 regime selection logic.",
            },
        )

        regime_rule_versions = []
        for item in REGIME_RULES:
            rule, _ = RuleDefinition.objects.update_or_create(
                rule_id=item["rule_id"],
                defaults={
                    "name": item["name"],
                    "scope": ScopeChoices.ITR,
                    "description": item["natural_language"],
                },
            )
            version, _ = RuleVersion.objects.update_or_create(
                rule=rule,
                version="1.0",
                defaults={
                    "status": StatusChoices.ACTIVE,
                    "source_reference": item["source_reference"],
                    "natural_language": item["natural_language"],
                    "structured_logic": item["structured_logic"],
                    "mode": item["mode"],
                    "trigger": item["trigger"],
                    "consequence": item["consequence"],
                    "severity": item["severity"],
                    "approved_by": "SeedCommand",
                    "approved_at": timezone.now(),
                    "metadata": {"assessment_context": context.code},
                },
            )
            regime_rule_versions.append(version)

        regime_primitive_version, _ = PrimitiveVersion.objects.update_or_create(
            primitive=regime_primitive,
            version="1.0",
            defaults={
                "status": StatusChoices.ACTIVE,
                "input_schema": {
                    "type": "object",
                    "required": [
                        "has_business_profession_income",
                        "regime_selection",
                        "filing_date",
                        "due_date_139_1",
                    ],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "applicable_regime": {"type": "string"},
                        "alerts": {"type": "array"},
                    },
                },
                "completeness_report": {
                    "seeded_from": "ITR_Rule_System.md",
                    "rules_seeded": len(REGIME_RULES),
                },
                "approved_by": "SeedCommand",
                "approved_at": timezone.now(),
            },
        )
        regime_primitive_version.rules.set(regime_rule_versions)

        tax_primitive, _ = PrimitiveDefinition.objects.update_or_create(
            code="ITR.TAX_COMPUTATION",
            defaults={
                "name": "ITR Tax Computation",
                "module_scope": ScopeChoices.ITR,
                "question": "How is tax computed for this taxpayer in the current slice?",
                "description": "Initial primitive containing new-regime slab, rebate, and cess logic.",
            },
        )

        tax_rule_versions = []
        for item in TAX_COMPUTATION_RULES:
            rule, _ = RuleDefinition.objects.update_or_create(
                rule_id=item["rule_id"],
                defaults={
                    "name": item["name"],
                    "scope": ScopeChoices.ITR,
                    "description": item["natural_language"],
                },
            )
            version, _ = RuleVersion.objects.update_or_create(
                rule=rule,
                version="1.0",
                defaults={
                    "status": StatusChoices.ACTIVE,
                    "source_reference": item["source_reference"],
                    "natural_language": item["natural_language"],
                    "structured_logic": item["structured_logic"],
                    "mode": item["mode"],
                    "trigger": item["trigger"],
                    "consequence": item["consequence"],
                    "severity": item["severity"],
                    "approved_by": "SeedCommand",
                    "approved_at": timezone.now(),
                    "metadata": {"assessment_context": context.code},
                },
            )
            tax_rule_versions.append(version)

        tax_primitive_version, _ = PrimitiveVersion.objects.update_or_create(
            primitive=tax_primitive,
            version="1.0",
            defaults={
                "status": StatusChoices.ACTIVE,
                "input_schema": {
                    "type": "object",
                    "required": [
                        "applicable_regime",
                        "taxable_income",
                        "special_rate_income",
                    ],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "base_tax": {"type": "string"},
                        "rebate_87a": {"type": "string"},
                        "cess": {"type": "string"},
                        "total_liability": {"type": "string"},
                    },
                },
                "completeness_report": {
                    "seeded_from": "ITR_Rule_System.md",
                    "rules_seeded": len(TAX_COMPUTATION_RULES),
                    "scope_note": "new regime slice only",
                },
                "approved_by": "SeedCommand",
                "approved_at": timezone.now(),
            },
        )
        tax_primitive_version.rules.set(tax_rule_versions)

        decision_table, _ = DecisionTableDefinition.objects.update_or_create(
            code="ITR.FORM_SELECTION",
            defaults={
                "name": "ITR Form Selection",
                "scope": ScopeChoices.ITR,
                "description": "Initial ITR decision table for selecting between ITR1, ITR2, and ITR3_OR_ITR4 suggestions.",
            },
        )
        decision_table_version, _ = DecisionTableVersion.objects.update_or_create(
            decision_table=decision_table,
            version="1.0",
            defaults={
                "status": StatusChoices.ACTIVE,
                "module_scope": ScopeChoices.ITR,
                "input_columns": [
                    "itr1_disqualified",
                    "itr2_suggested",
                    "redirect_to_itr3_or_itr4",
                ],
                "output_columns": ["selected_form", "suggested_forms"],
                "rows": [
                    {
                        "when": {
                            "itr1_disqualified": False,
                            "itr2_suggested": False,
                            "redirect_to_itr3_or_itr4": False,
                        },
                        "then": {"selected_form": "ITR1", "suggested_forms": []},
                    },
                    {
                        "when": {
                            "itr1_disqualified": True,
                            "itr2_suggested": True,
                            "redirect_to_itr3_or_itr4": False,
                        },
                        "then": {"selected_form": "ITR2", "suggested_forms": ["ITR2"]},
                    },
                    {
                        "when": {
                            "itr1_disqualified": True,
                            "itr2_suggested": False,
                            "redirect_to_itr3_or_itr4": True,
                        },
                        "then": {
                            "selected_form": "ITR3_OR_ITR4",
                            "suggested_forms": ["ITR3_OR_ITR4"],
                        },
                    },
                ],
                "completeness_report": {
                    "seeded_from": "ITR_Rule_System.md",
                    "decision": "form_selection",
                },
                "approved_by": "SeedCommand",
                "approved_at": timezone.now(),
            },
        )
        decision_table_version.input_primitives.set([primitive_version])

        regime_decision_table, _ = DecisionTableDefinition.objects.update_or_create(
            code="ITR.REGIME_SELECTION",
            defaults={
                "name": "ITR Regime Selection",
                "scope": ScopeChoices.ITR,
                "description": "Initial ITR decision table for selecting applicable regime.",
            },
        )
        regime_decision_table_version, _ = DecisionTableVersion.objects.update_or_create(
            decision_table=regime_decision_table,
            version="1.0",
            defaults={
                "status": StatusChoices.ACTIVE,
                "module_scope": ScopeChoices.ITR,
                "input_columns": [
                    "default_applied",
                    "new_regime_requested",
                    "old_regime_allowed",
                    "old_regime_requested",
                ],
                "output_columns": ["applicable_regime"],
                "rows": [
                    {
                        "when": {
                            "default_applied": True,
                            "new_regime_requested": False,
                            "old_regime_allowed": False,
                            "old_regime_requested": False,
                        },
                        "then": {"applicable_regime": "NEW_REGIME"},
                    },
                    {
                        "when": {
                            "default_applied": False,
                            "new_regime_requested": True,
                            "old_regime_allowed": False,
                            "old_regime_requested": False,
                        },
                        "then": {"applicable_regime": "NEW_REGIME"},
                    },
                    {
                        "when": {
                            "default_applied": False,
                            "new_regime_requested": False,
                            "old_regime_allowed": True,
                            "old_regime_requested": True,
                        },
                        "then": {"applicable_regime": "OLD_REGIME"},
                    },
                    {
                        "when": {
                            "default_applied": False,
                            "new_regime_requested": False,
                            "old_regime_allowed": False,
                            "old_regime_requested": True,
                        },
                        "then": {"applicable_regime": "NEW_REGIME"},
                    },
                ],
                "completeness_report": {
                    "seeded_from": "ITR_Rule_System.md",
                    "decision": "regime_selection",
                },
                "approved_by": "SeedCommand",
                "approved_at": timezone.now(),
            },
        )
        regime_decision_table_version.input_primitives.set([regime_primitive_version])

        module, _ = ModuleDefinition.objects.update_or_create(
            code="INDIA_INDIVIDUAL_TAX",
            defaults={
                "name": "India Individual Tax",
                "scope": ScopeChoices.ITR,
                "description": "Initial ITR module for AY 2026-27.",
            },
        )
        module_version, _ = ModuleVersion.objects.update_or_create(
            module=module,
            version="1.0",
            assessment_context=context,
            defaults={
                "status": ModuleStatusChoices.ACTIVE,
                "contract_provides": [
                    {
                        "output_id": "itr.selected_form",
                        "description": "Primary ITR form recommendation for the taxpayer profile",
                        "data_type": "string",
                    },
                    {
                        "output_id": "itr.suggested_forms",
                        "description": "Additional ITR form suggestions for the taxpayer profile",
                        "data_type": "array",
                    },
                ],
                "contract_consumes": [],
                "fallback_behaviour": {
                    "rule_data_missing": "do_not_select_form",
                    "assessment_context_missing": "reject_evaluation",
                },
                "approved_by": "SeedCommand",
                "approved_at": timezone.now(),
            },
        )
        module_version.primitives.set([primitive_version])
        module_version.primitives.set([primitive_version, regime_primitive_version, tax_primitive_version])
        module_version.decision_tables.set([decision_table_version, regime_decision_table_version])

        change_set, _ = ChangeSet.objects.update_or_create(
            code="CS.ITR.AY2026_27.INITIAL",
            defaults={
                "name": "Initial ITR AY 2026-27 Activation",
                "description": "Initial bundled activation set for the seeded ITR module slices.",
                "assessment_context": context,
                "status": StatusChoices.ACTIVE,
                "impact_analysis": {
                    "module": "INDIA_INDIVIDUAL_TAX",
                    "domains": ["form_eligibility", "regime_selection", "tax_computation"],
                },
                "activation_report": {
                    "seeded_by": "SeedCommand",
                    "notes": "Initial seeded activation bundle",
                },
                "approved_by": "SeedCommand",
                "approved_at": timezone.now(),
                "activated_at": timezone.now(),
            },
        )
        change_set.rule_versions.set(rule_versions + regime_rule_versions + tax_rule_versions)
        change_set.primitive_versions.set([primitive_version, regime_primitive_version, tax_primitive_version])
        change_set.decision_table_versions.set([decision_table_version, regime_decision_table_version])
        change_set.module_versions.set([module_version])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(rule_versions)} ITR eligibility rules, {len(regime_rule_versions)} regime rules, {len(tax_rule_versions)} tax computation rules, 2 decision tables, 1 module version, and 1 initial change set for {context.code}."
            )
        )
