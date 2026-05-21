from django.urls import path

from .views import AuditHealthView, EvaluationLogDetailView, EvaluationLogListView

urlpatterns = [
    path("", AuditHealthView.as_view(), name="audit-health"),
    path("evaluation-logs/", EvaluationLogListView.as_view(), name="evaluation-log-list"),
    path(
        "evaluation-logs/<str:event_id>/",
        EvaluationLogDetailView.as_view(),
        name="evaluation-log-detail",
    ),
]
