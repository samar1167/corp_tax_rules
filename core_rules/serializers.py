from rest_framework import serializers

from .models import (
    AssessmentContext,
    DecisionTableDefinition,
    DecisionTableVersion,
    ChangeSet,
    ModuleDefinition,
    ModuleVersion,
    PrimitiveDefinition,
    PrimitiveVersion,
    RuleDefinition,
    RuleVersion,
)


class AssessmentContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentContext
        fields = "__all__"


class RuleDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleDefinition
        fields = "__all__"


class RuleVersionSerializer(serializers.ModelSerializer):
    rule = RuleDefinitionSerializer(read_only=True)
    rule_id = serializers.PrimaryKeyRelatedField(
        source="rule",
        queryset=RuleDefinition.objects.all(),
        write_only=True,
    )

    class Meta:
        model = RuleVersion
        fields = [
            "id",
            "rule",
            "rule_id",
            "version",
            "status",
            "source_reference",
            "natural_language",
            "structured_logic",
            "mode",
            "trigger",
            "consequence",
            "severity",
            "approved_by",
            "approved_at",
            "metadata",
            "created_at",
            "updated_at",
        ]


class PrimitiveDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrimitiveDefinition
        fields = "__all__"


class PrimitiveVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrimitiveVersion
        fields = "__all__"


class ModuleDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleDefinition
        fields = "__all__"


class ModuleVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleVersion
        fields = "__all__"


class DecisionTableDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionTableDefinition
        fields = "__all__"


class DecisionTableVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionTableVersion
        fields = "__all__"


class ModuleReadinessIssueSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.JSONField()


class ModuleReadinessReportSerializer(serializers.Serializer):
    module_code = serializers.CharField()
    assessment_context = serializers.CharField()
    is_ready = serializers.BooleanField()
    module_version = serializers.CharField(allow_null=True)
    summary = serializers.JSONField()
    issues = ModuleReadinessIssueSerializer(many=True)


class ChangeSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeSet
        fields = "__all__"


class ChangeSetActivationReportSerializer(serializers.Serializer):
    change_set_code = serializers.CharField()
    assessment_context = serializers.CharField()
    is_ready = serializers.BooleanField()
    summary = serializers.JSONField()
    issues = ModuleReadinessIssueSerializer(many=True)


class DraftChangeSetBundleSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    assessment_context = serializers.CharField()
    rule_version_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )
    primitive_version_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )
    decision_table_version_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )
    module_version_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )


class DraftChangeSetBundleResultSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    code = serializers.CharField()
    name = serializers.CharField()
    status = serializers.CharField()
    assessment_context = serializers.CharField()
    summary = serializers.JSONField()


class ApprovalActionSerializer(serializers.Serializer):
    approved_by = serializers.CharField(required=False, allow_blank=True, default="system")


class ActivationActionSerializer(serializers.Serializer):
    activated_by = serializers.CharField(required=False, allow_blank=True, default="system")


class LifecycleTransitionResultSerializer(serializers.Serializer):
    transitioned = serializers.BooleanField()
    object_type = serializers.CharField()
    object_label = serializers.CharField()
    from_status = serializers.CharField()
    to_status = serializers.CharField()
    readiness = serializers.JSONField()


class ChangeSetActivationResultSerializer(serializers.Serializer):
    activated = serializers.BooleanField()
    change_set_code = serializers.CharField()
    from_status = serializers.CharField()
    to_status = serializers.CharField()
    activated_at = serializers.CharField()
    summary = serializers.JSONField()


class RuleVersionSupersedeSerializer(serializers.Serializer):
    source_rule_version_id = serializers.IntegerField()


class RuleVersionSupersedeResultSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    source_rule_version = serializers.CharField()
    new_rule_version = serializers.CharField()
    status = serializers.CharField()


class PrimitiveVersionSupersedeSerializer(serializers.Serializer):
    source_primitive_version_id = serializers.IntegerField()
    replacement_rule_version_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )


class PrimitiveVersionSupersedeResultSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    source_primitive_version = serializers.CharField()
    new_primitive_version = serializers.CharField()
    status = serializers.CharField()
    rule_versions = serializers.ListField(child=serializers.CharField())


class DeleteResultSerializer(serializers.Serializer):
    deleted = serializers.BooleanField()
    message = serializers.CharField()
