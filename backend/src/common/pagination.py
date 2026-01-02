"""
Common pagination classes for the API.
"""

from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response

from common.config import Pagination, ThrottleRates


class StandardPagination(PageNumberPagination):
    """
    Standard pagination with customizable page size.

    Query params:
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
    """

    page_size = Pagination.DEFAULT_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = Pagination.MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        return Response(
            {
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'total_pages': self.page.paginator.num_pages,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data,
            }
        )


class CursorPaginationByCreated(CursorPagination):
    """
    Cursor-based pagination for large datasets.

    More efficient for large offsets and stable when items are added.
    """

    page_size = Pagination.DEFAULT_PAGE_SIZE
    ordering = '-created_at'
    cursor_query_param = 'cursor'


class SmallPagination(PageNumberPagination):
    """Smaller page size for nested resources."""

    page_size = Pagination.SMALL_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = Pagination.SMALL_MAX_PAGE_SIZE


# =============================================================================
# Throttle Classes (M6)
# =============================================================================

from rest_framework.throttling import UserRateThrottle


class BulkOperationThrottle(UserRateThrottle):
    """
    Rate limiting for bulk operations (M6).

    More restrictive than regular operations to prevent abuse.
    """

    rate = ThrottleRates.BULK
    scope = 'bulk'


class ImportThrottle(UserRateThrottle):
    """Rate limiting for import operations."""

    rate = ThrottleRates.IMPORT
    scope = 'import'


class ExportThrottle(UserRateThrottle):
    """Rate limiting for export/download operations."""

    rate = ThrottleRates.EXPORT
    scope = 'export'
