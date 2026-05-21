from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from core_rules.models import (
    AssessmentContext,
    ChangeSet,
    DecisionTableDefinition,
    DecisionTableVersion,
    ModuleDefinition,
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
        "rule_id": "CORP.CLASS.001",
        "primitive_code": "CORP.ENTITY_TYPE",
        "name": "Domestic company classification",
        "source_reference": "Income-tax Act 2025 Section 2(23A)",
        "natural_language": "A company incorporated in India under the Companies Act is classified as a domestic company.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "entity_classification"},
        "consequence": {"action": ["CLASSIFY_ENTITY"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "registration_country", "operator": "equals", "value": "INDIA"},
                        {"field": "registration_act", "operator": "equals", "value": "COMPANIES_ACT"},
                    ],
                }
            ],
            "then": {"entity_type": "DOMESTIC_COMPANY"},
        },
    },
    {
        "rule_id": "CORP.CLASS.002",
        "primitive_code": "CORP.ENTITY_TYPE",
        "name": "LLP classification",
        "source_reference": "Income-tax Act 2025 LLP treatment",
        "natural_language": "An entity registered under the LLP Act is classified as an LLP.",
        "mode": "CONTROL",
        "severity": "ABSOLUTE",
        "trigger": {"event": "entity_classification"},
        "consequence": {"action": ["CLASSIFY_ENTITY"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "registration_act", "operator": "equals", "value": "LLP_ACT"}
                    ],
                }
            ],
            "then": {"entity_type": "LLP"},
        },
    },
    {
        "rule_id": "CORP.CLASS.003",
        "primitive_code": "CORP.ENTITY_TYPE",
        "name": "Deemed domestic classification",
        "source_reference": "Corporate tax residential status concept",
        "natural_language": "A foreign company with management control in India is flagged as deemed domestic for this concept slice.",
        "mode": "ALERT",
        "severity": "CRITICAL",
        "trigger": {"event": "entity_classification"},
        "consequence": {"action": ["REVIEW_RESIDENTIAL_STATUS"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "registration_country", "operator": "not_equals", "value": "INDIA"},
                        {
                            "field": "management_control_in_india",
                            "operator": "equals",
                            "value": True,
                        },
                    ],
                }
            ],
            "then": {"entity_type": "DEEMED_DOMESTIC"},
        },
    },
    {
        "rule_id": "CORP.PE.001",
        "primitive_code": "CORP.PE_STATUS",
        "name": "Domestic PE not applicable",
        "source_reference": "Corporate PE concept",
        "natural_language": "PE analysis is not applicable to domestic or deemed domestic entities in this slice.",
        "mode": "OBSERVER",
        "severity": "INFO",
        "trigger": {"event": "pe_evaluation"},
        "consequence": {"action": ["PE_NOT_APPLICABLE"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "any",
                    "conditions": [
                        {"field": "entity_type", "operator": "equals", "value": "DOMESTIC_COMPANY"},
                        {"field": "entity_type", "operator": "equals", "value": "DEEMED_DOMESTIC"},
                        {"field": "entity_type", "operator": "equals", "value": "LLP"},
                    ],
                }
            ],
            "then": {"pe_status": "NOT_APPLICABLE"},
        },
    },
    {
        "rule_id": "CORP.PE.002",
        "primitive_code": "CORP.PE_STATUS",
        "name": "Fixed place PE",
        "source_reference": "PE determination concept",
        "natural_language": "A foreign company with a fixed place office in India is treated as having a PE.",
        "mode": "CONTROL",
        "severity": "CRITICAL",
        "trigger": {"event": "pe_evaluation"},
        "consequence": {"action": ["PE_EXISTS", "DTAA_REVIEW_RECOMMENDED"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "entity_type", "operator": "equals", "value": "FOREIGN_COMPANY"},
                        {
                            "field": "office_fixed_place_in_india",
                            "operator": "equals",
                            "value": True,
                        },
                    ],
                }
            ],
            "then": {"pe_status": "PE_EXISTS"},
        },
    },
    {
        "rule_id": "CORP.PE.003",
        "primitive_code": "CORP.PE_STATUS",
        "name": "Dependent agent or construction PE",
        "source_reference": "PE determination concept",
        "natural_language": "A foreign company with a dependent agent in India or a long construction project is treated as having a PE.",
        "mode": "CONTROL",
        "severity": "CRITICAL",
        "trigger": {"event": "pe_evaluation"},
        "consequence": {"action": ["PE_EXISTS", "DTAA_REVIEW_RECOMMENDED"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "entity_type", "operator": "equals", "value": "FOREIGN_COMPANY"},
                        {
                            "field": "agents_dependent_in_india",
                            "operator": "equals",
                            "value": True,
                        },
                    ],
                },
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "entity_type", "operator": "equals", "value": "FOREIGN_COMPANY"},
                        {
                            "field": "construction_project_duration_days",
                            "operator": "gt",
                            "value": 183,
                        },
                    ],
                },
            ],
            "then": {"pe_status": "PE_EXISTS"},
        },
    },
    {
        "rule_id": "CORP.PE.004",
        "primitive_code": "CORP.PE_STATUS",
        "name": "No PE default",
        "source_reference": "PE determination concept",
        "natural_language": "A foreign company without fixed place, dependent agents, or long construction presence is treated as having no PE.",
        "mode": "OBSERVER",
        "severity": "INFO",
        "trigger": {"event": "pe_evaluation"},
        "consequence": {"action": ["NO_PE_DETECTED"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "entity_type", "operator": "equals", "value": "FOREIGN_COMPANY"},
                        {
                            "field": "office_fixed_place_in_india",
                            "operator": "equals",
                            "value": False,
                        },
                        {
                            "field": "agents_dependent_in_india",
                            "operator": "equals",
                            "value": False,
                        },
                        {
                            "field": "construction_project_duration_days",
                            "operator": "lte",
                            "value": 183,
                        },
                    ],
                }
            ],
            "then": {"pe_status": "NO_PE"},
        },
    },
    {
        "rule_id": "CORP.TURN.001",
        "primitive_code": "CORP.TURNOVER_CATEGORY",
        "name": "LLP turnover category",
        "source_reference": "Corporate rate track concept",
        "natural_language": "An LLP stays on the LLP flat 30 percent track regardless of turnover.",
        "mode": "OBSERVER",
        "severity": "INFO",
        "trigger": {"event": "turnover_classification"},
        "consequence": {"action": ["LLP_RATE_TRACK"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [{"field": "entity_type", "operator": "equals", "value": "LLP"}],
                }
            ],
            "then": {"turnover_category": "LLP_FLAT_30"},
        },
    },
    {
        "rule_id": "CORP.TURN.002",
        "primitive_code": "CORP.TURNOVER_CATEGORY",
        "name": "Domestic below 400Cr",
        "source_reference": "Finance Act turnover threshold",
        "natural_language": "A domestic or deemed domestic company with previous-year turnover up to 400 crore is in the below 400 crore category.",
        "mode": "CONTROL",
        "severity": "INFO",
        "trigger": {"event": "turnover_classification"},
        "consequence": {"action": ["CLASSIFY_TURNOVER"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {
                            "field": "entity_type",
                            "operator": "in",
                            "value": ["DOMESTIC_COMPANY", "DEEMED_DOMESTIC"],
                        },
                        {"field": "previous_year_turnover", "operator": "lte", "value": 4000000000},
                    ],
                }
            ],
            "then": {"turnover_category": "BELOW_400CR"},
        },
    },
    {
        "rule_id": "CORP.TURN.003",
        "primitive_code": "CORP.TURNOVER_CATEGORY",
        "name": "Domestic above 400Cr",
        "source_reference": "Finance Act turnover threshold",
        "natural_language": "A domestic or deemed domestic company with previous-year turnover above 400 crore is in the above 400 crore category.",
        "mode": "CONTROL",
        "severity": "INFO",
        "trigger": {"event": "turnover_classification"},
        "consequence": {"action": ["CLASSIFY_TURNOVER"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {
                            "field": "entity_type",
                            "operator": "in",
                            "value": ["DOMESTIC_COMPANY", "DEEMED_DOMESTIC"],
                        },
                        {"field": "previous_year_turnover", "operator": "gt", "value": 4000000000},
                    ],
                }
            ],
            "then": {"turnover_category": "ABOVE_400CR"},
        },
    },
    {
        "rule_id": "CORP.TURN.004",
        "primitive_code": "CORP.TURNOVER_CATEGORY",
        "name": "Foreign turnover category",
        "source_reference": "Corporate foreign company concept",
        "natural_language": "A foreign company is kept in a foreign turnover bucket because the standard 400 crore domestic threshold is not used for its rate track.",
        "mode": "OBSERVER",
        "severity": "INFO",
        "trigger": {"event": "turnover_classification"},
        "consequence": {"action": ["CLASSIFY_TURNOVER"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "entity_type", "operator": "equals", "value": "FOREIGN_COMPANY"}
                    ],
                }
            ],
            "then": {"turnover_category": "FOREIGN"},
        },
    },
    {
        "rule_id": "CORP.INCORP.001",
        "primitive_code": "CORP.INCORPORATION_DATE_STATUS",
        "name": "Eligible for 15 percent manufacturing regime",
        "source_reference": "Section 115BAB concept",
        "natural_language": "A company incorporated in India on or after 1 October 2019 and carrying on manufacturing is eligible for the 15 percent manufacturing track in this concept slice.",
        "mode": "CONTROL",
        "severity": "CRITICAL",
        "trigger": {"event": "incorporation_evaluation"},
        "consequence": {"action": ["CHECK_115BAB_ELIGIBILITY"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "registration_country", "operator": "equals", "value": "INDIA"},
                        {"field": "incorporation_date", "operator": "gte", "value": "2019-10-01"},
                        {
                            "field": "business_activity",
                            "operator": "equals",
                            "value": "MANUFACTURING",
                        },
                    ],
                }
            ],
            "then": {"incorporation_date_status": "ELIGIBLE_FOR_15PCT"},
        },
    },
    {
        "rule_id": "CORP.INCORP.002",
        "primitive_code": "CORP.INCORPORATION_DATE_STATUS",
        "name": "Ineligible because pre-October 2019",
        "source_reference": "Section 115BAB concept",
        "natural_language": "A company incorporated before 1 October 2019 is not eligible for the 15 percent manufacturing track.",
        "mode": "CONTROL",
        "severity": "INFO",
        "trigger": {"event": "incorporation_evaluation"},
        "consequence": {"action": ["115BAB_NOT_AVAILABLE"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "incorporation_date", "operator": "lt", "value": "2019-10-01"}
                    ],
                }
            ],
            "then": {"incorporation_date_status": "INELIGIBLE_FOR_15PCT"},
        },
    },
    {
        "rule_id": "CORP.INCORP.003",
        "primitive_code": "CORP.INCORPORATION_DATE_STATUS",
        "name": "Ineligible because non-manufacturing",
        "source_reference": "Section 115BAB concept",
        "natural_language": "A company that is not engaged in manufacturing is not eligible for the 15 percent manufacturing track.",
        "mode": "CONTROL",
        "severity": "INFO",
        "trigger": {"event": "incorporation_evaluation"},
        "consequence": {"action": ["115BAB_NOT_AVAILABLE"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {
                            "field": "business_activity",
                            "operator": "not_equals",
                            "value": "MANUFACTURING",
                        }
                    ],
                }
            ],
            "then": {"incorporation_date_status": "INELIGIBLE_FOR_15PCT"},
        },
    },
    {
        "rule_id": "CORP.INCORP.004",
        "primitive_code": "CORP.INCORPORATION_DATE_STATUS",
        "name": "2026 onward eligibility review",
        "source_reference": "Section 115BAB concept limitation",
        "natural_language": "Even where the basic manufacturing test is met, the 2026 concept slice flags a forward-looking review requirement after 31 March 2026.",
        "mode": "ALERT",
        "severity": "WARNING",
        "trigger": {"event": "incorporation_evaluation"},
        "consequence": {"action": ["REVIEW_2026_FORWARD_ELIGIBILITY"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "incorporation_date", "operator": "gte", "value": "2019-10-01"},
                        {
                            "field": "business_activity",
                            "operator": "equals",
                            "value": "MANUFACTURING",
                        },
                    ],
                }
            ],
            "then": {"incorporation_date_status": "ELIGIBLE_FOR_15PCT"},
        },
    },
    {
        "rule_id": "CORP.REGIME.001",
        "primitive_code": "CORP.REGIME_TRACK",
        "name": "115BAA election intent",
        "source_reference": "Concessional 22 percent regime concept",
        "natural_language": "A domestic or deemed domestic company can express intent to opt for the 22 percent concessional track.",
        "mode": "ALERT",
        "severity": "WARNING",
        "trigger": {"event": "regime_selection"},
        "consequence": {"action": ["REVIEW_IRREVERSIBLE_115BAA_ELECTION"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {
                            "field": "entity_type",
                            "operator": "in",
                            "value": ["DOMESTIC_COMPANY", "DEEMED_DOMESTIC"],
                        },
                        {"field": "regime_option", "operator": "equals", "value": "OPT_115BAA"},
                    ],
                }
            ],
            "then": {"wants_115baa": True},
        },
    },
    {
        "rule_id": "CORP.REGIME.002",
        "primitive_code": "CORP.REGIME_TRACK",
        "name": "115BAB election intent",
        "source_reference": "Concessional 15 percent manufacturing regime concept",
        "natural_language": "A domestic or deemed domestic company can express intent to opt for the 15 percent manufacturing track only when the incorporation test is met.",
        "mode": "ALERT",
        "severity": "CRITICAL",
        "trigger": {"event": "regime_selection"},
        "consequence": {"action": ["REVIEW_IRREVERSIBLE_115BAB_ELECTION"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {
                            "field": "entity_type",
                            "operator": "in",
                            "value": ["DOMESTIC_COMPANY", "DEEMED_DOMESTIC"],
                        },
                        {"field": "regime_option", "operator": "equals", "value": "OPT_115BAB"},
                        {
                            "field": "incorporation_date_status",
                            "operator": "equals",
                            "value": "ELIGIBLE_FOR_15PCT",
                        },
                    ],
                }
            ],
            "then": {"wants_115bab": True},
        },
    },
    {
        "rule_id": "CORP.ROUTE.001",
        "primitive_code": "CORP.FILING_ROUTE",
        "name": "Domestic filing route review",
        "source_reference": "Corporate return filing concept",
        "natural_language": "Domestic and deemed domestic companies generally go through the company filing route and should be reviewed for audit pack completeness.",
        "mode": "ALERT",
        "severity": "WARNING",
        "trigger": {"event": "filing_route"},
        "consequence": {"action": ["AUDIT_PACK_REVIEW_REQUIRED"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "any",
                    "conditions": [
                        {"field": "entity_type", "operator": "equals", "value": "DOMESTIC_COMPANY"},
                        {"field": "entity_type", "operator": "equals", "value": "DEEMED_DOMESTIC"},
                    ],
                }
            ],
            "then": {"audit_flag": True},
        },
    },
    {
        "rule_id": "CORP.ROUTE.002",
        "primitive_code": "CORP.FILING_ROUTE",
        "name": "Foreign PE route review",
        "source_reference": "Foreign company filing concept",
        "natural_language": "A foreign company with a PE in India requires foreign-company filing review and treaty checks.",
        "mode": "ALERT",
        "severity": "CRITICAL",
        "trigger": {"event": "filing_route"},
        "consequence": {"action": ["DTAA_REVIEW_REQUIRED", "FOREIGN_TAX_PACK_REVIEW"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "entity_type", "operator": "equals", "value": "FOREIGN_COMPANY"},
                        {"field": "pe_status", "operator": "equals", "value": "PE_EXISTS"},
                    ],
                }
            ],
            "then": {"audit_flag": True},
        },
    },
    {
        "rule_id": "CORP.ROUTE.003",
        "primitive_code": "CORP.FILING_ROUTE",
        "name": "LLP filing route review",
        "source_reference": "LLP return filing concept",
        "natural_language": "An LLP follows the LLP filing path and should be reviewed for AMT and partner-reporting implications.",
        "mode": "ALERT",
        "severity": "WARNING",
        "trigger": {"event": "filing_route"},
        "consequence": {"action": ["LLP_COMPLIANCE_REVIEW"]},
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [{"field": "entity_type", "operator": "equals", "value": "LLP"}],
                }
            ],
            "then": {"audit_flag": True},
        },
    },
]

PRIMITIVES = [
    {
        "code": "CORP.ENTITY_TYPE",
        "name": "Corporate Entity Type",
        "question": "What type of corporate taxpayer is this entity?",
        "input_schema": {
            "registration_country": "string",
            "registration_act": "string",
            "management_control_in_india": "boolean",
        },
        "output_schema": {"entity_type": "string"},
        "rule_ids": ["CORP.CLASS.001", "CORP.CLASS.002", "CORP.CLASS.003"],
    },
    {
        "code": "CORP.PE_STATUS",
        "name": "Corporate PE Status",
        "question": "Does this entity have a permanent establishment in India?",
        "input_schema": {
            "entity_type": "string",
            "office_fixed_place_in_india": "boolean",
            "agents_dependent_in_india": "boolean",
            "construction_project_duration_days": "integer",
        },
        "output_schema": {"pe_status": "string"},
        "rule_ids": ["CORP.PE.001", "CORP.PE.002", "CORP.PE.003", "CORP.PE.004"],
    },
    {
        "code": "CORP.TURNOVER_CATEGORY",
        "name": "Corporate Turnover Category",
        "question": "Which turnover bucket applies for corporate rate-path decisions?",
        "input_schema": {
            "entity_type": "string",
            "previous_year_turnover": "integer",
        },
        "output_schema": {"turnover_category": "string"},
        "rule_ids": ["CORP.TURN.001", "CORP.TURN.002", "CORP.TURN.003", "CORP.TURN.004"],
    },
    {
        "code": "CORP.INCORPORATION_DATE_STATUS",
        "name": "Corporate Incorporation Date Status",
        "question": "Is the company eligible for the manufacturing concessional track based on incorporation facts?",
        "input_schema": {
            "registration_country": "string",
            "incorporation_date": "date",
            "business_activity": "string",
        },
        "output_schema": {"incorporation_date_status": "string"},
        "rule_ids": [
            "CORP.INCORP.001",
            "CORP.INCORP.002",
            "CORP.INCORP.003",
            "CORP.INCORP.004",
        ],
    },
    {
        "code": "CORP.REGIME_TRACK",
        "name": "Corporate Regime Track",
        "question": "Which regime track is being elected or inferred for this entity?",
        "input_schema": {
            "entity_type": "string",
            "turnover_category": "string",
            "incorporation_date_status": "string",
            "regime_option": "string",
        },
        "output_schema": {
            "wants_115baa": "boolean",
            "wants_115bab": "boolean",
        },
        "rule_ids": ["CORP.REGIME.001", "CORP.REGIME.002"],
    },
    {
        "code": "CORP.FILING_ROUTE",
        "name": "Corporate Filing Route",
        "question": "Which filing route and compliance review path applies?",
        "input_schema": {
            "entity_type": "string",
            "pe_status": "string",
            "regime_track": "string",
        },
        "output_schema": {"audit_flag": "boolean"},
        "rule_ids": ["CORP.ROUTE.001", "CORP.ROUTE.002", "CORP.ROUTE.003"],
    },
]

DECISION_TABLES = [
    {
        "code": "CORP.REGIME_SELECTION",
        "name": "Corporate Regime Selection",
        "input_primitive_codes": [
            "CORP.ENTITY_TYPE",
            "CORP.TURNOVER_CATEGORY",
            "CORP.INCORPORATION_DATE_STATUS",
            "CORP.REGIME_TRACK",
        ],
        "input_columns": [
            "entity_type",
            "turnover_category",
            "incorporation_date_status",
            "wants_115baa",
            "wants_115bab",
        ],
        "output_columns": ["regime_track"],
        "rows": [
            {
                "when": {"entity_type": "LLP"},
                "then": {"regime_track": "LLP_30PCT"},
            },
            {
                "when": {"entity_type": "FOREIGN_COMPANY"},
                "then": {"regime_track": "FOREIGN_35PCT"},
            },
            {
                "when": {"wants_115bab": True},
                "then": {"regime_track": "NEW_MANUFACTURING_15PCT"},
            },
            {
                "when": {"wants_115baa": True},
                "then": {"regime_track": "CONCESSIONAL_22PCT"},
            },
            {
                "when": {"entity_type": "DOMESTIC_COMPANY", "turnover_category": "BELOW_400CR"},
                "then": {"regime_track": "STANDARD_25PCT"},
            },
            {
                "when": {"entity_type": "DEEMED_DOMESTIC", "turnover_category": "BELOW_400CR"},
                "then": {"regime_track": "STANDARD_25PCT"},
            },
            {
                "when": {"entity_type": "DOMESTIC_COMPANY", "turnover_category": "ABOVE_400CR"},
                "then": {"regime_track": "STANDARD_30PCT"},
            },
            {
                "when": {"entity_type": "DEEMED_DOMESTIC", "turnover_category": "ABOVE_400CR"},
                "then": {"regime_track": "STANDARD_30PCT"},
            },
        ],
    },
    {
        "code": "CORP.FILING_ROUTE",
        "name": "Corporate Filing Route",
        "input_primitive_codes": [
            "CORP.ENTITY_TYPE",
            "CORP.PE_STATUS",
            "CORP.REGIME_TRACK",
            "CORP.FILING_ROUTE",
        ],
        "input_columns": ["entity_type", "pe_status", "regime_track", "audit_flag"],
        "output_columns": ["filing_route"],
        "rows": [
            {
                "when": {"entity_type": "LLP"},
                "then": {"filing_route": "ITR5_LLP"},
            },
            {
                "when": {"entity_type": "FOREIGN_COMPANY", "pe_status": "PE_EXISTS"},
                "then": {"filing_route": "ITR6_FOREIGN_WITH_PE_REVIEW"},
            },
            {
                "when": {"entity_type": "FOREIGN_COMPANY", "pe_status": "NO_PE"},
                "then": {"filing_route": "FOREIGN_COMPANY_REVIEW_REQUIRED"},
            },
            {
                "when": {"entity_type": "DOMESTIC_COMPANY"},
                "then": {"filing_route": "ITR6_DOMESTIC_COMPANY"},
            },
            {
                "when": {"entity_type": "DEEMED_DOMESTIC"},
                "then": {"filing_route": "ITR6_DOMESTIC_COMPANY"},
            },
        ],
    },
]

MODULE_CONTRACT_PROVIDES = [
    "entity_type",
    "pe_status",
    "turnover_category",
    "incorporation_date_status",
    "regime_track",
    "filing_route",
    "compliance_alerts",
]

MODULE_CONTRACT_CONSUMES = [
    "company_profile",
    "registration_facts",
    "turnover_facts",
    "incorporation_facts",
    "pe_indicators",
]


class Command(BaseCommand):
    help = "Seed the first corporate-tax concept slice for TY 2026-27."

    def handle(self, *args, **options):
        now = timezone.now()
        context, _ = AssessmentContext.objects.update_or_create(
            code="TY_2026_27",
            defaults={
                "assessment_year": "TY 2026-27",
                "financial_year": "FY 2025-26",
                "effective_from": date(2026, 4, 1),
                "effective_to": date(2027, 3, 31),
                "is_active": True,
                "metadata": {"domain": "corporate_tax"},
            },
        )

        for payload in RULES:
            rule_definition, _ = RuleDefinition.objects.update_or_create(
                rule_id=payload["rule_id"],
                defaults={
                    "name": payload["name"],
                    "scope": ScopeChoices.CORPORATE_TAX,
                    "description": payload["natural_language"],
                },
            )
            RuleVersion.objects.update_or_create(
                rule=rule_definition,
                version="1.0",
                defaults={
                    "status": StatusChoices.ACTIVE,
                    "source_reference": payload["source_reference"],
                    "natural_language": payload["natural_language"],
                    "structured_logic": payload["structured_logic"],
                    "mode": payload["mode"],
                    "trigger": payload["trigger"],
                    "consequence": payload["consequence"],
                    "severity": payload["severity"],
                    "approved_by": "seed-system",
                    "approved_at": now,
                    "metadata": {"assessment_context": context.code, "primitive_code": payload["primitive_code"]},
                },
            )

        primitive_versions = {}
        for payload in PRIMITIVES:
            primitive_definition, _ = PrimitiveDefinition.objects.update_or_create(
                code=payload["code"],
                defaults={
                    "name": payload["name"],
                    "module_scope": ScopeChoices.CORPORATE_TAX,
                    "question": payload["question"],
                    "description": payload["question"],
                },
            )
            primitive_version, _ = PrimitiveVersion.objects.update_or_create(
                primitive=primitive_definition,
                version="1.0",
                defaults={
                    "status": StatusChoices.ACTIVE,
                    "input_schema": payload["input_schema"],
                    "output_schema": payload["output_schema"],
                    "completeness_report": {"seeded": True, "assessment_context": context.code},
                    "approved_by": "seed-system",
                    "approved_at": now,
                },
            )
            rule_versions = list(
                RuleVersion.objects.filter(
                    rule__rule_id__in=payload["rule_ids"],
                    version="1.0",
                ).select_related("rule")
            )
            primitive_version.rules.set(rule_versions)
            primitive_versions[payload["code"]] = primitive_version

        decision_table_versions = {}
        for payload in DECISION_TABLES:
            decision_table_definition, _ = DecisionTableDefinition.objects.update_or_create(
                code=payload["code"],
                defaults={
                    "name": payload["name"],
                    "scope": ScopeChoices.CORPORATE_TAX,
                    "description": payload["name"],
                },
            )
            decision_table_version, _ = DecisionTableVersion.objects.update_or_create(
                decision_table=decision_table_definition,
                version="1.0",
                defaults={
                    "status": StatusChoices.ACTIVE,
                    "module_scope": ScopeChoices.CORPORATE_TAX,
                    "input_columns": payload["input_columns"],
                    "output_columns": payload["output_columns"],
                    "rows": payload["rows"],
                    "completeness_report": {"seeded": True, "assessment_context": context.code},
                    "approved_by": "seed-system",
                    "approved_at": now,
                },
            )
            decision_table_version.input_primitives.set(
                [primitive_versions[code] for code in payload["input_primitive_codes"]]
            )
            decision_table_versions[payload["code"]] = decision_table_version

        module_definition, _ = ModuleDefinition.objects.update_or_create(
            code="INDIA_CORPORATE_TAX",
            defaults={
                "name": "India Corporate Tax",
                "scope": ScopeChoices.CORPORATE_TAX,
                "description": "Corporate tax concept slice for TY 2026-27.",
            },
        )
        module_version, _ = ModuleVersion.objects.update_or_create(
            module=module_definition,
            version="1.0",
            defaults={
                "status": StatusChoices.ACTIVE,
                "assessment_context": context,
                "contract_provides": MODULE_CONTRACT_PROVIDES,
                "contract_consumes": MODULE_CONTRACT_CONSUMES,
                "fallback_behaviour": {"default_route": "CORP_REVIEW_REQUIRED"},
                "approved_by": "seed-system",
                "approved_at": now,
            },
        )
        module_version.primitives.set(list(primitive_versions.values()))
        module_version.decision_tables.set(list(decision_table_versions.values()))

        change_set, _ = ChangeSet.objects.update_or_create(
            code="CS.CORP.TY2026_27.INITIAL",
            defaults={
                "name": "Corporate Tax TY 2026-27 Initial Activation",
                "description": "Initial corporate concept slice activation bundle.",
                "assessment_context": context,
                "status": StatusChoices.ACTIVE,
                "impact_analysis": {"seeded": True},
                "activation_report": {
                    "seeded": True,
                    "activated_by": "seed-system",
                    "module_version": str(module_version),
                },
                "approved_by": "seed-system",
                "approved_at": now,
                "activated_at": now,
            },
        )
        change_set.rule_versions.set(
            RuleVersion.objects.filter(metadata__assessment_context=context.code, version="1.0")
        )
        change_set.primitive_versions.set(list(primitive_versions.values()))
        change_set.decision_table_versions.set(list(decision_table_versions.values()))
        change_set.module_versions.set([module_version])

        self.stdout.write(self.style.SUCCESS("Seeded corporate tax concept slice for TY 2026-27."))
