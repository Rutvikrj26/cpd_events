"""
Common filters for the API.
"""

import django_filters
from django.db.models import Q


class UUIDInFilter(django_filters.BaseInFilter, django_filters.UUIDFilter):
    """Filter for UUID__in lookups."""
    pass


class SoftDeleteFilter(django_filters.FilterSet):
    """Base filter that handles soft-delete."""
    include_deleted = django_filters.BooleanFilter(
        method='filter_include_deleted',
        label='Include deleted records'
    )
    
    def filter_include_deleted(self, queryset, name, value):
        if value:
            return queryset.model.all_objects.all()
        return queryset


class DateRangeFilter(django_filters.FilterSet):
    """Mixin for date range filtering."""
    from_date = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='date__gte',
        label='From date'
    )
    to_date = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='date__lte',
        label='To date'
    )


class BaseModelFilter(SoftDeleteFilter, DateRangeFilter):
    """Combined base filter with soft-delete and date range."""
    pass
