from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from core_rules.models import (
    AssessmentContext,
    ChangeSet,
    ModuleDefinition,
    ModuleVersion,
    ScopeChoices,
    StatusChoices,
)

from governance.models import CrossModuleRule


RULES = [
    {
        "rule_id": "GOV.CROSS.001",
        "name": "Director linked company disclosure review",
        "source_reference": "Prototype governance relationship rule",
        "natural_language": "If the linked individual is a company director and the company is on the domestic ITR6 path, trigger related disclosure review.",
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "itr.is_director_in_company", "operator": "equals", "value": True},
                        {
                            "field": "corporate.filing_route",
                            "operator": "equals",
                            "value": "ITR6_DOMESTIC_COMPANY",
                        },
                    ],
                }
            ],
            "then": {
                "governance_actions": [
                    "RELATED_DIRECTOR_DISCLOSURE_REVIEW",
                    "RECONCILE_INDIVIDUAL_COMPANY_DISCLOSURES",
                ]
            },
        },
    },
    {
        "rule_id": "GOV.CROSS.002",
        "name": "Cross-border disclosure review",
        "source_reference": "Prototype governance relationship rule",
        "natural_language": "If the individual has foreign-asset disclosure and the related company has a PE in India, trigger cross-border governance review.",
        "structured_logic": {
            "when": [
                {
                    "operator": "all",
                    "conditions": [
                        {"field": "itr.has_foreign_assets", "operator": "equals", "value": True},
                        {"field": "corporate.pe_status", "operator": "equals", "value": "PE_EXISTS"},
                    ],
                }
            ],
            "then": {
                "governance_actions": [
                    "CROSS_BORDER_DISCLOSURE_REVIEW",
                    "DTAA_AND_FOREIGN_ASSET_ALIGNMENT_REVIEW",
                ]
            },
        },
    },
]


class Command(BaseCommand):
    help = "Seed the first governance cross-module concept slice for 2026-27."

    def handle(self, *args, **options):
        now = timezone.now()
        context, _ = AssessmentContext.objects.update_or_create(
            code="GOV_2026_27",
            defaults={
                "assessment_year": "GOV 2026-27",
                "financial_year": "FY 2025-26",
                "effective_from": date(2026, 4, 1),
                "effective_to": date(2027, 3, 31),
                "is_active": True,
                "metadata": {"domain": "governance"},
            },
        )
        module_definition, _ = ModuleDefinition.objects.update_or_create(
            code="INDIA_TAX_GOVERNANCE",
            defaults={
                "name": "India Tax Governance",
                "scope": ScopeChoices.GOVERNANCE,
                "description": "Cross-module governance concept slice for 2026-27.",
            },
        )
        module_version, _ = ModuleVersion.objects.update_or_create(
            module=module_definition,
            version="1.0",
            defaults={
                "status": StatusChoices.ACTIVE,
                "assessment_context": context,
                "contract_provides": ["governance_status", "governance_actions"],
                "contract_consumes": ["itr_module_outputs", "corporate_module_outputs"],
                "fallback_behaviour": {"default_status": "CLEAR"},
                "approved_by": "seed-system",
                "approved_at": now,
            },
        )
        dependency_modules = list(
            ModuleVersion.objects.filter(
                module__code__in=["INDIA_INDIVIDUAL_TAX", "INDIA_CORPORATE_TAX"],
                status="ACTIVE",
            )
        )
        for payload in RULES:
            rule, _ = CrossModuleRule.objects.update_or_create(
                rule_id=payload["rule_id"],
                version="1.0",
                defaults={
                    "name": payload["name"],
                    "status": StatusChoices.ACTIVE,
                    "source_reference": payload["source_reference"],
                    "natural_language": payload["natural_language"],
                    "structured_logic": payload["structured_logic"],
                    "approved_by": "seed-system",
                    "approved_at": now,
                },
            )
            rule.depends_on_modules.set(dependency_modules + [module_version])

        change_set, _ = ChangeSet.objects.update_or_create(
            code="CS.GOV.2026_27.INITIAL",
            defaults={
                "name": "Governance 2026-27 Initial Activation",
                "description": "Initial governance cross-module activation bundle.",
                "assessment_context": context,
                "status": StatusChoices.ACTIVE,
                "impact_analysis": {"seeded": True},
                "activation_report": {"seeded": True, "activated_by": "seed-system"},
                "approved_by": "seed-system",
                "approved_at": now,
                "activated_at": now,
            },
        )
        change_set.module_versions.set([module_version])

        self.stdout.write(self.style.SUCCESS("Seeded governance cross-module concept slice for 2026-27."))
