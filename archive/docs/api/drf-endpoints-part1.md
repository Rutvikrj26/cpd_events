# Django REST Framework API Layer Specification

## Overview

This document specifies the complete DRF implementation for the platform, including serializers, viewsets, permissions, and routing. Following this spec enables auto-generation of OpenAPI documentation via `drf-spectacular`.

**Design Principles:**
- UUIDs for all external-facing identifiers (never expose integer PKs)
- Consistent response envelope and error format
- Proper queryset optimization (select_related, prefetch_related)
- Role-based permissions with object-level checks
- Soft-delete aware querysets
- Comprehensive filtering, search, and ordering

---

## Table of Contents

1. [Foundation & Configuration](#foundation--configuration)
2. [Common Components](#common-components)
3. [Accounts API](#accounts-api)
4. [Events API](#events-api)
5. [Registrations API](#registrations-api)
6. [Certificates API](#certificates-api)
7. [Contacts API](#contacts-api)
8. [Billing API](#billing-api)
9. [Learning API](#learning-api)
10. [Recordings API](#recordings-api)
11. [Webhooks](#webhooks)

---

## Foundation & Configuration

### Settings Configuration

```python
# config/settings/base.py

REST_FRAMEWORK = {
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # For browsable API
    ],
    
    # Permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    
    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    
    # Filtering
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    
    # Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'auth': '20/hour',  # Login/signup attempts
    },
    
    # Rendering
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',  # Dev only
    ],
    
    # Parsing
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    
    # Exception handling
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    
    # Schema
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
    # Versioning (optional)
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'uuid',
    'USER_ID_CLAIM': 'user_uuid',
}

# Spectacular Settings (OpenAPI generation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'CPD Platform API',
    'DESCRIPTION': 'API for managing events, certificates, and CPD tracking',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/v[0-9]',
}
```

---

### Pagination

```python
# common/pagination.py

from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Standard pagination with customizable page size.
    
    Query params:
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
    
    Response includes:
        count: Total items
        next: Next page URL
        previous: Previous page URL
        results: Page data
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'total_pages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })


class CursorPaginationByCreated(CursorPagination):
    """
    Cursor-based pagination for large datasets or real-time feeds.
    
    More efficient for large offsets and provides stable pagination
    when items are being added.
    """
    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'


class CursorPaginationByUpdated(CursorPagination):
    """Cursor pagination ordered by update time."""
    page_size = 20
    ordering = '-updated_at'
    cursor_query_param = 'cursor'
```

---

### Exception Handling

```python
# common/exceptions.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error responses.
    
    Response format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...}  # Optional field-level errors
        }
    }
    """
    # Call default handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        error_payload = {
            'error': {
                'code': _get_error_code(exc),
                'message': _get_error_message(exc, response),
                'details': _get_error_details(exc, response),
            }
        }
        response.data = error_payload
    
    # Handle Django ValidationError
    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Validation failed',
                    'details': exc.message_dict if hasattr(exc, 'message_dict') else {'__all__': exc.messages},
                }
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return response


def _get_error_code(exc):
    """Map exception to error code."""
    from rest_framework.exceptions import (
        AuthenticationFailed, NotAuthenticated, PermissionDenied,
        NotFound, ValidationError, Throttled
    )
    
    error_codes = {
        AuthenticationFailed: 'AUTHENTICATION_FAILED',
        NotAuthenticated: 'NOT_AUTHENTICATED',
        PermissionDenied: 'PERMISSION_DENIED',
        NotFound: 'NOT_FOUND',
        ValidationError: 'VALIDATION_ERROR',
        Throttled: 'RATE_LIMITED',
    }
    
    return error_codes.get(type(exc), 'ERROR')


def _get_error_message(exc, response):
    """Extract human-readable message."""
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, str):
            return exc.detail
        if isinstance(exc.detail, list):
            return exc.detail[0] if exc.detail else 'An error occurred'
    return 'An error occurred'


def _get_error_details(exc, response):
    """Extract field-level error details."""
    if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
        return exc.detail
    return None


# Custom Exceptions
class ConflictError(Exception):
    """409 Conflict - Resource state conflict."""
    status_code = status.HTTP_409_CONFLICT
    default_code = 'CONFLICT'
    
    def __init__(self, message='Resource conflict'):
        self.detail = message


class BusinessRuleViolation(Exception):
    """422 Unprocessable Entity - Business rule violation."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = 'BUSINESS_RULE_VIOLATION'
    
    def __init__(self, message, code=None):
        self.detail = message
        self.code = code or self.default_code
```

---

## Common Components

### Base Serializers

```python
# common/serializers.py

from rest_framework import serializers


class UUIDLookupMixin:
    """
    Mixin to use UUID for lookups instead of PK.
    
    Use with ModelSerializer to ensure UUIDs are used
    for all external references.
    """
    def get_fields(self):
        fields = super().get_fields()
        # Remove 'id' field if present
        fields.pop('id', None)
        return fields


class TimestampMixin(serializers.Serializer):
    """Standard timestamp fields."""
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class BaseModelSerializer(UUIDLookupMixin, serializers.ModelSerializer):
    """
    Base serializer for all models.
    
    Provides:
    - UUID as primary identifier
    - Timestamps (read-only)
    - Excludes internal 'id' field
    """
    uuid = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class SoftDeleteModelSerializer(BaseModelSerializer):
    """
    Base serializer for soft-delete models.
    
    Adds is_deleted indicator (read-only).
    """
    is_deleted = serializers.BooleanField(read_only=True)


# Nested serializer pattern for related objects
class MinimalUserSerializer(serializers.Serializer):
    """Minimal user representation for embedding."""
    uuid = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField()


class MinimalEventSerializer(serializers.Serializer):
    """Minimal event representation for embedding."""
    uuid = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.SlugField()
    starts_at = serializers.DateTimeField()
    status = serializers.CharField()
```

---

### Base ViewSets

```python
# common/viewsets.py

from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from django.db.models import Q


class UUIDLookupMixin:
    """
    Use UUID for object lookups instead of PK.
    
    Changes lookup from /api/events/1/ to /api/events/550e8400-.../
    """
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'


class SoftDeleteMixin:
    """
    Handle soft-delete in viewsets.
    
    - Default queryset excludes deleted items
    - DELETE performs soft delete
    - Adds restore action
    """
    
    def get_queryset(self):
        """Override to use default manager (excludes deleted)."""
        qs = super().get_queryset()
        # Already filtered by SoftDeleteManager, but be explicit
        if hasattr(qs.model, 'deleted_at'):
            qs = qs.filter(deleted_at__isnull=True)
        return qs
    
    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        instance.soft_delete()
    
    def get_include_deleted(self):
        """Check if request wants deleted items."""
        return self.request.query_params.get('include_deleted', '').lower() == 'true'


class BaseModelViewSet(UUIDLookupMixin, viewsets.ModelViewSet):
    """
    Base viewset for standard models.
    
    Provides:
    - UUID-based lookups
    - Standard CRUD operations
    - Consistent response format
    """
    
    def get_serializer_context(self):
        """Add request to serializer context."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class SoftDeleteModelViewSet(SoftDeleteMixin, BaseModelViewSet):
    """
    Base viewset for soft-delete models.
    
    Provides:
    - Soft delete on DELETE
    - Optional include_deleted query param
    - Restore action
    """
    
    from rest_framework.decorators import action
    
    @action(detail=True, methods=['post'])
    def restore(self, request, uuid=None):
        """Restore a soft-deleted object."""
        # Use all_objects to find deleted items
        instance = self.get_queryset().model.all_objects.get(uuid=uuid)
        instance.restore()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ReadOnlyModelViewSet(UUIDLookupMixin, viewsets.ReadOnlyModelViewSet):
    """Base viewset for read-only resources."""
    pass


# Mixins for specific operation sets
class CreateListRetrieveViewSet(
    UUIDLookupMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """ViewSet for create, list, retrieve (no update/delete)."""
    pass


class ListRetrieveUpdateViewSet(
    UUIDLookupMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    """ViewSet for list, retrieve, update (no create/delete)."""
    pass
```

---

### Permissions

```python
# common/permissions.py

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Object-level permission: only owner can access.
    
    Expects model to have 'owner' field pointing to User.
    """
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission: owner can edit, others read-only.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class IsOrganizer(permissions.BasePermission):
    """
    Only users with organizer account type.
    """
    message = "Organizer account required."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.account_type == 'organizer'
        )


class IsOrganizerOrReadOnly(permissions.BasePermission):
    """
    Organizers can write, everyone can read.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user.is_authenticated and 
            request.user.account_type == 'organizer'
        )


class IsEventOwner(permissions.BasePermission):
    """
    Permission for event-related objects.
    
    Checks if user owns the parent event.
    """
    def has_object_permission(self, request, view, obj):
        # Handle different object types
        if hasattr(obj, 'event'):
            return obj.event.owner == request.user
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False


class IsRegistrant(permissions.BasePermission):
    """
    Permission for registration-owned objects.
    
    User can access their own registrations.
    """
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'registration'):
            return obj.registration.user == request.user
        return False


class IsEventOwnerOrRegistrant(permissions.BasePermission):
    """
    Either event owner or the registrant can access.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Check if owner
        if hasattr(obj, 'event') and obj.event.owner == user:
            return True
        if hasattr(obj, 'owner') and obj.owner == user:
            return True
        
        # Check if registrant
        if hasattr(obj, 'user') and obj.user == user:
            return True
        if hasattr(obj, 'registration') and obj.registration.user == user:
            return True
        
        return False


class HasActiveSubscription(permissions.BasePermission):
    """
    Organizer must have active subscription for certain actions.
    """
    message = "Active subscription required."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.account_type != 'organizer':
            return True  # Non-organizers don't need subscription
        
        subscription = getattr(request.user, 'subscription', None)
        if not subscription:
            return False
        return subscription.status in ['active', 'trialing']


class IsPublicOrAuthenticated(permissions.BasePermission):
    """
    Allow access to public resources, require auth for private.
    
    Used for events with visibility settings.
    """
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'visibility'):
            if obj.visibility == 'public':
                return True
        return request.user.is_authenticated
```

---

### Filters

```python
# common/filters.py

import django_filters
from django.db.models import Q


class UUIDInFilter(django_filters.BaseInFilter, django_filters.UUIDFilter):
    """Filter for UUID__in lookups."""
    pass


class SoftDeleteFilter(django_filters.FilterSet):
    """
    Base filter that handles soft-delete.
    
    Adds 'include_deleted' filter option.
    """
    include_deleted = django_filters.BooleanFilter(
        method='filter_include_deleted',
        label='Include deleted records'
    )
    
    def filter_include_deleted(self, queryset, name, value):
        if value:
            return queryset.model.all_objects.all()
        return queryset


class DateRangeFilter(django_filters.FilterSet):
    """
    Mixin for date range filtering.
    
    Provides from_date and to_date filters.
    """
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
```

---

### Mixins for Common Patterns

```python
# common/mixins.py

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


class BulkCreateMixin:
    """
    Mixin to support bulk creation.
    
    POST /api/resource/bulk/
    Body: [{"field": "value"}, {"field": "value"}]
    """
    
    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk_create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def perform_bulk_create(self, serializer):
        serializer.save()


class BulkUpdateMixin:
    """
    Mixin to support bulk updates.
    
    PATCH /api/resource/bulk/
    Body: [{"uuid": "...", "field": "value"}, ...]
    """
    
    @action(detail=False, methods=['patch'], url_path='bulk')
    def bulk_update(self, request):
        uuids = [item.get('uuid') for item in request.data]
        instances = self.get_queryset().filter(uuid__in=uuids)
        
        # Map instances by UUID
        instance_map = {str(i.uuid): i for i in instances}
        
        updated = []
        for item_data in request.data:
            uuid = item_data.get('uuid')
            instance = instance_map.get(uuid)
            if instance:
                serializer = self.get_serializer(
                    instance, data=item_data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
                updated.append(serializer.data)
        
        return Response(updated)


class ExportMixin:
    """
    Mixin to support CSV/Excel export.
    
    GET /api/resource/export/?format=csv
    """
    export_fields = None  # Override in viewset
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        
        format = request.query_params.get('format', 'csv')
        queryset = self.filter_queryset(self.get_queryset())
        
        if format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="export.csv"'
            
            writer = csv.writer(response)
            fields = self.export_fields or [f.name for f in queryset.model._meta.fields]
            writer.writerow(fields)
            
            for obj in queryset:
                row = [getattr(obj, f, '') for f in fields]
                writer.writerow(row)
            
            return response
        
        return Response({'error': 'Unsupported format'}, status=400)


class NestedViewSetMixin:
    """
    Mixin for nested viewsets (e.g., /events/{uuid}/registrations/).
    
    Automatically filters queryset by parent.
    """
    parent_lookup_field = 'event_uuid'  # URL kwarg
    parent_model_field = 'event__uuid'  # Model field path
    
    def get_queryset(self):
        qs = super().get_queryset()
        parent_uuid = self.kwargs.get(self.parent_lookup_field)
        if parent_uuid:
            qs = qs.filter(**{self.parent_model_field: parent_uuid})
        return qs
```

---

## Accounts API

### Serializers

```python
# accounts/serializers.py

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from common.serializers import BaseModelSerializer, SoftDeleteModelSerializer

User = get_user_model()


# =============================================================================
# Authentication Serializers
# =============================================================================

class SignupSerializer(serializers.ModelSerializer):
    """
    User registration serializer.
    
    Creates attendee account by default.
    """
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 
            'full_name', 'professional_title', 'credentials', 'organization_name'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Passwords don't match."
            })
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.set_password(password)
        user.account_type = 'attendee'
        user.save()
        
        # Send verification email
        user.send_verification_email()
        
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user data.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user info to response
        data['user'] = {
            'uuid': str(self.user.uuid),
            'email': self.user.email,
            'full_name': self.user.full_name,
            'account_type': self.user.account_type,
            'email_verified': self.user.email_verified,
        }
        
        return data


class PasswordChangeSerializer(serializers.Serializer):
    """Change password for authenticated user."""
    current_password = serializers.CharField(
        required=True, 
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True, 
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True, 
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Passwords don't match."
            })
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Request password reset email."""
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirm password reset with token."""
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, 
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(
        required=True, 
        write_only=True
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Passwords don't match."
            })
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Verify email with token."""
    token = serializers.CharField(required=True)


class ResendVerificationSerializer(serializers.Serializer):
    """Resend verification email."""
    email = serializers.EmailField(required=True)


# =============================================================================
# User Serializers
# =============================================================================

class UserSerializer(SoftDeleteModelSerializer):
    """
    Full user serializer for profile management.
    """
    class Meta:
        model = User
        fields = [
            'uuid', 'email', 'full_name', 'professional_title', 
            'credentials', 'organization_name', 'bio', 'profile_photo_url',
            'account_type', 'email_verified', 'timezone',
            # Organizer-specific
            'organizer_display_name', 'organizer_logo_url', 
            'organizer_website', 'organizer_bio',
            'organizer_social_linkedin', 'organizer_social_twitter',
            'is_organizer_profile_public',
            # Notification preferences
            'notify_event_reminders', 'notify_certificate_issued',
            'notify_marketing', 'notify_new_registration', 'notify_event_summary',
            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'uuid', 'email', 'account_type', 'email_verified',
            'created_at', 'updated_at',
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    
    Separate from full UserSerializer for security.
    """
    class Meta:
        model = User
        fields = [
            'full_name', 'professional_title', 'credentials',
            'organization_name', 'bio', 'profile_photo_url', 'timezone',
        ]


class OrganizerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating organizer-specific profile fields.
    """
    class Meta:
        model = User
        fields = [
            'organizer_display_name', 'organizer_logo_url',
            'organizer_website', 'organizer_bio',
            'organizer_social_linkedin', 'organizer_social_twitter',
            'is_organizer_profile_public',
        ]


class NotificationPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences only."""
    class Meta:
        model = User
        fields = [
            'notify_event_reminders', 'notify_certificate_issued',
            'notify_marketing', 'notify_new_registration', 'notify_event_summary',
        ]


class PublicOrganizerSerializer(serializers.ModelSerializer):
    """
    Public-facing organizer profile.
    
    Used for organizer public profile pages.
    """
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'uuid', 'display_name', 'organizer_logo_url',
            'organizer_website', 'organizer_bio',
            'organizer_social_linkedin', 'organizer_social_twitter',
        ]
    
    def get_display_name(self, obj):
        return obj.organizer_display_name or obj.full_name


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user data for embedding in other responses."""
    class Meta:
        model = User
        fields = ['uuid', 'full_name', 'email']


# =============================================================================
# Zoom Connection Serializers
# =============================================================================

class ZoomConnectionSerializer(BaseModelSerializer):
    """Zoom connection status (safe fields only)."""
    class Meta:
        model = 'accounts.ZoomConnection'  # Use string reference
        fields = [
            'uuid', 'zoom_email', 'is_active', 'is_healthy',
            'connected_at', 'last_refresh_at', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class ZoomConnectionStatusSerializer(serializers.Serializer):
    """Simple status check for Zoom connection."""
    connected = serializers.BooleanField()
    zoom_email = serializers.EmailField(allow_null=True)
    is_healthy = serializers.BooleanField()
    needs_reconnect = serializers.BooleanField()


# =============================================================================
# Session Serializers
# =============================================================================

class UserSessionSerializer(serializers.ModelSerializer):
    """Active session information."""
    display_device = serializers.CharField(read_only=True)
    display_location = serializers.CharField(read_only=True)
    
    class Meta:
        model = 'accounts.UserSession'
        fields = [
            'uuid', 'device_type', 'browser', 'os',
            'display_device', 'display_location',
            'ip_address', 'is_current', 'last_activity_at', 'created_at',
        ]
        read_only_fields = fields


# =============================================================================
# CPD Requirement Serializers
# =============================================================================

class CPDRequirementSerializer(BaseModelSerializer):
    """CPD/CE requirement tracking."""
    completion_percent = serializers.IntegerField(read_only=True)
    credits_remaining = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )
    earned_credits = serializers.SerializerMethodField()
    period_bounds = serializers.SerializerMethodField()
    
    class Meta:
        model = 'accounts.CPDRequirement'
        fields = [
            'uuid', 'cpd_type', 'cpd_type_display', 'annual_requirement',
            'period_type', 'fiscal_year_start_month', 'fiscal_year_start_day',
            'licensing_body', 'license_number', 'notes', 'is_active',
            # Computed
            'completion_percent', 'credits_remaining', 'earned_credits',
            'period_bounds',
            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']
    
    def get_earned_credits(self, obj):
        return str(obj.get_earned_credits())
    
    def get_period_bounds(self, obj):
        start, end = obj.get_current_period_bounds()
        return {
            'start': start.isoformat(),
            'end': end.isoformat(),
        }


class CPDRequirementCreateSerializer(serializers.ModelSerializer):
    """Create/update CPD requirement."""
    class Meta:
        model = 'accounts.CPDRequirement'
        fields = [
            'cpd_type', 'cpd_type_display', 'annual_requirement',
            'period_type', 'fiscal_year_start_month', 'fiscal_year_start_day',
            'licensing_body', 'license_number', 'notes', 'is_active',
        ]
    
    def validate(self, attrs):
        # Validate fiscal year settings
        if attrs.get('period_type') == 'fiscal_year':
            if not attrs.get('fiscal_year_start_month'):
                raise serializers.ValidationError({
                    'fiscal_year_start_month': 'Required for fiscal year period.'
                })
        return attrs
```

### ViewSets

```python
# accounts/views.py

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import get_user_model
from common.viewsets import BaseModelViewSet
from common.permissions import IsOrganizer
from . import serializers

User = get_user_model()


# =============================================================================
# Authentication Views
# =============================================================================

class AuthThrottle(AnonRateThrottle):
    """Stricter throttle for auth endpoints."""
    rate = '20/hour'


class SignupView(generics.CreateAPIView):
    """
    POST /api/v1/auth/signup/
    
    Create new user account.
    """
    serializer_class = serializers.SignupSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'message': 'Account created. Please check your email to verify.',
            'user': {
                'uuid': str(user.uuid),
                'email': user.email,
                'full_name': user.full_name,
            }
        }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/v1/auth/token/
    
    Obtain JWT token pair.
    """
    serializer_class = serializers.CustomTokenObtainPairSerializer
    throttle_classes = [AuthThrottle]


class EmailVerificationView(generics.GenericAPIView):
    """
    POST /api/v1/auth/verify-email/
    
    Verify email address with token.
    """
    serializer_class = serializers.EmailVerificationSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            user = User.objects.get(
                email_verification_token=token,
                email_verified=False
            )
        except User.DoesNotExist:
            return Response(
                {'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired token.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check expiration
        from django.utils import timezone
        if user.email_verification_token_expires_at < timezone.now():
            return Response(
                {'error': {'code': 'TOKEN_EXPIRED', 'message': 'Token has expired.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.email_verified = True
        user.email_verification_token = ''
        user.save()
        
        return Response({'message': 'Email verified successfully.'})


class ResendVerificationView(generics.GenericAPIView):
    """
    POST /api/v1/auth/resend-verification/
    
    Resend email verification.
    """
    serializer_class = serializers.ResendVerificationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email, email_verified=False)
            user.send_verification_email()
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        
        return Response({
            'message': 'If an unverified account exists, a verification email has been sent.'
        })


class PasswordResetRequestView(generics.GenericAPIView):
    """
    POST /api/v1/auth/password-reset/
    
    Request password reset email.
    """
    serializer_class = serializers.PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            user.send_password_reset_email()
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        
        return Response({
            'message': 'If an account exists, a password reset email has been sent.'
        })


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    POST /api/v1/auth/password-reset/confirm/
    
    Confirm password reset with token.
    """
    serializer_class = serializers.PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        password = serializer.validated_data['new_password']
        
        try:
            user = User.objects.get(password_reset_token=token)
        except User.DoesNotExist:
            return Response(
                {'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired token.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check expiration
        from django.utils import timezone
        if user.password_reset_token_expires_at < timezone.now():
            return Response(
                {'error': {'code': 'TOKEN_EXPIRED', 'message': 'Token has expired.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(password)
        user.password_reset_token = ''
        user.save()
        
        return Response({'message': 'Password reset successfully.'})


class PasswordChangeView(generics.GenericAPIView):
    """
    POST /api/v1/auth/password-change/
    
    Change password for authenticated user.
    """
    serializer_class = serializers.PasswordChangeSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully.'})


# =============================================================================
# User Profile Views
# =============================================================================

class CurrentUserView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/users/me/
    PATCH /api/v1/users/me/
    
    Current user profile.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return serializers.UserProfileUpdateSerializer
        return serializers.UserSerializer
    
    def get_object(self):
        return self.request.user


class OrganizerProfileView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/users/me/organizer-profile/
    PATCH /api/v1/users/me/organizer-profile/
    
    Organizer-specific profile fields.
    """
    serializer_class = serializers.OrganizerProfileUpdateSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]
    
    def get_object(self):
        return self.request.user


class NotificationPreferencesView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/users/me/notifications/
    PATCH /api/v1/users/me/notifications/
    
    Notification preferences.
    """
    serializer_class = serializers.NotificationPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class PublicOrganizerView(generics.RetrieveAPIView):
    """
    GET /api/v1/organizers/{uuid}/
    
    Public organizer profile.
    """
    serializer_class = serializers.PublicOrganizerSerializer
    permission_classes = [AllowAny]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        return User.objects.filter(
            account_type='organizer',
            is_organizer_profile_public=True
        )


class UpgradeToOrganizerView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/upgrade/
    
    Upgrade attendee to organizer account.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.account_type == 'organizer':
            return Response(
                {'error': {'code': 'ALREADY_ORGANIZER', 'message': 'Already an organizer.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.upgrade_to_organizer()
        
        return Response({
            'message': 'Successfully upgraded to organizer.',
            'user': serializers.UserSerializer(user).data
        })


# =============================================================================
# Zoom Connection Views
# =============================================================================

class ZoomConnectionView(generics.RetrieveDestroyAPIView):
    """
    GET /api/v1/users/me/zoom/
    DELETE /api/v1/users/me/zoom/
    
    Zoom connection status and disconnect.
    """
    serializer_class = serializers.ZoomConnectionSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]
    
    def get_object(self):
        return self.request.user.zoom_connection
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = serializers.ZoomConnectionStatusSerializer({
                'connected': True,
                'zoom_email': instance.zoom_email,
                'is_healthy': instance.is_healthy,
                'needs_reconnect': instance.needs_refresh or not instance.is_active,
            })
        except:
            serializer = serializers.ZoomConnectionStatusSerializer({
                'connected': False,
                'zoom_email': None,
                'is_healthy': False,
                'needs_reconnect': True,
            })
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
        except:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class ZoomOAuthInitView(generics.GenericAPIView):
    """
    GET /api/v1/users/me/zoom/connect/
    
    Initiate Zoom OAuth flow.
    Returns OAuth authorization URL.
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    
    def get(self, request):
        from django.conf import settings
        import urllib.parse
        
        state = request.user.generate_oauth_state()
        
        params = {
            'response_type': 'code',
            'client_id': settings.ZOOM_CLIENT_ID,
            'redirect_uri': settings.ZOOM_REDIRECT_URI,
            'state': state,
        }
        
        url = f"https://zoom.us/oauth/authorize?{urllib.parse.urlencode(params)}"
        
        return Response({'authorization_url': url})


class ZoomOAuthCallbackView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/zoom/callback/
    
    Handle Zoom OAuth callback.
    Exchange code for tokens.
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    
    def post(self, request):
        code = request.data.get('code')
        state = request.data.get('state')
        
        if not code or not state:
            return Response(
                {'error': {'code': 'MISSING_PARAMS', 'message': 'Code and state required.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate state
        if not request.user.validate_oauth_state(state):
            return Response(
                {'error': {'code': 'INVALID_STATE', 'message': 'Invalid OAuth state.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Exchange code for tokens (implementation in services)
        from accounts.services import zoom_service
        try:
            zoom_service.complete_oauth(request.user, code)
        except Exception as e:
            return Response(
                {'error': {'code': 'OAUTH_FAILED', 'message': str(e)}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'message': 'Zoom connected successfully.'})


# =============================================================================
# Session Views
# =============================================================================

class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/users/me/sessions/
    GET /api/v1/users/me/sessions/{uuid}/
    DELETE /api/v1/users/me/sessions/{uuid}/
    
    Manage active sessions.
    """
    serializer_class = serializers.UserSessionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        return self.request.user.sessions.all()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.terminate()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'], url_path='terminate-all')
    def terminate_all(self, request):
        """Terminate all sessions except current."""
        from accounts.models import UserSession
        UserSession.terminate_all_for_user(
            request.user,
            except_session_key=request.session.session_key
        )
        return Response({'message': 'All other sessions terminated.'})


# =============================================================================
# CPD Requirements Views
# =============================================================================

class CPDRequirementViewSet(BaseModelViewSet):
    """
    CRUD for user's CPD requirements.
    
    GET /api/v1/users/me/cpd-requirements/
    POST /api/v1/users/me/cpd-requirements/
    GET /api/v1/users/me/cpd-requirements/{uuid}/
    PATCH /api/v1/users/me/cpd-requirements/{uuid}/
    DELETE /api/v1/users/me/cpd-requirements/{uuid}/
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return serializers.CPDRequirementCreateSerializer
        return serializers.CPDRequirementSerializer
    
    def get_queryset(self):
        return self.request.user.cpd_requirements.all()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

### URL Configuration

```python
# accounts/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'sessions', views.UserSessionViewSet, basename='session')
router.register(r'cpd-requirements', views.CPDRequirementViewSet, basename='cpd-requirement')

urlpatterns = [
    # Authentication
    path('auth/signup/', views.SignupView.as_view(), name='signup'),
    path('auth/token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify-email/', views.EmailVerificationView.as_view(), name='verify_email'),
    path('auth/resend-verification/', views.ResendVerificationView.as_view(), name='resend_verification'),
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/password-change/', views.PasswordChangeView.as_view(), name='password_change'),
    
    # Current user
    path('users/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('users/me/organizer-profile/', views.OrganizerProfileView.as_view(), name='organizer_profile'),
    path('users/me/notifications/', views.NotificationPreferencesView.as_view(), name='notification_preferences'),
    path('users/me/upgrade/', views.UpgradeToOrganizerView.as_view(), name='upgrade_to_organizer'),
    
    # Zoom OAuth
    path('users/me/zoom/', views.ZoomConnectionView.as_view(), name='zoom_connection'),
    path('users/me/zoom/connect/', views.ZoomOAuthInitView.as_view(), name='zoom_connect'),
    path('users/me/zoom/callback/', views.ZoomOAuthCallbackView.as_view(), name='zoom_callback'),
    
    # Sessions and CPD Requirements (router)
    path('users/me/', include(router.urls)),
    
    # Public organizer profile
    path('organizers/<uuid:uuid>/', views.PublicOrganizerView.as_view(), name='public_organizer'),
]
```

---

## Events API

### Serializers

```python
# events/serializers.py

from rest_framework import serializers
from common.serializers import SoftDeleteModelSerializer, BaseModelSerializer
from accounts.serializers import UserMinimalSerializer
from .models import Event, EventCustomField, EventReminder, EventInvitation, EventStatusHistory


# =============================================================================
# Event Serializers
# =============================================================================

class EventCustomFieldSerializer(BaseModelSerializer):
    """Custom registration field definition."""
    class Meta:
        model = EventCustomField
        fields = [
            'uuid', 'label', 'field_type', 'required', 'options',
            'order', 'placeholder', 'help_text', 'show_on_certificate',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class EventListSerializer(SoftDeleteModelSerializer):
    """
    Lightweight event serializer for list views.
    
    Used in:
    - Event list/dashboard
    - Search results
    - Related event lists
    """
    owner = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'uuid', 'title', 'slug', 'status', 'event_type', 'visibility',
            'starts_at', 'duration_minutes', 'timezone',
            'cpd_enabled', 'cpd_credit_type', 'cpd_credit_value',
            'registration_count', 'attendance_count', 'certificate_count',
            'owner', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class EventDetailSerializer(SoftDeleteModelSerializer):
    """
    Full event serializer for detail views.
    
    Includes all fields and nested relationships.
    """
    owner = UserMinimalSerializer(read_only=True)
    custom_fields = EventCustomFieldSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_register = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()
    spots_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            # Identity
            'uuid', 'title', 'slug', 'description', 'event_type', 'visibility',
            # Status
            'status', 'published_at', 'cancelled_at', 'cancellation_reason',
            # Schedule
            'starts_at', 'duration_minutes', 'timezone', 'ends_at',
            'actual_started_at', 'actual_ended_at',
            # Registration
            'registration_enabled', 'registration_deadline', 'capacity',
            'waitlist_enabled', 'registration_count',
            # Zoom
            'zoom_enabled', 'zoom_join_url', 'zoom_meeting_id',
            # CPD
            'cpd_enabled', 'cpd_credit_type', 'cpd_credit_value', 'cpd_accreditation_note',
            # Certificates
            'certificates_enabled', 'auto_issue_certificates',
            'minimum_attendance_percent', 'attendance_count', 'certificate_count',
            # Recording
            'recording_enabled', 'auto_publish_recordings', 'recording_access_level',
            # Learning
            'modules_enabled', 'require_module_completion',
            # Relations
            'owner', 'custom_fields',
            # Computed
            'can_edit', 'can_register', 'is_past', 'spots_remaining',
            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'uuid', 'slug', 'published_at', 'cancelled_at',
            'actual_started_at', 'actual_ended_at',
            'registration_count', 'attendance_count', 'certificate_count',
            'created_at', 'updated_at',
        ]
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.owner == request.user and obj.status in ['draft', 'published']
    
    def get_can_register(self, obj):
        return (
            obj.status == 'published' and
            obj.registration_enabled and
            not obj.is_past and
            (not obj.capacity or obj.registration_count < obj.capacity)
        )
    
    def get_is_past(self, obj):
        return obj.is_past
    
    def get_spots_remaining(self, obj):
        if not obj.capacity:
            return None
        return max(0, obj.capacity - obj.registration_count)


class EventCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating events.
    
    Validates all required fields and business rules.
    """
    custom_fields = EventCustomFieldSerializer(many=True, required=False)
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_type', 'visibility',
            'starts_at', 'duration_minutes', 'timezone',
            'registration_deadline', 'capacity', 'waitlist_enabled',
            'zoom_enabled', 'zoom_settings',
            'cpd_enabled', 'cpd_credit_type', 'cpd_credit_value', 'cpd_accreditation_note',
            'certificates_enabled', 'certificate_template',
            'auto_issue_certificates', 'minimum_attendance_percent',
            'recording_enabled', 'auto_publish_recordings', 'recording_access_level',
            'modules_enabled', 'require_module_completion',
            'custom_fields',
        ]
    
    def validate(self, attrs):
        # Validate CPD fields
        if attrs.get('cpd_enabled'):
            if not attrs.get('cpd_credit_type'):
                raise serializers.ValidationError({
                    'cpd_credit_type': 'Required when CPD is enabled.'
                })
            if not attrs.get('cpd_credit_value'):
                raise serializers.ValidationError({
                    'cpd_credit_value': 'Required when CPD is enabled.'
                })
        
        # Validate waitlist requires capacity
        if attrs.get('waitlist_enabled') and not attrs.get('capacity'):
            raise serializers.ValidationError({
                'waitlist_enabled': 'Waitlist requires capacity to be set.'
            })
        
        # Validate dates
        from django.utils import timezone
        if attrs.get('starts_at') and attrs['starts_at'] < timezone.now():
            raise serializers.ValidationError({
                'starts_at': 'Event start time must be in the future.'
            })
        
        if attrs.get('registration_deadline') and attrs.get('starts_at'):
            if attrs['registration_deadline'] > attrs['starts_at']:
                raise serializers.ValidationError({
                    'registration_deadline': 'Must be before event start time.'
                })
        
        return attrs
    
    def create(self, validated_data):
        custom_fields_data = validated_data.pop('custom_fields', [])
        
        event = Event.objects.create(**validated_data)
        
        for idx, field_data in enumerate(custom_fields_data):
            field_data['order'] = idx
            EventCustomField.objects.create(event=event, **field_data)
        
        return event


class EventUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating events.
    
    Enforces edit restrictions based on event status.
    """
    custom_fields = EventCustomFieldSerializer(many=True, required=False)
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_type', 'visibility',
            'starts_at', 'duration_minutes', 'timezone',
            'registration_deadline', 'capacity', 'waitlist_enabled',
            'cpd_enabled', 'cpd_credit_type', 'cpd_credit_value', 'cpd_accreditation_note',
            'certificates_enabled', 'certificate_template',
            'auto_issue_certificates', 'minimum_attendance_percent',
            'recording_enabled', 'auto_publish_recordings', 'recording_access_level',
            'modules_enabled', 'require_module_completion',
            'custom_fields',
        ]
    
    def validate(self, attrs):
        instance = self.instance
        
        # Enforce edit restrictions based on status
        if instance.status == 'published':
            # Cannot change date/time once published
            restricted_fields = ['starts_at', 'duration_minutes', 'timezone']
            for field in restricted_fields:
                if field in attrs and attrs[field] != getattr(instance, field):
                    raise serializers.ValidationError({
                        field: f'Cannot change {field} after event is published.'
                    })
        
        if instance.status not in ['draft', 'published']:
            raise serializers.ValidationError(
                'Cannot edit event in current status.'
            )
        
        return attrs
    
    def update(self, instance, validated_data):
        custom_fields_data = validated_data.pop('custom_fields', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update custom fields if provided
        if custom_fields_data is not None:
            instance.custom_fields.all().delete()
            for idx, field_data in enumerate(custom_fields_data):
                field_data['order'] = idx
                EventCustomField.objects.create(event=instance, **field_data)
        
        return instance


class PublicEventSerializer(serializers.ModelSerializer):
    """
    Public-facing event serializer.
    
    Used for event discovery and public event pages.
    Does not expose sensitive organizer data.
    """
    organizer_name = serializers.SerializerMethodField()
    organizer_uuid = serializers.SerializerMethodField()
    can_register = serializers.SerializerMethodField()
    spots_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'uuid', 'title', 'slug', 'description', 'event_type',
            'starts_at', 'duration_minutes', 'timezone', 'ends_at',
            'cpd_enabled', 'cpd_credit_type', 'cpd_credit_value',
            'registration_enabled', 'capacity',
            'organizer_name', 'organizer_uuid',
            'can_register', 'spots_remaining',
        ]
    
    def get_organizer_name(self, obj):
        return obj.owner.organizer_display_name or obj.owner.full_name
    
    def get_organizer_uuid(self, obj):
        if obj.owner.is_organizer_profile_public:
            return str(obj.owner.uuid)
        return None
    
    def get_can_register(self, obj):
        return (
            obj.status == 'published' and
            obj.registration_enabled and
            not obj.is_past
        )
    
    def get_spots_remaining(self, obj):
        if not obj.capacity:
            return None
        remaining = obj.capacity - obj.registration_count
        # Only show if limited spots
        if remaining <= 20:
            return remaining
        return None


# =============================================================================
# Event Reminder Serializers
# =============================================================================

class EventReminderSerializer(BaseModelSerializer):
    """Event reminder configuration."""
    class Meta:
        model = EventReminder
        fields = [
            'uuid', 'reminder_type', 'send_hours_before',
            'scheduled_for', 'sent_at', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'scheduled_for', 'sent_at', 'status', 'created_at', 'updated_at']


class EventReminderCreateSerializer(serializers.ModelSerializer):
    """Create event reminder."""
    class Meta:
        model = EventReminder
        fields = ['reminder_type', 'send_hours_before']


# =============================================================================
# Event Invitation Serializers  
# =============================================================================

class EventInvitationSerializer(BaseModelSerializer):
    """Event invitation tracking."""
    class Meta:
        model = EventInvitation
        fields = [
            'uuid', 'email', 'status', 'sent_at', 'opened_at',
            'responded_at', 'response',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class EventInvitationCreateSerializer(serializers.Serializer):
    """Create invitations (single or bulk)."""
    emails = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=500
    )
    send_immediately = serializers.BooleanField(default=True)


# =============================================================================
# Event Status History
# =============================================================================

class EventStatusHistorySerializer(BaseModelSerializer):
    """Event status change audit log."""
    changed_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = EventStatusHistory
        fields = [
            'uuid', 'from_status', 'to_status',
            'changed_by', 'reason', 'created_at',
        ]
        read_only_fields = fields
```

### ViewSets

```python
# events/views.py

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters import rest_framework as filters
from common.viewsets import SoftDeleteModelViewSet, ReadOnlyModelViewSet
from common.permissions import IsOrganizer, IsOwner, IsOwnerOrReadOnly, HasActiveSubscription
from common.mixins import ExportMixin
from . import serializers
from .models import Event, EventReminder, EventInvitation


# =============================================================================
# Event Filters
# =============================================================================

class EventFilter(filters.FilterSet):
    """Filter events by various criteria."""
    status = filters.ChoiceFilter(choices=Event.Status.choices)
    event_type = filters.ChoiceFilter(choices=Event.EventType.choices)
    visibility = filters.ChoiceFilter(choices=Event.Visibility.choices)
    starts_after = filters.DateTimeFilter(field_name='starts_at', lookup_expr='gte')
    starts_before = filters.DateTimeFilter(field_name='starts_at', lookup_expr='lte')
    cpd_type = filters.CharFilter(field_name='cpd_credit_type')
    has_capacity = filters.BooleanFilter(method='filter_has_capacity')
    
    class Meta:
        model = Event
        fields = ['status', 'event_type', 'visibility', 'cpd_credit_type']
    
    def filter_has_capacity(self, queryset, name, value):
        if value:
            return queryset.filter(capacity__isnull=False)
        return queryset.filter(capacity__isnull=True)


# =============================================================================
# Event ViewSets
# =============================================================================

class EventViewSet(SoftDeleteModelViewSet, ExportMixin):
    """
    Event management for organizers.
    
    GET    /api/v1/events/              List organizer's events
    POST   /api/v1/events/              Create event
    GET    /api/v1/events/{uuid}/       Get event detail
    PATCH  /api/v1/events/{uuid}/       Update event
    DELETE /api/v1/events/{uuid}/       Soft delete event
    
    Actions:
    POST   /api/v1/events/{uuid}/publish/      Publish draft
    POST   /api/v1/events/{uuid}/cancel/       Cancel event
    POST   /api/v1/events/{uuid}/duplicate/    Duplicate event
    GET    /api/v1/events/{uuid}/status-history/   Audit log
    """
    permission_classes = [IsAuthenticated, IsOrganizer, HasActiveSubscription]
    filterset_class = EventFilter
    search_fields = ['title', 'description']
    ordering_fields = ['starts_at', 'created_at', 'title']
    ordering = ['-starts_at']
    export_fields = ['title', 'starts_at', 'status', 'registration_count', 'attendance_count']
    
    def get_queryset(self):
        return Event.objects.filter(owner=self.request.user).select_related('owner')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.EventCreateSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.EventUpdateSerializer
        if self.action == 'list':
            return serializers.EventListSerializer
        return serializers.EventDetailSerializer
    
    def perform_create(self, serializer):
        event = serializer.save(owner=self.request.user)
        
        # Create Zoom meeting if enabled
        if event.zoom_enabled:
            from events.services import zoom_service
            zoom_service.create_meeting_for_event(event)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, uuid=None):
        """Publish a draft event."""
        event = self.get_object()
        
        if event.status != 'draft':
            return Response(
                {'error': {'code': 'INVALID_STATUS', 'message': 'Only draft events can be published.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.publish(user=request.user)
        
        return Response(serializers.EventDetailSerializer(event, context={'request': request}).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        """Cancel an event."""
        event = self.get_object()
        reason = request.data.get('reason', '')
        
        if event.status not in ['published', 'live']:
            return Response(
                {'error': {'code': 'INVALID_STATUS', 'message': 'Cannot cancel event in current status.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.cancel(user=request.user, reason=reason)
        
        # Notify registrants
        from events.tasks import notify_event_cancelled
        notify_event_cancelled.delay(event.id)
        
        return Response(serializers.EventDetailSerializer(event, context={'request': request}).data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, uuid=None):
        """Create a copy of an event."""
        event = self.get_object()
        
        new_title = request.data.get('title')
        new_start = request.data.get('starts_at')
        
        if new_start:
            from django.utils.dateparse import parse_datetime
            new_start = parse_datetime(new_start)
        
        new_event = event.duplicate(
            new_title=new_title,
            new_start=new_start,
            user=request.user
        )
        
        return Response(
            serializers.EventDetailSerializer(new_event, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'], url_path='status-history')
    def status_history(self, request, uuid=None):
        """Get event status change history."""
        event = self.get_object()
        history = event.status_history.select_related('changed_by').order_by('-created_at')
        serializer = serializers.EventStatusHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start(self, request, uuid=None):
        """Mark event as live (usually triggered by webhook)."""
        event = self.get_object()
        
        if event.status != 'published':
            return Response(
                {'error': {'code': 'INVALID_STATUS', 'message': 'Only published events can be started.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.start(user=request.user)
        return Response(serializers.EventDetailSerializer(event, context={'request': request}).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, uuid=None):
        """Mark event as completed."""
        event = self.get_object()
        
        if event.status != 'live':
            return Response(
                {'error': {'code': 'INVALID_STATUS', 'message': 'Only live events can be completed.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.complete(user=request.user)
        return Response(serializers.EventDetailSerializer(event, context={'request': request}).data)


class PublicEventViewSet(ReadOnlyModelViewSet):
    """
    Public event discovery.
    
    GET /api/v1/public/events/           Browse public events
    GET /api/v1/public/events/{uuid}/    Get public event detail
    GET /api/v1/public/events/{slug}/    Get by slug
    """
    serializer_class = serializers.PublicEventSerializer
    permission_classes = [AllowAny]
    filterset_class = EventFilter
    search_fields = ['title', 'description']
    ordering_fields = ['starts_at']
    ordering = ['starts_at']
    lookup_field = 'uuid'
    
    def get_queryset(self):
        from django.utils import timezone
        return Event.objects.filter(
            visibility='public',
            status='published',
            starts_at__gte=timezone.now()
        ).select_related('owner')
    
    @action(detail=False, methods=['get'], url_path='by-slug/(?P<slug>[-\\w]+)')
    def by_slug(self, request, slug=None):
        """Get event by slug."""
        event = self.get_queryset().filter(slug=slug).first()
        if not event:
            return Response(
                {'error': {'code': 'NOT_FOUND', 'message': 'Event not found.'}},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(event)
        return Response(serializer.data)


# =============================================================================
# Nested Event Resources
# =============================================================================

class EventReminderViewSet(viewsets.ModelViewSet):
    """
    Manage reminders for an event.
    
    GET    /api/v1/events/{event_uuid}/reminders/
    POST   /api/v1/events/{event_uuid}/reminders/
    DELETE /api/v1/events/{event_uuid}/reminders/{uuid}/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return EventReminder.objects.filter(
            event__uuid=event_uuid,
            event__owner=self.request.user
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.EventReminderCreateSerializer
        return serializers.EventReminderSerializer
    
    def perform_create(self, serializer):
        event_uuid = self.kwargs.get('event_uuid')
        event = Event.objects.get(uuid=event_uuid, owner=self.request.user)
        reminder = serializer.save(event=event)
        reminder.schedule()


class EventInvitationViewSet(viewsets.ModelViewSet):
    """
    Manage invitations for an event.
    
    GET    /api/v1/events/{event_uuid}/invitations/
    POST   /api/v1/events/{event_uuid}/invitations/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return EventInvitation.objects.filter(
            event__uuid=event_uuid,
            event__owner=self.request.user
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.EventInvitationCreateSerializer
        return serializers.EventInvitationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        event_uuid = self.kwargs.get('event_uuid')
        event = Event.objects.get(uuid=event_uuid, owner=request.user)
        
        emails = serializer.validated_data['emails']
        send_immediately = serializer.validated_data['send_immediately']
        
        invitations = []
        for email in emails:
            inv, created = EventInvitation.objects.get_or_create(
                event=event,
                email=email.lower(),
                defaults={'status': 'pending'}
            )
            if created:
                invitations.append(inv)
        
        if send_immediately and invitations:
            from events.tasks import send_invitations
            send_invitations.delay([i.id for i in invitations])
        
        return Response({
            'created': len(invitations),
            'skipped': len(emails) - len(invitations),
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='send-all')
    def send_all(self, request, event_uuid=None):
        """Send all pending invitations."""
        pending = self.get_queryset().filter(status='pending')
        
        from events.tasks import send_invitations
        send_invitations.delay([i.id for i in pending])
        
        return Response({'queued': pending.count()})
```

### URL Configuration

```python
# events/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers
from . import views

# Main router
router = DefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'public/events', views.PublicEventViewSet, basename='public-event')

# Nested routers for event sub-resources
events_router = nested_routers.NestedDefaultRouter(router, r'events', lookup='event')
events_router.register(r'reminders', views.EventReminderViewSet, basename='event-reminders')
events_router.register(r'invitations', views.EventInvitationViewSet, basename='event-invitations')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(events_router.urls)),
]
```

---

*[Document continues with Registrations, Certificates, Contacts, Billing, Learning, and Recordings APIs...]*
