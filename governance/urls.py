from django.urls import path

from .views import (
    GovernanceCrossModuleEvaluationView,
    GovernanceHealthView,
    GovernanceRecentEvaluationsView,
)

urlpatterns = [
    path("", GovernanceHealthView.as_view(), name="governance-health"),
    path(
        "cross-module-evaluation/",
        GovernanceCrossModuleEvaluationView.as_view(),
        name="governance-cross-module-evaluation",
    ),
    path("evaluations/", GovernanceRecentEvaluationsView.as_view(), name="governance-evaluations"),
]
