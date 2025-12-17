"""
CPD requirement serializers.
"""

from rest_framework import serializers
from accounts.models import CPDRequirement


class CPDRequirementSerializer(serializers.ModelSerializer):
    """Full CPD requirement details."""
    
    period_type_display = serializers.CharField(
        source='get_period_type_display', read_only=True
    )
    earned_credits = serializers.SerializerMethodField()
    completion_percent = serializers.IntegerField(read_only=True)
    credits_remaining = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    period_bounds = serializers.SerializerMethodField()
    
    class Meta:
        model = CPDRequirement
        fields = [
            'uuid', 'cpd_type', 'cpd_type_display',
            'annual_requirement', 'period_type', 'period_type_display',
            'fiscal_year_start_month', 'fiscal_year_start_day',
            'licensing_body', 'license_number', 'notes',
            'is_active', 'earned_credits', 'completion_percent',
            'credits_remaining', 'period_bounds',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']
    
    def get_earned_credits(self, obj):
        return str(obj.get_earned_credits())
    
    def get_period_bounds(self, obj):
        start, end = obj.get_current_period_bounds()
        return {
            'start': start.isoformat(),
            'end': end.isoformat()
        }


class CPDRequirementCreateSerializer(serializers.ModelSerializer):
    """Create/update CPD requirement."""
    
    class Meta:
        model = CPDRequirement
        fields = [
            'cpd_type', 'cpd_type_display', 'annual_requirement',
            'period_type', 'fiscal_year_start_month', 'fiscal_year_start_day',
            'licensing_body', 'license_number', 'notes', 'is_active'
        ]


class CPDProgressSerializer(serializers.Serializer):
    """CPD progress summary across all requirements."""
    
    total_requirements = serializers.IntegerField()
    completed_requirements = serializers.IntegerField()
    in_progress_requirements = serializers.IntegerField()
    total_credits_earned = serializers.DecimalField(max_digits=8, decimal_places=2)
    requirements = CPDRequirementSerializer(many=True)
