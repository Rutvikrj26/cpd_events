"""
Tests for PromoCodeService.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from factories import EventFactory, RegistrationFactory
from promo_codes.models import PromoCode
from promo_codes.services import (
    PromoCodeExhaustedError,
    PromoCodeExpiredError,
    PromoCodeInactiveError,
    PromoCodeMinimumNotMetError,
    PromoCodeNotApplicableError,
    PromoCodeNotYetValidError,
    PromoCodeService,
    PromoCodeUserLimitError,
)


@pytest.mark.django_db
class TestPromoCodeService:

    @pytest.fixture
    def event(self, db):
        return EventFactory(price=Decimal('100.00'), currency='USD')

    @pytest.fixture
    def promo_code(self, event, db):
        code = PromoCode.objects.create(
            code='TESTCODE',
            discount_type='percentage',
            discount_value=Decimal('10.00'), # 10%
            owner=event.owner,
            is_active=True,
            max_uses=10,
            max_uses_per_user=1
        )
        code.events.add(event)
        return code

    def test_find_code(self, promo_code, event):
        """Should find code case-insensitively."""
        found = PromoCodeService.find_code('testcode', event)
        assert found == promo_code

        found_upper = PromoCodeService.find_code('TESTCODE', event)
        assert found_upper == promo_code

    def test_find_code_invalid_event(self, promo_code):
        """Should not find code if not owned by event owner."""
        other_event = EventFactory()
        found = PromoCodeService.find_code('TESTCODE', other_event)
        assert found is None

    def test_validate_code_success(self, promo_code, event):
        """Should pass validation for valid code."""
        PromoCodeService.validate_code(promo_code, event, 'new@example.com')

    def test_validate_code_inactive(self, promo_code, event):
        """Should fail if inactive."""
        promo_code.is_active = False
        promo_code.save()

        with pytest.raises(PromoCodeInactiveError):
            PromoCodeService.validate_code(promo_code, event, 'test@example.com')

    def test_validate_code_expired(self, promo_code, event):
        """Should fail if expired."""
        promo_code.valid_until = timezone.now() - timedelta(days=1)
        promo_code.save()

        with pytest.raises(PromoCodeExpiredError):
            PromoCodeService.validate_code(promo_code, event, 'test@example.com')

    def test_validate_code_not_yet_valid(self, promo_code, event):
        """Should fail if valid_from is in future."""
        promo_code.valid_from = timezone.now() + timedelta(days=1)
        promo_code.save()

        with pytest.raises(PromoCodeNotYetValidError):
            PromoCodeService.validate_code(promo_code, event, 'test@example.com')

    def test_validate_code_exhausted(self, promo_code, event):
        """Should fail if max uses reached."""
        promo_code.current_uses = 10
        promo_code.max_uses = 10
        promo_code.save()

        with pytest.raises(PromoCodeExhaustedError):
            PromoCodeService.validate_code(promo_code, event, 'test@example.com')

    def test_validate_code_user_limit(self, promo_code, event):
        """Should fail if user limit reached."""
        # Create usage
        reg = RegistrationFactory(event=event, email='user@example.com')
        PromoCodeService.apply_code(promo_code, reg, event.price)

        with pytest.raises(PromoCodeUserLimitError):
            PromoCodeService.validate_code(promo_code, event, 'user@example.com')

    def test_validate_code_event_mismatch(self, promo_code, event):
        """Should fail if not applicable to event."""
        other_event = EventFactory(owner=event.owner, price=Decimal('100.00'))
        # Code is linked to 'event', not 'other_event'

        with pytest.raises(PromoCodeNotApplicableError):
            PromoCodeService.validate_code(promo_code, other_event, 'test@example.com')

    def test_validate_code_minimum_not_met(self, promo_code, event):
        """Should fail if event price < minimum_order_amount."""
        promo_code.minimum_order_amount = Decimal('200.00')
        promo_code.save()

        with pytest.raises(PromoCodeMinimumNotMetError):
            PromoCodeService.validate_code(promo_code, event, 'test@example.com')

    def test_apply_code_atomic(self, promo_code, event):
        """Should atomically increment usage."""
        reg = RegistrationFactory(event=event, email='apply@example.com')

        usage = PromoCodeService.apply_code(promo_code, reg, event.price)

        promo_code.refresh_from_db()
        assert promo_code.current_uses == 1
        assert usage.discount_amount == Decimal('10.00') # 10% of 100
        assert usage.final_price == Decimal('90.00')

    def test_apply_code_race_condition_check(self, promo_code, event):
        """
        Verify exhausted error is raised inside apply if limit reached concurrently.
        We simulate this by manually setting limit before calling apply.
        """
        promo_code.current_uses = 9
        promo_code.max_uses = 10
        promo_code.save()

        # First use OK
        reg1 = RegistrationFactory(event=event, email='user1@example.com')
        PromoCodeService.apply_code(promo_code, reg1, event.price)

        promo_code.refresh_from_db()
        assert promo_code.current_uses == 10

        # Second use should fail
        reg2 = RegistrationFactory(event=event, email='user2@example.com')
        with pytest.raises(PromoCodeExhaustedError):
            PromoCodeService.apply_code(promo_code, reg2, event.price)

    def test_validate_and_preview(self, promo_code, event):
        """Verify preview dictionary structure."""
        res = PromoCodeService.validate_and_preview('TESTCODE', event, 'new@example.com')

        assert res['valid'] is True
        assert res['code'] == 'TESTCODE'
        assert res['discount_amount'] == '10.00'
        assert res['final_price'] == '90.00'
