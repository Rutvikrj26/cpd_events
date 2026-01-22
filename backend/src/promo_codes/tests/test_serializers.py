"""
Tests for promo code serializers - validation logic.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from promo_codes.models import PromoCode
from promo_codes.serializers import PromoCodeSerializer, ValidatePromoCodeSerializer


@pytest.mark.django_db
class TestPromoCodeSerializer:
    """Tests for PromoCodeSerializer validation."""

    def test_code_normalized_to_uppercase(self, organizer, rf):
        """Test that promo codes are normalized to uppercase."""
        request = rf.post('/')
        request.user = organizer

        serializer = PromoCodeSerializer(
            data={
                "code": "save20",  # lowercase
                "discount_type": "percentage",
                "discount_value": "20.00",
            },
            context={'request': request}
        )

        assert serializer.is_valid()
        assert serializer.validated_data["code"] == "SAVE20"

    def test_code_strips_whitespace(self, organizer, rf):
        """Test that whitespace is stripped from codes."""
        request = rf.post('/')
        request.user = organizer

        serializer = PromoCodeSerializer(
            data={
                "code": "  SAVE20  ",
                "discount_type": "percentage",
                "discount_value": "20.00",
            },
            context={'request': request}
        )

        assert serializer.is_valid()
        assert serializer.validated_data["code"] == "SAVE20"

    def test_discount_value_must_be_positive(self, organizer, rf):
        """Test that discount value must be positive."""
        request = rf.post('/')
        request.user = organizer

        serializer = PromoCodeSerializer(
            data={
                "code": "NEGATIVE",
                "discount_type": "percentage",
                "discount_value": "-10.00",
            },
            context={'request': request}
        )

        assert not serializer.is_valid()
        assert "discount_value" in serializer.errors

    def test_discount_value_cannot_be_zero(self, organizer, rf):
        """Test that discount value cannot be zero."""
        request = rf.post('/')
        request.user = organizer

        serializer = PromoCodeSerializer(
            data={
                "code": "ZERO",
                "discount_type": "percentage",
                "discount_value": "0.00",
            },
            context={'request': request}
        )

        assert not serializer.is_valid()
        assert "discount_value" in serializer.errors

    def test_percentage_discount_cannot_exceed_100(self, organizer, rf):
        """Test that percentage discounts cannot exceed 100%."""
        request = rf.post('/')
        request.user = organizer

        serializer = PromoCodeSerializer(
            data={
                "code": "TOOBIG",
                "discount_type": "percentage",
                "discount_value": "150.00",
            },
            context={'request': request}
        )

        assert not serializer.is_valid()
        assert "discount_value" in serializer.errors

    def test_percentage_discount_100_is_valid(self, organizer, rf):
        """Test that 100% discount is valid."""
        request = rf.post('/')
        request.user = organizer

        serializer = PromoCodeSerializer(
            data={
                "code": "FREE",
                "discount_type": "percentage",
                "discount_value": "100.00",
            },
            context={'request': request}
        )

        assert serializer.is_valid()

    def test_fixed_amount_can_exceed_100(self, organizer, rf):
        """Test that fixed amount discounts can exceed 100."""
        request = rf.post('/')
        request.user = organizer

        serializer = PromoCodeSerializer(
            data={
                "code": "BIG",
                "discount_type": "fixed_amount",
                "discount_value": "200.00",
            },
            context={'request': request}
        )

        assert serializer.is_valid()

    def test_valid_until_must_be_after_valid_from(self, organizer, rf):
        """Test date range validation."""
        request = rf.post('/')
        request.user = organizer

        now = timezone.now()
        serializer = PromoCodeSerializer(
            data={
                "code": "DATES",
                "discount_type": "percentage",
                "discount_value": "10.00",
                "valid_from": now + timedelta(days=2),
                "valid_until": now + timedelta(days=1),  # Before valid_from
            },
            context={'request': request}
        )

        assert not serializer.is_valid()
        assert "valid_until" in serializer.errors

    def test_valid_date_range(self, organizer, rf):
        """Test valid date range."""
        request = rf.post('/')
        request.user = organizer

        now = timezone.now()
        serializer = PromoCodeSerializer(
            data={
                "code": "DATES",
                "discount_type": "percentage",
                "discount_value": "10.00",
                "valid_from": now,
                "valid_until": now + timedelta(days=7),
            },
            context={'request': request}
        )

        assert serializer.is_valid()

    def test_create_with_event_uuids(self, organizer, published_event, rf):
        """Test creating promo code with linked events."""
        request = rf.post('/')
        request.user = organizer

        serializer = PromoCodeSerializer(
            data={
                "code": "EVENT",
                "discount_type": "percentage",
                "discount_value": "15.00",
                "event_uuids": [str(published_event.uuid)],
            },
            context={'request': request}
        )

        assert serializer.is_valid()
        promo = serializer.save()

        assert promo.events.count() == 1
        assert promo.events.first() == published_event

    def test_update_event_links(self, organizer, published_event, rf):
        """Test updating event links."""
        # Create promo code
        promo = PromoCode.objects.create(
            owner=organizer,
            code="UPDATE",
            discount_type="percentage",
            discount_value=10,
        )

        request = rf.put('/')
        request.user = organizer

        # Update with new event
        serializer = PromoCodeSerializer(
            instance=promo,
            data={
                "code": "UPDATE",
                "discount_type": "percentage",
                "discount_value": "10.00",
                "event_uuids": [str(published_event.uuid)],
            },
            context={'request': request}
        )

        assert serializer.is_valid()
        promo = serializer.save()

        assert promo.events.count() == 1
        assert promo.events.first() == published_event


@pytest.mark.django_db
class TestValidatePromoCodeSerializer:
    """Tests for ValidatePromoCodeSerializer."""

    def test_valid_data(self):
        """Test serializer with valid data."""
        from uuid import uuid4

        serializer = ValidatePromoCodeSerializer(
            data={
                "code": "TEST",
                "event_uuid": str(uuid4()),
                "email": "test@example.com",
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["code"] == "TEST"

    def test_invalid_email(self):
        """Test serializer rejects invalid email."""
        from uuid import uuid4

        serializer = ValidatePromoCodeSerializer(
            data={
                "code": "TEST",
                "event_uuid": str(uuid4()),
                "email": "not-an-email",
            }
        )

        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_invalid_uuid(self):
        """Test serializer rejects invalid UUID."""
        serializer = ValidatePromoCodeSerializer(
            data={
                "code": "TEST",
                "event_uuid": "not-a-uuid",
                "email": "test@example.com",
            }
        )

        assert not serializer.is_valid()
        assert "event_uuid" in serializer.errors

    def test_missing_fields(self):
        """Test serializer rejects missing required fields."""
        serializer = ValidatePromoCodeSerializer(data={})

        assert not serializer.is_valid()
        assert "code" in serializer.errors
        assert "event_uuid" in serializer.errors
        assert "email" in serializer.errors


# Add pytest.helpers if not available
@pytest.fixture(autouse=True)
def setup_helpers():
    """Setup pytest helpers."""
    if not hasattr(pytest, 'helpers'):
        pytest.helpers = type('Helpers', (), {})()
