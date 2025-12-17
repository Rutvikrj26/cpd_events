"""
Serializers for billing API.
"""

from rest_framework import serializers

from .models import Subscription, Invoice, PaymentMethod


class SubscriptionSerializer(serializers.ModelSerializer):
    """Full subscription details."""
    
    plan_display = serializers.CharField(source='get_plan_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_trialing = serializers.BooleanField(read_only=True)
    limits = serializers.DictField(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'uuid', 'plan', 'plan_display', 'status', 'status_display',
            'is_active', 'is_trialing', 'limits',
            'current_period_start', 'current_period_end',
            'trial_ends_at', 'cancel_at_period_end', 'canceled_at',
            'events_created_this_period', 'certificates_issued_this_period',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class SubscriptionStatusSerializer(serializers.ModelSerializer):
    """Minimal subscription status."""
    
    is_active = serializers.BooleanField(read_only=True)
    can_create_event = serializers.SerializerMethodField()
    can_issue_certificate = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'plan', 'status', 'is_active',
            'can_create_event', 'can_issue_certificate',
            'events_created_this_period', 'certificates_issued_this_period',
            'current_period_end'
        ]
    
    def get_can_create_event(self, obj):
        return obj.check_event_limit()
    
    def get_can_issue_certificate(self, obj):
        return obj.check_certificate_limit()


class SubscriptionCreateSerializer(serializers.Serializer):
    """Create or update subscription."""
    
    plan = serializers.ChoiceField(choices=Subscription.Plan.choices)
    payment_method_id = serializers.CharField(required=False, allow_blank=True)
    
    def validate_plan(self, value):
        user = self.context['request'].user
        if hasattr(user, 'subscription') and user.subscription.plan == value:
            raise serializers.ValidationError("Already on this plan")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    """Full invoice details."""
    
    amount_display = serializers.CharField(read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'uuid', 'stripe_invoice_id',
            'amount_cents', 'amount_display', 'currency',
            'status', 'is_paid',
            'invoice_pdf_url', 'hosted_invoice_url',
            'period_start', 'period_end', 'paid_at', 'due_date',
            'created_at'
        ]
        read_only_fields = fields


class InvoiceListSerializer(serializers.ModelSerializer):
    """Invoice list view - minimal fields."""
    
    amount_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'uuid', 'amount_display', 'status',
            'period_start', 'period_end', 'created_at',
            'invoice_pdf_url'
        ]
        read_only_fields = fields


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Payment method details."""
    
    is_expired = serializers.BooleanField(read_only=True)
    card_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'uuid', 'card_brand', 'card_last4',
            'card_exp_month', 'card_exp_year',
            'is_default', 'is_expired', 'card_display',
            'billing_name', 'billing_email',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_card_display(self, obj):
        return f"{obj.card_brand} ****{obj.card_last4}"


class PaymentMethodCreateSerializer(serializers.Serializer):
    """Add payment method via Stripe token."""
    
    stripe_payment_method_id = serializers.CharField()
    set_as_default = serializers.BooleanField(default=True)


class CheckoutSessionSerializer(serializers.Serializer):
    """Create Stripe checkout session."""
    
    plan = serializers.ChoiceField(choices=Subscription.Plan.choices)
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()


class BillingPortalSerializer(serializers.Serializer):
    """Create Stripe billing portal session."""
    
    return_url = serializers.URLField()
