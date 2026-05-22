from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Sector, HealthLabel, Company, FiscalYear, ProfitLoss, BalanceSheet, CashFlow, Analysis, ProsCons, MLScore

class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = '__all__'

class HealthLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthLabel
        fields = '__all__'

class FiscalYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalYear
        fields = '__all__'

class CompanySerializer(serializers.ModelSerializer):
    sector_name = serializers.ReadOnlyField(source='sector.sector_name')
    
    class Meta:
        model = Company
        fields = ['company_id', 'symbol', 'company_name', 'sector', 'sector_name', 'industry', 'listing_date']

class ProfitLossSerializer(serializers.ModelSerializer):
    year_val = serializers.ReadOnlyField(source='year.fiscal_year')
    class Meta:
        model = ProfitLoss
        fields = '__all__'

class BalanceSheetSerializer(serializers.ModelSerializer):
    year_val = serializers.ReadOnlyField(source='year.fiscal_year')
    class Meta:
        model = BalanceSheet
        fields = '__all__'

class CashFlowSerializer(serializers.ModelSerializer):
    year_val = serializers.ReadOnlyField(source='year.fiscal_year')
    class Meta:
        model = CashFlow
        fields = '__all__'

class AnalysisSerializer(serializers.ModelSerializer):
    year_val = serializers.ReadOnlyField(source='year.fiscal_year')
    class Meta:
        model = Analysis
        fields = '__all__'

class ProsConsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProsCons
        fields = '__all__'

class MLScoreSerializer(serializers.ModelSerializer):
    health_label = serializers.ReadOnlyField(source='health.label_name')
    year_val = serializers.ReadOnlyField(source='year.fiscal_year')
    class Meta:
        model = MLScore
        fields = '__all__'

# Detailed Serializer for Company Dashboard
class CompanyDetailSerializer(serializers.ModelSerializer):
    sector_name = serializers.ReadOnlyField(source='sector.sector_name')
    scores = serializers.SerializerMethodField()
    financials = serializers.SerializerMethodField()
    pros_cons = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ['company_id', 'symbol', 'company_name', 'sector_name', 'industry', 'scores', 'financials', 'pros_cons']

    @extend_schema_field(MLScoreSerializer(many=True))
    def get_scores(self, obj):
        scores = MLScore.objects.filter(company=obj).order_by('-year__fiscal_year')
        return MLScoreSerializer(scores, many=True).data

    @extend_schema_field(ProfitLossSerializer(many=True))
    def get_financials(self, obj):
        pl = ProfitLoss.objects.filter(company=obj).order_by('-year__fiscal_year')
        return ProfitLossSerializer(pl, many=True).data

    @extend_schema_field(ProsConsSerializer(many=True))
    def get_pros_cons(self, obj):
        pc = ProsCons.objects.filter(company=obj)
        return ProsConsSerializer(pc, many=True).data
