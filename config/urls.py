from django.contrib import admin
from django.urls import include, path

from core_rules.ui_views import (
    DecisionTableVersionDetailView,
    ModuleVersionDetailView,
    PromotionGuideView,
    PrimitiveVersionDetailView,
    RuleVersionDetailView,
    WorkflowActionView,
    WorkflowDashboardView,
)

urlpatterns = [
    path("", WorkflowDashboardView.as_view(), name="workflow-dashboard"),
    path("workflow/", WorkflowDashboardView.as_view(), name="workflow-dashboard-alt"),
    path("workflow/promotion/", PromotionGuideView.as_view(), name="workflow-promotion"),
    path("workflow/action/", WorkflowActionView.as_view(), name="workflow-action"),
    path("workflow/rules/<int:pk>/", RuleVersionDetailView.as_view(), name="rule-version-detail"),
    path("workflow/primitives/<int:pk>/", PrimitiveVersionDetailView.as_view(), name="primitive-version-detail"),
    path(
        "workflow/decision-tables/<int:pk>/",
        DecisionTableVersionDetailView.as_view(),
        name="decision-table-version-detail",
    ),
    path("workflow/modules/<int:pk>/", ModuleVersionDetailView.as_view(), name="module-version-detail"),
    path("admin/", admin.site.urls),
    path("api/core-rules/", include("core_rules.urls")),
    path("api/itr/", include("itr.urls")),
    path("api/corporate-tax/", include("corporate_tax.urls")),
    path("api/governance/", include("governance.urls")),
    path("api/audit/", include("audit.urls")),
]
