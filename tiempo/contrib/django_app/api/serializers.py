from rest_framework import serializers
from rest_framework.pagination import LimitOffsetPagination

from tiempo.utils import JobReport


class JobsPaginator(LimitOffsetPagination):

    default_limit = 50
    offset = 0


class JobSerializer(serializers.BaseSerializer):

    def to_representation(self, obj):
        return obj
