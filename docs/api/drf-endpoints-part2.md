# Django REST Framework API Layer Specification - Part 2

## Registrations API

### Serializers

```python
# registrations/serializers.py

from rest_framework import serializers
from common.serializers import SoftDeleteModelSerializer, BaseModelSerializer
from accounts.serializers import UserMinimalSerializer
from events.serializers import EventListSerializer
from .models import Registration, AttendanceRecord


# =============================================================================
# Registration Serializers
# =============================================================================

class CustomFieldResponseSerializer(serializers.Serializer):
    """Custom field response data."""
    field_uuid = serializers.UUIDField()
    field_label = serializers.CharField()
    value = serializers.JSONField()


class RegistrationListSerializer(SoftDeleteModelSerializer):
    """Lightweight registration for list views."""
    user = UserMinimalSerializer(read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    
    class Meta:
        model = Registration
        fields = [
            'uuid', 'user', 'event_title', 'status',
            'attended', 'certificate_issued', 'waitlist_position',
            'registered_at', 'created_at',
        ]
        read_only_fields = fields


class RegistrationDetailSerializer(SoftDeleteModelSerializer):
    """Full registration detail."""
    user = UserMinimalSerializer(read_only=True)
    event = EventListSerializer(read_only=True)
    custom_field_responses = CustomFieldResponseSerializer(many=True, read_only=True)
    attendance_records = serializers.SerializerMethodField()
    
    class Meta:
        model = Registration
        fields = [
            'uuid', 'user', 'event', 'status',
            # Registration info
            'guest_email', 'guest_name', 'registered_at',
            'registration_source', 'discount_code_used',
            # Attendance
            'attended', 'attendance_percent', 'join_time', 'leave_time',
            'total_duration_minutes', 'attendance_records',
            # Certificate
            'certificate_issued', 'certificate_eligible',
            # Privacy
            'allow_public_verification',
            # Custom fields
            'custom_field_responses',
            # Waitlist
            'waitlist_position', 'waitlisted_at', 'promoted_at',
            # Cancellation
            'cancelled_at', 'cancellation_reason',
            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
    
    def get_attendance_records(self, obj):
        records = obj.attendance_records.order_by('joined_at')
        return AttendanceRecordSerializer(records, many=True).data


class RegistrationCreateSerializer(serializers.Serializer):
    """
    Register for an event.
    
    For authenticated users: no email required
    For guests: email required
    """
    email = serializers.EmailField(required=False)
    name = serializers.CharField(required=False, max_length=255)
    custom_field_responses = serializers.DictField(required=False)
    allow_public_verification = serializers.BooleanField(default=True)
    discount_code = serializers.CharField(required=False, max_length=50)
    
    def validate(self, attrs):
        request = self.context.get('request')
        
        # Guest registration requires email
        if not request.user.is_authenticated:
            if not attrs.get('email'):
                raise serializers.ValidationError({
                    'email': 'Email required for guest registration.'
                })
        
        return attrs


class RegistrationBulkCreateSerializer(serializers.Serializer):
    """Bulk add registrations (organizer use)."""
    registrations = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=500
    )
    send_confirmation = serializers.BooleanField(default=True)
    
    def validate_registrations(self, value):
        for reg in value:
            if 'email' not in reg:
                raise serializers.ValidationError('Each registration requires an email.')
        return value


class WaitlistPositionSerializer(serializers.Serializer):
    """Waitlist position info for attendee."""
    position = serializers.IntegerField()
    total_waitlisted = serializers.IntegerField()
    estimated_chance = serializers.CharField()


# =============================================================================
# Attendance Serializers
# =============================================================================

class AttendanceRecordSerializer(BaseModelSerializer):
    """Individual join/leave record from Zoom."""
    class Meta:
        model = AttendanceRecord
        fields = [
            'uuid', 'joined_at', 'left_at', 'duration_minutes',
            'join_source', 'device_type', 'created_at',
        ]
        read_only_fields = fields


class AttendanceUpdateSerializer(serializers.Serializer):
    """Manual attendance update by organizer."""
    attended = serializers.BooleanField()
    attendance_percent = serializers.IntegerField(
        required=False, min_value=0, max_value=100
    )
    notes = serializers.CharField(required=False, max_length=500)


class AttendanceBulkUpdateSerializer(serializers.Serializer):
    """Bulk update attendance."""
    updates = serializers.ListField(
        child=serializers.DictField()
    )
    
    def validate_updates(self, value):
        for update in value:
            if 'registration_uuid' not in update:
                raise serializers.ValidationError('Each update requires registration_uuid.')
            if 'attended' not in update:
                raise serializers.ValidationError('Each update requires attended field.')
        return value


# =============================================================================
# Attendee-facing Serializers
# =============================================================================

class MyRegistrationSerializer(SoftDeleteModelSerializer):
    """Registration from attendee's perspective."""
    event = EventListSerializer(read_only=True)
    zoom_join_url = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()
    certificate_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Registration
        fields = [
            'uuid', 'event', 'status', 'registered_at',
            'attended', 'attendance_percent',
            'certificate_issued', 'certificate_eligible',
            'allow_public_verification',
            'waitlist_position',
            'zoom_join_url', 'can_join', 'certificate_url',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_zoom_join_url(self, obj):
        if obj.status == 'confirmed' and obj.event.status in ['published', 'live']:
            return obj.event.zoom_join_url
        return None
    
    def get_can_join(self, obj):
        return (
            obj.status == 'confirmed' and
            obj.event.status in ['published', 'live']
        )
    
    def get_certificate_url(self, obj):
        if obj.certificate_issued:
            cert = obj.certificates.first()
            if cert:
                return f"/api/v1/certificates/{cert.uuid}/"
        return None
```

### ViewSets

```python
# registrations/views.py

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters import rest_framework as filters
from common.viewsets import SoftDeleteModelViewSet
from common.permissions import IsOrganizer, IsEventOwner, IsRegistrant
from common.mixins import ExportMixin, BulkUpdateMixin
from . import serializers
from .models import Registration


class RegistrationFilter(filters.FilterSet):
    """Filter registrations."""
    status = filters.ChoiceFilter(choices=Registration.Status.choices)
    attended = filters.BooleanFilter()
    certificate_issued = filters.BooleanFilter()
    registered_after = filters.DateTimeFilter(field_name='registered_at', lookup_expr='gte')
    registered_before = filters.DateTimeFilter(field_name='registered_at', lookup_expr='lte')
    
    class Meta:
        model = Registration
        fields = ['status', 'attended', 'certificate_issued']


class EventRegistrationViewSet(SoftDeleteModelViewSet, ExportMixin, BulkUpdateMixin):
    """
    Manage registrations for an event (organizer view).
    
    GET    /api/v1/events/{event_uuid}/registrations/
    POST   /api/v1/events/{event_uuid}/registrations/          Bulk add
    GET    /api/v1/events/{event_uuid}/registrations/{uuid}/
    PATCH  /api/v1/events/{event_uuid}/registrations/{uuid}/   Update attendance
    DELETE /api/v1/events/{event_uuid}/registrations/{uuid}/   Cancel registration
    
    Actions:
    GET    /api/v1/events/{event_uuid}/registrations/waitlist/
    POST   /api/v1/events/{event_uuid}/registrations/{uuid}/promote/
    POST   /api/v1/events/{event_uuid}/registrations/promote-next/
    PATCH  /api/v1/events/{event_uuid}/registrations/bulk-attendance/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    filterset_class = RegistrationFilter
    search_fields = ['user__email', 'user__full_name', 'guest_email', 'guest_name']
    ordering_fields = ['registered_at', 'status', 'attended']
    ordering = ['-registered_at']
    export_fields = ['user__email', 'user__full_name', 'status', 'attended', 'registered_at']
    
    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return Registration.objects.filter(
            event__uuid=event_uuid,
            event__owner=self.request.user
        ).select_related('user', 'event')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.RegistrationBulkCreateSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.AttendanceUpdateSerializer
        if self.action == 'list':
            return serializers.RegistrationListSerializer
        return serializers.RegistrationDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Bulk add registrations."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        event_uuid = self.kwargs.get('event_uuid')
        from events.models import Event
        event = Event.objects.get(uuid=event_uuid, owner=request.user)
        
        created = []
        skipped = []
        
        for reg_data in serializer.validated_data['registrations']:
            email = reg_data['email'].lower()
            name = reg_data.get('name', '')
            
            # Check if already registered
            existing = Registration.objects.filter(
                event=event,
                guest_email=email
            ).first() or Registration.objects.filter(
                event=event,
                user__email=email
            ).first()
            
            if existing:
                skipped.append(email)
                continue
            
            # Find user or create guest registration
            from accounts.models import User
            user = User.objects.filter(email=email).first()
            
            reg = Registration.objects.create(
                event=event,
                user=user,
                guest_email=email if not user else '',
                guest_name=name if not user else '',
                status='confirmed',
                registration_source='organizer_added',
            )
            created.append(reg)
        
        # Send confirmations
        if serializer.validated_data['send_confirmation'] and created:
            from registrations.tasks import send_registration_confirmations
            send_registration_confirmations.delay([r.id for r in created])
        
        return Response({
            'created': len(created),
            'skipped': len(skipped),
            'skipped_emails': skipped,
        }, status=status.HTTP_201_CREATED)
    
    def partial_update(self, request, *args, **kwargs):
        """Update attendance for single registration."""
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        instance.attended = serializer.validated_data['attended']
        if 'attendance_percent' in serializer.validated_data:
            instance.attendance_percent = serializer.validated_data['attendance_percent']
        instance.save()
        
        return Response(serializers.RegistrationDetailSerializer(instance).data)
    
    @action(detail=False, methods=['get'])
    def waitlist(self, request, event_uuid=None):
        """Get waitlist registrations."""
        waitlisted = self.get_queryset().filter(
            status='waitlisted'
        ).order_by('waitlist_position')
        
        serializer = serializers.RegistrationListSerializer(waitlisted, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def promote(self, request, event_uuid=None, uuid=None):
        """Promote a waitlisted registration to confirmed."""
        registration = self.get_object()
        
        if registration.status != 'waitlisted':
            return Response(
                {'error': {'code': 'NOT_WAITLISTED', 'message': 'Registration is not waitlisted.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registration.promote_from_waitlist()
        
        return Response(serializers.RegistrationDetailSerializer(registration).data)
    
    @action(detail=False, methods=['post'], url_path='promote-next')
    def promote_next(self, request, event_uuid=None):
        """Promote next person in waitlist."""
        next_in_line = self.get_queryset().filter(
            status='waitlisted'
        ).order_by('waitlist_position').first()
        
        if not next_in_line:
            return Response(
                {'error': {'code': 'EMPTY_WAITLIST', 'message': 'No one on waitlist.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        next_in_line.promote_from_waitlist()
        
        return Response(serializers.RegistrationDetailSerializer(next_in_line).data)
    
    @action(detail=False, methods=['patch'], url_path='bulk-attendance')
    def bulk_attendance(self, request, event_uuid=None):
        """Bulk update attendance."""
        serializer = serializers.AttendanceBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated = []
        for update in serializer.validated_data['updates']:
            try:
                reg = self.get_queryset().get(uuid=update['registration_uuid'])
                reg.attended = update['attended']
                if 'attendance_percent' in update:
                    reg.attendance_percent = update['attendance_percent']
                reg.save()
                updated.append(str(reg.uuid))
            except Registration.DoesNotExist:
                pass
        
        return Response({'updated': len(updated), 'uuids': updated})
    
    @action(detail=False, methods=['get'])
    def summary(self, request, event_uuid=None):
        """Get registration summary stats."""
        qs = self.get_queryset()
        
        return Response({
            'total': qs.count(),
            'confirmed': qs.filter(status='confirmed').count(),
            'waitlisted': qs.filter(status='waitlisted').count(),
            'cancelled': qs.filter(status='cancelled').count(),
            'attended': qs.filter(attended=True).count(),
            'certificate_issued': qs.filter(certificate_issued=True).count(),
        })


class PublicRegistrationView(generics.CreateAPIView):
    """
    POST /api/v1/public/events/{event_uuid}/register/
    
    Public registration endpoint (authenticated or guest).
    """
    serializer_class = serializers.RegistrationCreateSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, event_uuid=None):
        from events.models import Event
        
        try:
            event = Event.objects.get(
                uuid=event_uuid,
                status='published',
                registration_enabled=True
            )
        except Event.DoesNotExist:
            return Response(
                {'error': {'code': 'NOT_FOUND', 'message': 'Event not found or registration closed.'}},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user if request.user.is_authenticated else None
        email = serializer.validated_data.get('email', '').lower()
        
        # Check for existing registration
        if user:
            existing = Registration.objects.filter(event=event, user=user).first()
        else:
            existing = Registration.objects.filter(event=event, guest_email=email).first()
        
        if existing:
            return Response(
                {'error': {'code': 'ALREADY_REGISTERED', 'message': 'Already registered for this event.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check capacity
        if event.capacity:
            confirmed_count = event.registrations.filter(status='confirmed').count()
            if confirmed_count >= event.capacity:
                if event.waitlist_enabled:
                    # Add to waitlist
                    return self._add_to_waitlist(event, user, serializer.validated_data)
                else:
                    return Response(
                        {'error': {'code': 'EVENT_FULL', 'message': 'Event is at capacity.'}},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        # Create registration
        registration = Registration.objects.create(
            event=event,
            user=user,
            guest_email=email if not user else '',
            guest_name=serializer.validated_data.get('name', '') if not user else '',
            status='confirmed',
            allow_public_verification=serializer.validated_data.get('allow_public_verification', True),
            registration_source='self_registered',
        )
        
        # Save custom field responses
        custom_responses = serializer.validated_data.get('custom_field_responses', {})
        registration.save_custom_field_responses(custom_responses)
        
        # Send confirmation
        from registrations.tasks import send_registration_confirmation
        send_registration_confirmation.delay(registration.id)
        
        return Response({
            'registration_uuid': str(registration.uuid),
            'status': registration.status,
            'message': 'Successfully registered!',
        }, status=status.HTTP_201_CREATED)
    
    def _add_to_waitlist(self, event, user, data):
        """Add to waitlist when event is full."""
        from django.db.models import Max
        
        max_position = Registration.objects.filter(
            event=event, status='waitlisted'
        ).aggregate(Max('waitlist_position'))['waitlist_position__max'] or 0
        
        registration = Registration.objects.create(
            event=event,
            user=user,
            guest_email=data.get('email', '').lower() if not user else '',
            guest_name=data.get('name', '') if not user else '',
            status='waitlisted',
            waitlist_position=max_position + 1,
            allow_public_verification=data.get('allow_public_verification', True),
            registration_source='self_registered',
        )
        
        return Response({
            'registration_uuid': str(registration.uuid),
            'status': 'waitlisted',
            'waitlist_position': registration.waitlist_position,
            'message': 'Added to waitlist.',
        }, status=status.HTTP_201_CREATED)


class MyRegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Current user's registrations.
    
    GET /api/v1/users/me/registrations/
    GET /api/v1/users/me/registrations/{uuid}/
    POST /api/v1/users/me/registrations/{uuid}/cancel/
    """
    serializer_class = serializers.MyRegistrationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        return Registration.objects.filter(
            user=self.request.user
        ).select_related('event', 'event__owner')
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        """Cancel a registration."""
        registration = self.get_object()
        
        if registration.status == 'cancelled':
            return Response(
                {'error': {'code': 'ALREADY_CANCELLED', 'message': 'Already cancelled.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if registration.event.status in ['live', 'completed', 'closed']:
            return Response(
                {'error': {'code': 'CANNOT_CANCEL', 'message': 'Cannot cancel after event has started.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registration.cancel(reason='User requested cancellation')
        
        return Response({'message': 'Registration cancelled.'})
```

---

## Certificates API

### Serializers

```python
# certificates/serializers.py

from rest_framework import serializers
from common.serializers import SoftDeleteModelSerializer, BaseModelSerializer
from accounts.serializers import UserMinimalSerializer
from .models import Certificate, CertificateTemplate


# =============================================================================
# Certificate Template Serializers
# =============================================================================

class CertificateTemplateListSerializer(SoftDeleteModelSerializer):
    """Template list view."""
    certificate_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CertificateTemplate
        fields = [
            'uuid', 'name', 'is_default', 'version', 'is_latest_version',
            'preview_url', 'certificate_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
    
    def get_certificate_count(self, obj):
        return obj.certificates.count()


class CertificateTemplateDetailSerializer(SoftDeleteModelSerializer):
    """Full template detail."""
    class Meta:
        model = CertificateTemplate
        fields = [
            'uuid', 'name', 'description', 'is_default',
            'template_file_url', 'preview_url',
            'field_positions', 'default_font', 'default_font_size', 'default_color',
            'version', 'is_latest_version', 'original_template',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'version', 'is_latest_version', 'created_at', 'updated_at']


class CertificateTemplateCreateSerializer(serializers.ModelSerializer):
    """Create new template."""
    template_file = serializers.FileField(write_only=True)
    
    class Meta:
        model = CertificateTemplate
        fields = [
            'name', 'description', 'template_file',
            'field_positions', 'default_font', 'default_font_size', 'default_color',
            'is_default',
        ]
    
    def create(self, validated_data):
        template_file = validated_data.pop('template_file')
        
        # Upload to cloud storage
        from certificates.services import storage_service
        file_url = storage_service.upload_template(template_file)
        validated_data['template_file_url'] = file_url
        
        # Generate preview
        preview_url = storage_service.generate_preview(file_url)
        validated_data['preview_url'] = preview_url
        
        return super().create(validated_data)


class CertificateTemplateUpdateSerializer(serializers.ModelSerializer):
    """Update template (may create new version)."""
    template_file = serializers.FileField(write_only=True, required=False)
    
    class Meta:
        model = CertificateTemplate
        fields = [
            'name', 'description', 'template_file',
            'field_positions', 'default_font', 'default_font_size', 'default_color',
            'is_default',
        ]
    
    def update(self, instance, validated_data):
        template_file = validated_data.pop('template_file', None)
        
        # Check if we need to create new version
        if template_file or 'field_positions' in validated_data:
            if instance.certificates.exists():
                # Create new version
                instance = instance.create_new_version()
        
        if template_file:
            from certificates.services import storage_service
            instance.template_file_url = storage_service.upload_template(template_file)
            instance.preview_url = storage_service.generate_preview(instance.template_file_url)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


# =============================================================================
# Certificate Serializers
# =============================================================================

class CertificateListSerializer(SoftDeleteModelSerializer):
    """Certificate list view."""
    attendee_name = serializers.CharField(source='certificate_data.attendee_name')
    event_title = serializers.CharField(source='certificate_data.event_title')
    
    class Meta:
        model = Certificate
        fields = [
            'uuid', 'certificate_id', 'attendee_name', 'event_title',
            'status', 'cpd_type', 'cpd_credits', 'event_date', 'issued_at',
            'created_at',
        ]
        read_only_fields = fields


class CertificateDetailSerializer(SoftDeleteModelSerializer):
    """Full certificate detail."""
    template = CertificateTemplateListSerializer(read_only=True)
    issued_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = Certificate
        fields = [
            'uuid', 'certificate_id', 'status',
            'certificate_data', 'cpd_type', 'cpd_credits', 'event_date',
            'pdf_url', 'verification_url',
            'issued_at', 'revoked_at', 'revocation_reason',
            'template', 'issued_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class CertificateIssueSerializer(serializers.Serializer):
    """Issue certificates to attendees."""
    registration_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Specific registrations to issue to. If empty, issues to all eligible."
    )
    template_uuid = serializers.UUIDField(required=False)
    send_notification = serializers.BooleanField(default=True)


class CertificateRevokeSerializer(serializers.Serializer):
    """Revoke a certificate."""
    reason = serializers.CharField(required=True, max_length=500)
    notify_attendee = serializers.BooleanField(default=True)


class CertificateVerifySerializer(serializers.Serializer):
    """Public certificate verification response."""
    valid = serializers.BooleanField()
    certificate_id = serializers.CharField()
    attendee_name = serializers.CharField()
    event_title = serializers.CharField()
    event_date = serializers.DateField()
    organizer_name = serializers.CharField()
    cpd_type = serializers.CharField(allow_null=True)
    cpd_credits = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    issued_at = serializers.DateTimeField()
    status = serializers.CharField()


class MyCertificateSerializer(SoftDeleteModelSerializer):
    """Certificate from attendee's perspective."""
    class Meta:
        model = Certificate
        fields = [
            'uuid', 'certificate_id', 'status',
            'certificate_data', 'cpd_type', 'cpd_credits', 'event_date',
            'pdf_url', 'verification_url', 'issued_at',
            'created_at',
        ]
        read_only_fields = fields
```

### ViewSets

```python
# certificates/views.py

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters import rest_framework as filters
from common.viewsets import SoftDeleteModelViewSet
from common.permissions import IsOrganizer, IsEventOwner
from . import serializers
from .models import Certificate, CertificateTemplate


# =============================================================================
# Template ViewSet
# =============================================================================

class CertificateTemplateViewSet(SoftDeleteModelViewSet):
    """
    Manage certificate templates.
    
    GET    /api/v1/templates/
    POST   /api/v1/templates/
    GET    /api/v1/templates/{uuid}/
    PATCH  /api/v1/templates/{uuid}/
    DELETE /api/v1/templates/{uuid}/
    
    Actions:
    POST   /api/v1/templates/{uuid}/set-default/
    GET    /api/v1/templates/{uuid}/versions/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    search_fields = ['name', 'description']
    ordering = ['-is_default', '-created_at']
    
    def get_queryset(self):
        return CertificateTemplate.objects.filter(
            owner=self.request.user,
            is_latest_version=True  # Only show latest versions
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.CertificateTemplateCreateSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.CertificateTemplateUpdateSerializer
        if self.action == 'list':
            return serializers.CertificateTemplateListSerializer
        return serializers.CertificateTemplateDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, uuid=None):
        """Set template as default."""
        template = self.get_object()
        
        # Unset other defaults
        CertificateTemplate.objects.filter(
            owner=request.user, is_default=True
        ).update(is_default=False)
        
        template.is_default = True
        template.save()
        
        return Response({'message': 'Template set as default.'})
    
    @action(detail=True, methods=['get'])
    def versions(self, request, uuid=None):
        """Get all versions of a template."""
        template = self.get_object()
        
        # Get original and all versions
        original = template.original_template or template
        all_versions = CertificateTemplate.objects.filter(
            original_template=original
        ) | CertificateTemplate.objects.filter(pk=original.pk)
        
        serializer = serializers.CertificateTemplateListSerializer(
            all_versions.order_by('-version'), many=True
        )
        return Response(serializer.data)


# =============================================================================
# Event Certificates ViewSet
# =============================================================================

class EventCertificateFilter(filters.FilterSet):
    """Filter certificates for an event."""
    status = filters.ChoiceFilter(choices=Certificate.Status.choices)
    cpd_type = filters.CharFilter()
    issued_after = filters.DateTimeFilter(field_name='issued_at', lookup_expr='gte')
    issued_before = filters.DateTimeFilter(field_name='issued_at', lookup_expr='lte')
    
    class Meta:
        model = Certificate
        fields = ['status', 'cpd_type']


class EventCertificateViewSet(viewsets.ModelViewSet):
    """
    Manage certificates for an event.
    
    GET    /api/v1/events/{event_uuid}/certificates/
    POST   /api/v1/events/{event_uuid}/certificates/issue/
    GET    /api/v1/events/{event_uuid}/certificates/{uuid}/
    POST   /api/v1/events/{event_uuid}/certificates/{uuid}/revoke/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    filterset_class = EventCertificateFilter
    lookup_field = 'uuid'
    
    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return Certificate.objects.filter(
            registration__event__uuid=event_uuid,
            registration__event__owner=self.request.user
        ).select_related('registration', 'template', 'issued_by')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CertificateListSerializer
        return serializers.CertificateDetailSerializer
    
    @action(detail=False, methods=['post'])
    def issue(self, request, event_uuid=None):
        """Issue certificates to eligible attendees."""
        serializer = serializers.CertificateIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from events.models import Event
        event = Event.objects.get(uuid=event_uuid, owner=request.user)
        
        # Get registrations to issue to
        from registrations.models import Registration
        
        registration_uuids = serializer.validated_data.get('registration_uuids')
        if registration_uuids:
            registrations = Registration.objects.filter(
                event=event,
                uuid__in=registration_uuids,
                certificate_issued=False,
                attended=True
            )
        else:
            # All eligible
            registrations = Registration.objects.filter(
                event=event,
                certificate_issued=False,
                certificate_eligible=True
            )
        
        # Get template
        template_uuid = serializer.validated_data.get('template_uuid')
        if template_uuid:
            template = CertificateTemplate.objects.get(
                uuid=template_uuid, owner=request.user
            )
        else:
            template = event.certificate_template
        
        if not template:
            return Response(
                {'error': {'code': 'NO_TEMPLATE', 'message': 'No certificate template specified.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Issue certificates
        from certificates.services import certificate_service
        issued = certificate_service.issue_bulk(
            registrations=registrations,
            template=template,
            issued_by=request.user,
            send_notification=serializer.validated_data['send_notification']
        )
        
        return Response({
            'issued': len(issued),
            'certificate_uuids': [str(c.uuid) for c in issued],
        })
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, event_uuid=None, uuid=None):
        """Revoke a certificate."""
        certificate = self.get_object()
        
        serializer = serializers.CertificateRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        certificate.revoke(
            reason=serializer.validated_data['reason'],
            revoked_by=request.user
        )
        
        if serializer.validated_data['notify_attendee']:
            from certificates.tasks import send_revocation_notification
            send_revocation_notification.delay(certificate.id)
        
        return Response(serializers.CertificateDetailSerializer(certificate).data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request, event_uuid=None):
        """Certificate issuance summary."""
        from registrations.models import Registration
        from events.models import Event
        
        event = Event.objects.get(uuid=event_uuid, owner=request.user)
        
        return Response({
            'total_attended': event.registrations.filter(attended=True).count(),
            'eligible': event.registrations.filter(certificate_eligible=True).count(),
            'issued': event.registrations.filter(certificate_issued=True).count(),
            'pending': event.registrations.filter(
                certificate_eligible=True, certificate_issued=False
            ).count(),
        })


# =============================================================================
# Public Verification
# =============================================================================

class CertificateVerifyView(generics.RetrieveAPIView):
    """
    GET /api/v1/public/certificates/verify/{certificate_id}/
    
    Public certificate verification.
    """
    permission_classes = [AllowAny]
    lookup_field = 'certificate_id'
    
    def get_queryset(self):
        return Certificate.objects.filter(
            registration__allow_public_verification=True
        )
    
    def retrieve(self, request, certificate_id=None):
        try:
            certificate = self.get_queryset().get(certificate_id=certificate_id)
        except Certificate.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Certificate not found or verification not allowed.',
            }, status=status.HTTP_404_NOT_FOUND)
        
        data = certificate.certificate_data
        
        return Response({
            'valid': certificate.status == 'issued',
            'certificate_id': certificate.certificate_id,
            'attendee_name': data.get('attendee_name'),
            'event_title': data.get('event_title'),
            'event_date': certificate.event_date,
            'organizer_name': data.get('organizer_name'),
            'cpd_type': certificate.cpd_type,
            'cpd_credits': certificate.cpd_credits,
            'issued_at': certificate.issued_at,
            'status': certificate.status,
        })


# =============================================================================
# My Certificates (Attendee)
# =============================================================================

class MyCertificateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Current user's certificates.
    
    GET /api/v1/users/me/certificates/
    GET /api/v1/users/me/certificates/{uuid}/
    """
    serializer_class = serializers.MyCertificateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'
    ordering = ['-issued_at']
    
    def get_queryset(self):
        return Certificate.objects.filter(
            registration__user=self.request.user
        ).select_related('registration__event')
    
    @action(detail=True, methods=['get'])
    def download(self, request, uuid=None):
        """Get PDF download URL."""
        certificate = self.get_object()
        
        if not certificate.pdf_url:
            return Response(
                {'error': {'code': 'NO_PDF', 'message': 'PDF not generated.'}},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate signed URL
        from certificates.services import storage_service
        signed_url = storage_service.get_signed_download_url(certificate.pdf_url)
        
        return Response({'download_url': signed_url})
```

---

## Contacts API

### Serializers

```python
# contacts/serializers.py

from rest_framework import serializers
from common.serializers import BaseModelSerializer
from .models import ContactList, Contact


class ContactSerializer(BaseModelSerializer):
    """Individual contact."""
    class Meta:
        model = Contact
        fields = [
            'uuid', 'email', 'full_name', 'professional_title',
            'organization_name', 'phone', 'tags', 'source',
            'events_registered', 'events_attended', 'last_event_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'uuid', 'events_registered', 'events_attended', 
            'last_event_at', 'created_at', 'updated_at'
        ]


class ContactCreateSerializer(serializers.ModelSerializer):
    """Create/update contact."""
    class Meta:
        model = Contact
        fields = [
            'email', 'full_name', 'professional_title',
            'organization_name', 'phone', 'tags',
        ]
    
    def validate_email(self, value):
        return value.lower().strip()


class ContactListSerializer(BaseModelSerializer):
    """Contact list."""
    contact_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ContactList
        fields = [
            'uuid', 'name', 'description', 'contact_count',
            'last_used_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'last_used_at', 'created_at', 'updated_at']


class ContactListDetailSerializer(BaseModelSerializer):
    """Contact list with contacts."""
    contacts = ContactSerializer(many=True, read_only=True)
    
    class Meta:
        model = ContactList
        fields = [
            'uuid', 'name', 'description', 'contacts',
            'last_used_at', 'created_at', 'updated_at',
        ]


class ContactImportSerializer(serializers.Serializer):
    """CSV import for contacts."""
    file = serializers.FileField()
    column_mapping = serializers.DictField(
        child=serializers.CharField(),
        help_text="Map CSV columns to contact fields"
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Tags to apply to all imported contacts"
    )
```

### ViewSets

```python
# contacts/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from common.viewsets import BaseModelViewSet
from common.permissions import IsOrganizer
from common.mixins import ExportMixin
from . import serializers
from .models import ContactList, Contact


class ContactListViewSet(BaseModelViewSet):
    """
    Manage contact lists.
    
    GET    /api/v1/contacts/lists/
    POST   /api/v1/contacts/lists/
    GET    /api/v1/contacts/lists/{uuid}/
    PATCH  /api/v1/contacts/lists/{uuid}/
    DELETE /api/v1/contacts/lists/{uuid}/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return ContactList.objects.filter(owner=self.request.user).annotate_contact_count()
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return serializers.ContactListDetailSerializer
        return serializers.ContactListSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ContactViewSet(BaseModelViewSet, ExportMixin):
    """
    Manage contacts within a list.
    
    GET    /api/v1/contacts/lists/{list_uuid}/contacts/
    POST   /api/v1/contacts/lists/{list_uuid}/contacts/
    GET    /api/v1/contacts/lists/{list_uuid}/contacts/{uuid}/
    PATCH  /api/v1/contacts/lists/{list_uuid}/contacts/{uuid}/
    DELETE /api/v1/contacts/lists/{list_uuid}/contacts/{uuid}/
    
    Actions:
    POST   /api/v1/contacts/lists/{list_uuid}/contacts/import/
    GET    /api/v1/contacts/lists/{list_uuid}/contacts/export/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    search_fields = ['email', 'full_name', 'organization_name']
    ordering = ['full_name', 'email']
    export_fields = ['email', 'full_name', 'professional_title', 'organization_name', 'phone']
    
    def get_queryset(self):
        list_uuid = self.kwargs.get('list_uuid')
        return Contact.objects.filter(
            contact_list__uuid=list_uuid,
            contact_list__owner=self.request.user
        )
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return serializers.ContactCreateSerializer
        return serializers.ContactSerializer
    
    def perform_create(self, serializer):
        list_uuid = self.kwargs.get('list_uuid')
        contact_list = ContactList.objects.get(
            uuid=list_uuid, owner=self.request.user
        )
        serializer.save(contact_list=contact_list)
    
    @action(detail=False, methods=['post'], url_path='import')
    def import_contacts(self, request, list_uuid=None):
        """Import contacts from CSV."""
        import csv
        import io
        
        serializer = serializers.ContactImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        contact_list = ContactList.objects.get(
            uuid=list_uuid, owner=request.user
        )
        
        file = serializer.validated_data['file']
        mapping = serializer.validated_data['column_mapping']
        tags = serializer.validated_data.get('tags', [])
        
        # Parse CSV
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        created = 0
        updated = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):
            try:
                email = row.get(mapping.get('email', 'email'), '').lower().strip()
                if not email:
                    errors.append(f"Row {row_num}: Missing email")
                    continue
                
                contact_data = {'email': email}
                
                # Map other fields
                field_mapping = {
                    'full_name': ['name', 'full_name', 'first_name'],
                    'professional_title': ['title', 'professional_title', 'job_title'],
                    'organization_name': ['organization', 'company', 'org'],
                    'phone': ['phone', 'phone_number'],
                }
                
                for field, csv_options in field_mapping.items():
                    mapped_col = mapping.get(field)
                    if mapped_col:
                        contact_data[field] = row.get(mapped_col, '')
                
                if tags:
                    contact_data['tags'] = tags
                
                contact, was_created = Contact.objects.update_or_create(
                    contact_list=contact_list,
                    email=email,
                    defaults=contact_data
                )
                
                if was_created:
                    created += 1
                else:
                    updated += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        return Response({
            'created': created,
            'updated': updated,
            'errors': errors[:10],  # Limit error messages
            'total_errors': len(errors),
        })


class GlobalContactSearchView(generics.ListAPIView):
    """
    Search across all contacts.
    
    GET /api/v1/contacts/search/?q=...
    """
    serializer_class = serializers.ContactSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]
    search_fields = ['email', 'full_name', 'organization_name']
    
    def get_queryset(self):
        return Contact.objects.filter(
            contact_list__owner=self.request.user
        ).distinct()
```

---

## Billing API

### Serializers

```python
# billing/serializers.py

from rest_framework import serializers
from common.serializers import BaseModelSerializer
from .models import Subscription, Invoice, PaymentMethod, Plan


class PlanSerializer(serializers.ModelSerializer):
    """Subscription plan."""
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'description', 'price_monthly', 'price_yearly',
            'features', 'max_events_per_month', 'max_certificates_per_month',
            'is_active',
        ]


class SubscriptionSerializer(BaseModelSerializer):
    """User subscription."""
    plan = PlanSerializer(read_only=True)
    days_until_renewal = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'uuid', 'plan', 'status', 'billing_cycle',
            'current_period_start', 'current_period_end',
            'trial_end', 'cancel_at_period_end',
            'days_until_renewal',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
    
    def get_days_until_renewal(self, obj):
        if obj.current_period_end:
            from django.utils import timezone
            delta = obj.current_period_end - timezone.now()
            return max(0, delta.days)
        return None


class SubscriptionCreateSerializer(serializers.Serializer):
    """Create subscription."""
    plan_id = serializers.IntegerField()
    billing_cycle = serializers.ChoiceField(choices=['monthly', 'yearly'])
    payment_method_uuid = serializers.UUIDField(required=False)


class SubscriptionUpdateSerializer(serializers.Serializer):
    """Update subscription (change plan)."""
    plan_id = serializers.IntegerField()


class PaymentMethodSerializer(BaseModelSerializer):
    """Payment method (card)."""
    class Meta:
        model = PaymentMethod
        fields = [
            'uuid', 'card_brand', 'card_last4', 'card_exp_month',
            'card_exp_year', 'is_default', 'created_at',
        ]
        read_only_fields = fields


class PaymentMethodCreateSerializer(serializers.Serializer):
    """Add payment method via Stripe token."""
    stripe_token = serializers.CharField()
    set_as_default = serializers.BooleanField(default=True)


class InvoiceSerializer(BaseModelSerializer):
    """Invoice."""
    class Meta:
        model = Invoice
        fields = [
            'uuid', 'invoice_number', 'status', 'amount', 'currency',
            'description', 'period_start', 'period_end',
            'pdf_url', 'paid_at', 'created_at',
        ]
        read_only_fields = fields


class UsageSerializer(serializers.Serializer):
    """Current billing period usage."""
    events_created = serializers.IntegerField()
    events_limit = serializers.IntegerField(allow_null=True)
    certificates_issued = serializers.IntegerField()
    certificates_limit = serializers.IntegerField(allow_null=True)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
```

### ViewSets

```python
# billing/views.py

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from common.permissions import IsOrganizer
from . import serializers
from .models import Subscription, Invoice, PaymentMethod, Plan


class PlanListView(generics.ListAPIView):
    """
    GET /api/v1/billing/plans/
    
    List available plans (public).
    """
    serializer_class = serializers.PlanSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return Plan.objects.filter(is_active=True).order_by('price_monthly')


class SubscriptionView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/billing/subscription/
    POST   /api/v1/billing/subscription/
    PATCH  /api/v1/billing/subscription/
    DELETE /api/v1/billing/subscription/
    
    Manage current user's subscription.
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return serializers.SubscriptionCreateSerializer
        if self.request.method == 'PATCH':
            return serializers.SubscriptionUpdateSerializer
        return serializers.SubscriptionSerializer
    
    def get_object(self):
        return self.request.user.subscription
    
    def retrieve(self, request, *args, **kwargs):
        try:
            subscription = self.get_object()
            serializer = serializers.SubscriptionSerializer(subscription)
            return Response(serializer.data)
        except Subscription.DoesNotExist:
            return Response({'subscription': None})
    
    def post(self, request):
        """Create subscription."""
        serializer = serializers.SubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from billing.services import stripe_service
        
        subscription = stripe_service.create_subscription(
            user=request.user,
            plan_id=serializer.validated_data['plan_id'],
            billing_cycle=serializer.validated_data['billing_cycle'],
            payment_method_uuid=serializer.validated_data.get('payment_method_uuid'),
        )
        
        return Response(
            serializers.SubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED
        )
    
    def patch(self, request, *args, **kwargs):
        """Change plan."""
        serializer = serializers.SubscriptionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        subscription = self.get_object()
        
        from billing.services import stripe_service
        subscription = stripe_service.change_plan(
            subscription=subscription,
            new_plan_id=serializer.validated_data['plan_id'],
        )
        
        return Response(serializers.SubscriptionSerializer(subscription).data)
    
    def delete(self, request, *args, **kwargs):
        """Cancel subscription."""
        subscription = self.get_object()
        
        from billing.services import stripe_service
        stripe_service.cancel_subscription(subscription)
        
        return Response({'message': 'Subscription cancelled.'})


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    Manage payment methods.
    
    GET    /api/v1/billing/payment-methods/
    POST   /api/v1/billing/payment-methods/
    DELETE /api/v1/billing/payment-methods/{uuid}/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.PaymentMethodCreateSerializer
        return serializers.PaymentMethodSerializer
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from billing.services import stripe_service
        
        payment_method = stripe_service.add_payment_method(
            user=request.user,
            stripe_token=serializer.validated_data['stripe_token'],
            set_as_default=serializer.validated_data['set_as_default'],
        )
        
        return Response(
            serializers.PaymentMethodSerializer(payment_method).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, uuid=None):
        """Set as default payment method."""
        payment_method = self.get_object()
        
        PaymentMethod.objects.filter(user=request.user).update(is_default=False)
        payment_method.is_default = True
        payment_method.save()
        
        return Response({'message': 'Payment method set as default.'})


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View invoices.
    
    GET /api/v1/billing/invoices/
    GET /api/v1/billing/invoices/{uuid}/
    """
    serializer_class = serializers.InvoiceSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]
    lookup_field = 'uuid'
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Invoice.objects.filter(subscription__user=self.request.user)


class UsageView(generics.RetrieveAPIView):
    """
    GET /api/v1/billing/usage/
    
    Current billing period usage.
    """
    serializer_class = serializers.UsageSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]
    
    def retrieve(self, request):
        subscription = request.user.subscription
        
        # Calculate usage
        from events.models import Event
        from certificates.models import Certificate
        
        events_created = Event.objects.filter(
            owner=request.user,
            created_at__gte=subscription.current_period_start,
            created_at__lte=subscription.current_period_end,
        ).count()
        
        certificates_issued = Certificate.objects.filter(
            issued_by=request.user,
            issued_at__gte=subscription.current_period_start,
            issued_at__lte=subscription.current_period_end,
        ).count()
        
        return Response({
            'events_created': events_created,
            'events_limit': subscription.plan.max_events_per_month,
            'certificates_issued': certificates_issued,
            'certificates_limit': subscription.plan.max_certificates_per_month,
            'period_start': subscription.current_period_start,
            'period_end': subscription.current_period_end,
        })
```

---

## Webhooks

### Zoom Webhooks

```python
# webhooks/views.py

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import hmac
import hashlib
import json


@method_decorator(csrf_exempt, name='dispatch')
class ZoomWebhookView(APIView):
    """
    POST /api/v1/webhooks/zoom/
    
    Handle Zoom webhook events.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Verify signature
        if not self._verify_signature(request):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        event_type = request.data.get('event')
        payload = request.data.get('payload', {})
        
        # Handle different event types
        handlers = {
            'meeting.started': self._handle_meeting_started,
            'meeting.ended': self._handle_meeting_ended,
            'meeting.participant_joined': self._handle_participant_joined,
            'meeting.participant_left': self._handle_participant_left,
            'recording.completed': self._handle_recording_completed,
        }
        
        handler = handlers.get(event_type)
        if handler:
            handler(payload)
        
        return Response({'status': 'received'})
    
    def _verify_signature(self, request):
        """Verify Zoom webhook signature."""
        from django.conf import settings
        
        signature = request.headers.get('x-zm-signature')
        timestamp = request.headers.get('x-zm-request-timestamp')
        
        if not signature or not timestamp:
            return False
        
        message = f"v0:{timestamp}:{request.body.decode()}"
        expected = 'v0=' + hmac.new(
            settings.ZOOM_WEBHOOK_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    def _handle_meeting_started(self, payload):
        """Mark event as live."""
        meeting_id = payload.get('object', {}).get('id')
        
        from events.models import Event
        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
            event.start()
        except Event.DoesNotExist:
            pass
    
    def _handle_meeting_ended(self, payload):
        """Mark event as completed."""
        meeting_id = payload.get('object', {}).get('id')
        
        from events.models import Event
        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
            event.complete()
            
            # Trigger auto-certificate issuance if enabled
            if event.auto_issue_certificates:
                from certificates.tasks import auto_issue_certificates
                auto_issue_certificates.delay(event.id)
        except Event.DoesNotExist:
            pass
    
    def _handle_participant_joined(self, payload):
        """Record participant join."""
        meeting_id = payload.get('object', {}).get('id')
        participant = payload.get('object', {}).get('participant', {})
        
        email = participant.get('email', '').lower()
        join_time = participant.get('join_time')
        
        from events.models import Event
        from registrations.models import Registration, AttendanceRecord
        
        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
            
            # Find registration
            registration = Registration.objects.filter(
                event=event,
                user__email=email
            ).first() or Registration.objects.filter(
                event=event,
                guest_email=email
            ).first()
            
            if registration:
                AttendanceRecord.objects.create(
                    registration=registration,
                    joined_at=join_time,
                    join_source='zoom_webhook',
                )
                
                if not registration.join_time:
                    registration.join_time = join_time
                    registration.save()
        except Event.DoesNotExist:
            pass
    
    def _handle_participant_left(self, payload):
        """Record participant leave."""
        meeting_id = payload.get('object', {}).get('id')
        participant = payload.get('object', {}).get('participant', {})
        
        email = participant.get('email', '').lower()
        leave_time = participant.get('leave_time')
        
        from registrations.models import Registration, AttendanceRecord
        from events.models import Event
        
        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
            
            registration = Registration.objects.filter(
                event=event,
                user__email=email
            ).first() or Registration.objects.filter(
                event=event,
                guest_email=email
            ).first()
            
            if registration:
                # Update latest attendance record
                latest_record = registration.attendance_records.filter(
                    left_at__isnull=True
                ).order_by('-joined_at').first()
                
                if latest_record:
                    latest_record.left_at = leave_time
                    latest_record.calculate_duration()
                    latest_record.save()
                
                registration.leave_time = leave_time
                registration.update_attendance_stats()
        except Event.DoesNotExist:
            pass
    
    def _handle_recording_completed(self, payload):
        """Process completed recording."""
        meeting_id = payload.get('object', {}).get('id')
        recording_files = payload.get('object', {}).get('recording_files', [])
        
        from events.models import Event
        from recordings.models import ZoomRecording, ZoomRecordingFile
        
        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
            
            recording = ZoomRecording.objects.create(
                event=event,
                zoom_recording_id=payload.get('object', {}).get('uuid'),
                duration_minutes=payload.get('object', {}).get('duration', 0),
                recording_start=payload.get('object', {}).get('recording_start'),
                recording_end=payload.get('object', {}).get('recording_end'),
            )
            
            for file_data in recording_files:
                ZoomRecordingFile.objects.create(
                    recording=recording,
                    file_type=file_data.get('file_type'),
                    file_size=file_data.get('file_size'),
                    download_url=file_data.get('download_url'),
                    play_url=file_data.get('play_url'),
                )
            
            # Auto-publish if enabled
            if event.auto_publish_recordings:
                recording.publish()
        except Event.DoesNotExist:
            pass


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """
    POST /api/v1/webhooks/stripe/
    
    Handle Stripe webhook events.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        import stripe
        from django.conf import settings
        
        payload = request.body
        sig_header = request.headers.get('Stripe-Signature')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        handlers = {
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.paid': self._handle_invoice_paid,
            'invoice.payment_failed': self._handle_payment_failed,
        }
        
        handler = handlers.get(event['type'])
        if handler:
            handler(event['data']['object'])
        
        return Response({'status': 'received'})
    
    def _handle_subscription_updated(self, stripe_sub):
        """Sync subscription status from Stripe."""
        from billing.models import Subscription
        
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_sub['id']
            )
            subscription.status = stripe_sub['status']
            subscription.current_period_start = stripe_sub['current_period_start']
            subscription.current_period_end = stripe_sub['current_period_end']
            subscription.cancel_at_period_end = stripe_sub['cancel_at_period_end']
            subscription.save()
        except Subscription.DoesNotExist:
            pass
    
    def _handle_subscription_deleted(self, stripe_sub):
        """Handle cancelled subscription."""
        from billing.models import Subscription
        
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_sub['id']
            )
            subscription.status = 'canceled'
            subscription.save()
        except Subscription.DoesNotExist:
            pass
    
    def _handle_invoice_paid(self, stripe_invoice):
        """Record paid invoice."""
        from billing.models import Invoice, Subscription
        
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_invoice['subscription']
            )
            
            Invoice.objects.update_or_create(
                stripe_invoice_id=stripe_invoice['id'],
                defaults={
                    'subscription': subscription,
                    'status': 'paid',
                    'amount': stripe_invoice['amount_paid'] / 100,
                    'paid_at': stripe_invoice['status_transitions']['paid_at'],
                    'pdf_url': stripe_invoice['invoice_pdf'],
                }
            )
        except Subscription.DoesNotExist:
            pass
    
    def _handle_payment_failed(self, stripe_invoice):
        """Handle failed payment."""
        from billing.models import Subscription
        from billing.tasks import send_payment_failed_email
        
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_invoice['subscription']
            )
            subscription.status = 'past_due'
            subscription.save()
            
            send_payment_failed_email.delay(subscription.user_id)
        except Subscription.DoesNotExist:
            pass
```

---

## URL Configuration Summary

```python
# config/urls.py

from django.urls import path, include

urlpatterns = [
    # API v1
    path('api/v1/', include([
        path('', include('accounts.urls')),
        path('', include('events.urls')),
        path('', include('registrations.urls')),
        path('', include('certificates.urls')),
        path('', include('contacts.urls')),
        path('', include('billing.urls')),
        path('', include('learning.urls')),
        path('', include('recordings.urls')),
        
        # Webhooks
        path('webhooks/zoom/', ZoomWebhookView.as_view(), name='webhook-zoom'),
        path('webhooks/stripe/', StripeWebhookView.as_view(), name='webhook-stripe'),
    ])),
    
    # Schema/docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```
