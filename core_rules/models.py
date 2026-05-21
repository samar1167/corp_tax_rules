from django.core.exceptions import ValidationError
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ImmutableApprovedModel(models.Model):
    immutable_statuses: tuple[str, ...] = ()

    class Meta:
        abstract = True

    def _loaded_values(self) -> dict:
        if not self.pk:
            return {}
        loaded = type(self).objects.filter(pk=self.pk).values().first()
        return loaded or {}

    def clean(self) -> None:
        super().clean()
        if not self.pk or not self.immutable_statuses:
            return
        existing = self._loaded_values()
        if not existing:
            return
        if existing.get("status") not in self.immutable_statuses:
            return

        mutable_fields = {"updated_at", "approved_at", "activated_at"}
        for field in self._meta.fields:
            if field.name in mutable_fields:
                continue
            if getattr(self, field.attname) != existing.get(field.attname):
                raise ValidationError(
                    f"{type(self).__name__} records in status "
                    f"{existing['status']} are immutable and must be superseded."
                )


class ProtectedLifecycleDeleteModel(models.Model):
    deletable_statuses: tuple[str, ...] = ()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        status = getattr(self, "status", None)
        if self.deletable_statuses and status not in self.deletable_statuses:
            raise ValidationError(
                f"{type(self).__name__} records in status {status} cannot be deleted."
            )
        return super().delete(using=using, keep_parents=keep_parents)


class StatusChoices(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    APPROVED = "APPROVED", "Approved"
    ACTIVE = "ACTIVE", "Active"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class RuleModeChoices(models.TextChoices):
    OBSERVER = "OBSERVER", "Observer"
    ALERT = "ALERT", "Alert"
    CONTROL = "CONTROL", "Control"
    DESIGNER = "DESIGNER", "Designer"


class SeverityChoices(models.TextChoices):
    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    CRITICAL = "CRITICAL", "Critical"
    ABSOLUTE = "ABSOLUTE", "Absolute"


class ModuleStatusChoices(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    APPROVED = "APPROVED", "Approved"
    ACTIVE = "ACTIVE", "Active"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class ScopeChoices(models.TextChoices):
    ITR = "ITR", "ITR"
    CORPORATE_TAX = "CORPORATE_TAX", "Corporate Tax"
    GOVERNANCE = "GOVERNANCE", "Governance"
    SHARED = "SHARED", "Shared"


class AssessmentContext(TimestampedModel):
    code = models.CharField(max_length=50, unique=True)
    assessment_year = models.CharField(max_length=20)
    financial_year = models.CharField(max_length=20, blank=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-effective_from", "code"]

    def __str__(self) -> str:
        return self.code


class RuleDefinition(TimestampedModel):
    rule_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    scope = models.CharField(max_length=32, choices=ScopeChoices.choices)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["rule_id"]

    def __str__(self) -> str:
        return self.rule_id


class RuleVersion(ProtectedLifecycleDeleteModel, ImmutableApprovedModel, TimestampedModel):
    immutable_statuses = (StatusChoices.APPROVED, StatusChoices.ACTIVE, StatusChoices.SUPERSEDED)
    deletable_statuses = (StatusChoices.DRAFT,)

    rule = models.ForeignKey(
        RuleDefinition,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version = models.CharField(max_length=32)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    source_reference = models.CharField(max_length=255)
    natural_language = models.TextField()
    structured_logic = models.JSONField(default=dict)
    mode = models.CharField(max_length=16, choices=RuleModeChoices.choices)
    trigger = models.JSONField(default=dict, blank=True)
    consequence = models.JSONField(default=dict, blank=True)
    severity = models.CharField(max_length=16, choices=SeverityChoices.choices)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["rule__rule_id", "-created_at"]
        unique_together = [("rule", "version")]

    def __str__(self) -> str:
        return f"{self.rule.rule_id}@{self.version}"

    def clean(self) -> None:
        super().clean()
        if self.status in {StatusChoices.APPROVED, StatusChoices.ACTIVE} and not self.approved_by:
            raise ValidationError("Approved or active rule versions must include approved_by.")


class PrimitiveDefinition(TimestampedModel):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    module_scope = models.CharField(max_length=32, choices=ScopeChoices.choices)
    question = models.TextField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class PrimitiveVersion(ProtectedLifecycleDeleteModel, ImmutableApprovedModel, TimestampedModel):
    immutable_statuses = (StatusChoices.APPROVED, StatusChoices.ACTIVE, StatusChoices.SUPERSEDED)
    deletable_statuses = (StatusChoices.DRAFT,)

    primitive = models.ForeignKey(
        PrimitiveDefinition,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version = models.CharField(max_length=32)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    rules = models.ManyToManyField(RuleVersion, related_name="primitive_versions", blank=True)
    input_schema = models.JSONField(default=dict, blank=True)
    output_schema = models.JSONField(default=dict, blank=True)
    completeness_report = models.JSONField(default=dict, blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["primitive__code", "-created_at"]
        unique_together = [("primitive", "version")]

    def __str__(self) -> str:
        return f"{self.primitive.code}@{self.version}"


class ModuleDefinition(TimestampedModel):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    scope = models.CharField(max_length=32, choices=ScopeChoices.choices)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class DecisionTableDefinition(TimestampedModel):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    scope = models.CharField(max_length=32, choices=ScopeChoices.choices)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class DecisionTableVersion(ProtectedLifecycleDeleteModel, ImmutableApprovedModel, TimestampedModel):
    immutable_statuses = (StatusChoices.APPROVED, StatusChoices.ACTIVE, StatusChoices.SUPERSEDED)
    deletable_statuses = (StatusChoices.DRAFT,)

    decision_table = models.ForeignKey(
        DecisionTableDefinition,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version = models.CharField(max_length=32)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    module_scope = models.CharField(max_length=32, choices=ScopeChoices.choices)
    input_primitives = models.ManyToManyField(
        PrimitiveVersion,
        related_name="decision_table_versions",
        blank=True,
    )
    input_columns = models.JSONField(default=list, blank=True)
    output_columns = models.JSONField(default=list, blank=True)
    rows = models.JSONField(default=list, blank=True)
    completeness_report = models.JSONField(default=dict, blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["decision_table__code", "-created_at"]
        unique_together = [("decision_table", "version")]

    def __str__(self) -> str:
        return f"{self.decision_table.code}@{self.version}"


class ModuleVersion(ProtectedLifecycleDeleteModel, ImmutableApprovedModel, TimestampedModel):
    immutable_statuses = (
        ModuleStatusChoices.APPROVED,
        ModuleStatusChoices.ACTIVE,
        ModuleStatusChoices.SUPERSEDED,
    )
    deletable_statuses = (ModuleStatusChoices.DRAFT,)

    module = models.ForeignKey(
        ModuleDefinition,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version = models.CharField(max_length=32)
    status = models.CharField(
        max_length=20,
        choices=ModuleStatusChoices.choices,
        default=ModuleStatusChoices.DRAFT,
    )
    assessment_context = models.ForeignKey(
        AssessmentContext,
        on_delete=models.PROTECT,
        related_name="module_versions",
    )
    primitives = models.ManyToManyField(
        PrimitiveVersion,
        related_name="module_versions",
        blank=True,
    )
    decision_tables = models.ManyToManyField(
        DecisionTableVersion,
        related_name="module_versions",
        blank=True,
    )
    contract_provides = models.JSONField(default=list, blank=True)
    contract_consumes = models.JSONField(default=list, blank=True)
    fallback_behaviour = models.JSONField(default=dict, blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["module__code", "-created_at"]
        unique_together = [("module", "version")]

    def __str__(self) -> str:
        return f"{self.module.code}@{self.version}"


class ChangeSet(ProtectedLifecycleDeleteModel, ImmutableApprovedModel, TimestampedModel):
    immutable_statuses = (StatusChoices.APPROVED, StatusChoices.ACTIVE, StatusChoices.SUPERSEDED)
    deletable_statuses = (StatusChoices.DRAFT,)

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assessment_context = models.ForeignKey(
        AssessmentContext,
        on_delete=models.PROTECT,
        related_name="change_sets",
    )
    rule_versions = models.ManyToManyField(
        RuleVersion,
        related_name="change_sets",
        blank=True,
    )
    primitive_versions = models.ManyToManyField(
        PrimitiveVersion,
        related_name="change_sets",
        blank=True,
    )
    decision_table_versions = models.ManyToManyField(
        DecisionTableVersion,
        related_name="change_sets",
        blank=True,
    )
    module_versions = models.ManyToManyField(
        ModuleVersion,
        related_name="change_sets",
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    impact_analysis = models.JSONField(default=dict, blank=True)
    activation_report = models.JSONField(default=dict, blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "code"]

    def __str__(self) -> str:
        return self.code
