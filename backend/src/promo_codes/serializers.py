"""
Promo Code serializers.
"""

from rest_framework import serializers

from .models import PromoCode, PromoCodeUsage


class PromoCodeSerializer(serializers.ModelSerializer):
    """Full promo code serializer for organizers."""

    discount_display = serializers.CharField(source="get_discount_display", read_only=True)
    uses_remaining = serializers.IntegerField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    event_uuids = serializers.ListField(child=serializers.UUIDField(), write_only=True, required=False, allow_empty=True)
    events_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PromoCode
        fields = [
            "uuid",
            "code",
            "description",
            "currency",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "discount_display",
            "is_active",
            "valid_from",
            "valid_until",
            "max_uses",
            "max_uses_per_user",
            "current_uses",
            "uses_remaining",
            "minimum_order_amount",
            "first_time_only",
            "is_valid",
            "is_expired",
            "event_uuids",
            "events_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "current_uses", "created_at", "updated_at"]

    def get_events_data(self, obj):
        """Return basic event info for linked events."""
        return [{"uuid": str(e.uuid), "title": e.title} for e in obj.events.all()]

    def validate_code(self, value):
        """Normalize code to uppercase."""
        return value.upper().strip()

    def validate_discount_value(self, value):
        """Validate discount value based on type."""
        if value <= 0:
            raise serializers.ValidationError("Discount value must be positive.")
        return value

    def validate(self, data):
        """Cross-field validation."""
        discount_type = data.get("discount_type", getattr(self.instance, "discount_type", None))
        discount_value = data.get("discount_value", getattr(self.instance, "discount_value", None))

        if discount_type == PromoCode.DiscountType.PERCENTAGE:
            if discount_value and discount_value > 100:
                raise serializers.ValidationError({"discount_value": "Percentage discount cannot exceed 100%."})

        # Validate date range
        valid_from = data.get("valid_from")
        valid_until = data.get("valid_until")
        if valid_from and valid_until and valid_from >= valid_until:
            raise serializers.ValidationError({"valid_until": "End date must be after start date."})

        return data

    def create(self, validated_data):
        event_uuids = validated_data.pop("event_uuids", [])
        request = self.context.get("request")

        promo_code = PromoCode.objects.create(owner=request.user, **validated_data)

        # Link events
        if event_uuids:
            from events.models import Event

            events = Event.objects.filter(uuid__in=event_uuids, owner=request.user, deleted_at__isnull=True)
            promo_code.events.set(events)

        return promo_code

    def update(self, instance, validated_data):
        event_uuids = validated_data.pop("event_uuids", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update events if provided
        if event_uuids is not None:
            from events.models import Event

            request = self.context.get("request")
            events = Event.objects.filter(uuid__in=event_uuids, owner=request.user, deleted_at__isnull=True)
            instance.events.set(events)

        return instance


class PromoCodeUsageSerializer(serializers.ModelSerializer):
    """Serializer for usage records."""

    promo_code_code = serializers.CharField(source="promo_code.code", read_only=True)
    registration_uuid = serializers.UUIDField(source="registration.uuid", read_only=True)
    event_title = serializers.CharField(source="registration.event.title", read_only=True)

    class Meta:
        model = PromoCodeUsage
        fields = [
            "uuid",
            "promo_code_code",
            "registration_uuid",
            "event_title",
            "user_email",
            "original_price",
            "discount_amount",
            "final_price",
            "created_at",
        ]


class ValidatePromoCodeSerializer(serializers.Serializer):
    """Serializer for promo code validation request."""

    code = serializers.CharField(max_length=50)
    event_uuid = serializers.UUIDField()
    email = serializers.EmailField()


class PromoCodePreviewSerializer(serializers.Serializer):
    """Serializer for promo code preview response."""

    valid = serializers.BooleanField()
    code = serializers.CharField()
    discount_type = serializers.CharField()
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_display = serializers.CharField()
    original_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    promo_code_uuid = serializers.UUIDField()
