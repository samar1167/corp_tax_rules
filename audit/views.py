from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EvaluationLog
from .serializers import EvaluationLogSerializer


class AuditHealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class EvaluationLogListView(APIView):
    def get(self, request):
        queryset = EvaluationLog.objects.select_related(
            "assessment_context",
            "module_version",
        ).all()

        assessment_context = request.query_params.get("assessment_context")
        event_id = request.query_params.get("event_id")

        if assessment_context:
            queryset = queryset.filter(assessment_context__code=assessment_context)
        if event_id:
            queryset = queryset.filter(event_id=event_id)

        serializer = EvaluationLogSerializer(queryset[:50], many=True)
        return Response(serializer.data)


class EvaluationLogDetailView(APIView):
    def get(self, request, event_id):
        evaluation_log = EvaluationLog.objects.select_related(
            "assessment_context",
            "module_version",
        ).get(event_id=event_id)
        serializer = EvaluationLogSerializer(evaluation_log)
        return Response(serializer.data)
