from rest_framework import viewsets
from tiempo.contrib.django_app.api.serializers import JobSerializer, JobsPaginator
from tiempo.utils import JobReport


class TiempoHistoryViewSet(viewsets.GenericViewSet):
    pagination_class = JobsPaginator
    serializer_class = JobSerializer
    queryset = JobReport()

    def list(self, request):
        paginated = self.paginate_queryset(self.get_queryset())
        response = self.get_paginated_response(paginated)
        return response


