"""
Common base serializers for the API.
"""

from rest_framework import serializers


class UUIDLookupMixin:
    """Mixin to use UUID for lookups instead of PK."""

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
    """Base serializer for soft-delete models."""

    is_deleted = serializers.SerializerMethodField()

    def get_is_deleted(self, obj):
        return obj.deleted_at is not None


# Minimal serializers for embedding in responses
class MinimalUserSerializer(serializers.Serializer):
    """Minimal user representation for embedding."""

    uuid = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField()


class MinimalEventSerializer(serializers.Serializer):
    """Minimal event representation for embedding.

    Recording-visibility fields:
      - `published_recordings_count`: how many recordings attendees can see.
      - `has_published_recording`: convenience boolean for the above.
      - `has_recording`: true iff the **current request user** can watch any
        recording for this event. Hosts/admins see this true even when no
        recording is published yet (they get a preview UX); other users
        only when something is published. Drives the My Learning "Watch
        Recording" button so organizers can review before publishing.

    All counts are computed lazily — one extra query per serialized event.
    Fine for typical 8–20 row registration lists; if it starts mattering,
    annotate the queryset before serialization.
    """

    uuid = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.SlugField()
    starts_at = serializers.DateTimeField()
    status = serializers.CharField()
    cpd_credit_value = serializers.DecimalField(max_digits=5, decimal_places=2)
    cpd_credit_type = serializers.CharField()
    has_published_recording = serializers.SerializerMethodField()
    published_recordings_count = serializers.SerializerMethodField()
    has_recording = serializers.SerializerMethodField()

    def get_has_published_recording(self, obj):
        return self._published_count(obj) > 0

    def get_published_recordings_count(self, obj):
        return self._published_count(obj)

    def get_has_recording(self, obj):
        # Hosts + platform admins can preview unpublished recordings, so
        # the watch button needs to surface to them whenever ANY recording
        # exists (RECORDING / PROCESSING / AVAILABLE — the EventRecordingPage
        # itself handles the "still processing" empty states). Everyone
        # else sees the button only when a recording is actually published.
        if self._user_can_preview_unpublished(obj):
            return self._total_count(obj) > 0
        return self._published_count(obj) > 0

    def _user_can_preview_unpublished(self, obj) -> bool:
        request = self.context.get('request')
        if not request:
            return False
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if isinstance(obj, dict):
            # We don't have a model handle for `is_event_host` checks against
            # a plain dict; bail out conservatively.
            return False
        # Local imports to avoid circular dep at module load time.
        from conferencing.views import is_event_host, is_platform_admin
        return is_platform_admin(user) or is_event_host(user, obj)

    def _published_count(self, obj):
        return self._count(obj, only_published=True)

    def _total_count(self, obj):
        return self._count(obj, only_published=False)

    def _count(self, obj, *, only_published: bool):
        from conferencing.models import VideoRecording

        # Cache both variants per-instance so the three derived fields
        # share a single query each (worst case 2 queries / event).
        cache_attr = (
            '_published_recording_count_cache'
            if only_published
            else '_total_recording_count_cache'
        )
        cache = getattr(obj, cache_attr, None)
        if cache is not None:
            return cache

        # Resolve the right filter key. `VideoRecording.event` is an FK to
        # the integer `id` PK of Event, NOT the public `uuid` column —
        # so we filter via the related `event__uuid` lookup. When `obj`
        # is the Event model instance we pass it directly, which lets
        # Django use the FK shortcut and avoids the related join.
        event_uuid = obj.uuid if isinstance(obj, dict) else getattr(obj, 'uuid', None)
        if not event_uuid:
            return 0

        # `is_published` (boolean) is the source of truth for "currently
        # visible to attendees" — `published_at` remains set even after
        # an admin un-publishes via the manage panel.
        # `VideoRecording` is not a soft-delete model — no `deleted_at`.
        if isinstance(obj, dict):
            qs = VideoRecording.objects.filter(event__uuid=event_uuid)
        else:
            qs = VideoRecording.objects.filter(event=obj)
        if only_published:
            qs = qs.filter(is_published=True)
        count = qs.count()

        try:
            setattr(obj, cache_attr, count)
        except Exception:
            # `obj` may be a dict in some serializer contexts.
            pass
        return count
