import logging
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg, Sum, Count, Max
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import (
    Sector, Company, ProfitLoss, MLScore, Analysis, 
    ProsCons, FiscalYear, BalanceSheet, CashFlow
)
from .serializers import (
    SectorSerializer, CompanySerializer, CompanyDetailSerializer, 
    MLScoreSerializer, ProfitLossSerializer, AnalysisSerializer, ProsConsSerializer
)
from .stock_service import StockService

logger = logging.getLogger(__name__)

def register(request):
    """Registration view for new analysts with enhanced production logging."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                logger.info(f"User {user.username} created successfully.")
                login(request, user)
                logger.info(f"User {user.username} logged in successfully. Redirecting to dashboard.")
                return redirect('dashboard')
            except Exception as e:
                logger.error(f"Error during user registration/login: {str(e)}")
                return render(request, 'registration/register.html', {
                    'form': form,
                    'error': "An internal error occurred during registration. Please try again."
                })
        else:
            logger.warning(f"Registration form invalid: {form.errors}")
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

from django.http import HttpResponse

def ping(request):
    """Public health check endpoint."""
    return HttpResponse("pong", status=200)

@login_required
@cache_page(60 * 5)  # Cache for 5 minutes
def dashboard(request):
    """Main dashboard view with robust multi-record year handling and error fallback."""
    try:
        total_companies = Company.objects.count()
        sectors = Sector.objects.annotate(company_count=Count('company'))
        
        # 🚀 FIX: Find the latest YEAR VALUE that actually has scores
        latest_year_val = MLScore.objects.aggregate(max_year=Max('year__fiscal_year'))['max_year']
        
        if latest_year_val:
            latest_scores = MLScore.objects.filter(
                year__fiscal_year=latest_year_val
            ).select_related('company', 'health').order_by('-probability_score')
        else:
            latest_scores = MLScore.objects.none()
            latest_year_val = "N/A"
    except Exception as e:
        logger.error(f"Database error in dashboard: {e}")
        total_companies = 0
        sectors = []
        latest_scores = []
        latest_year_val = "Error"

    # Add live market trends (non-blocking errors)
    try:
        market_trends = StockService.get_market_trends()
    except Exception as e:
        logger.error(f"Stock service error in dashboard: {e}")
        market_trends = []
    
    context = {
        'total_companies': total_companies,
        'sectors': sectors,
        'latest_scores': latest_scores[:10] if latest_scores else [], 
        'display_year': latest_year_val,
        'market_trends': market_trends
    }
    return render(request, 'analytics/dashboard.html', context)

@login_required
def company_detail(request, symbol):
    """Deep-dive company analysis view with multi-dimensional data."""
    company = get_object_or_404(Company, symbol=symbol)
    
    # Fetch live stock data
    live_data = StockService.get_live_data(company.symbol)
    
    # 1. Historical Metrics
    scores = MLScore.objects.filter(company=company).select_related('health', 'year').order_by('year__fiscal_year')
    financials = ProfitLoss.objects.filter(company=company).select_related('year').order_by('year__fiscal_year')
    balance_sheet = BalanceSheet.objects.filter(company=company).select_related('year').order_by('year__fiscal_year')
    cash_flow = CashFlow.objects.filter(company=company).select_related('year').order_by('year__fiscal_year')
    analysis = Analysis.objects.filter(company=company).select_related('year').order_by('year__fiscal_year')
    pros_cons = ProsCons.objects.filter(company=company)
    
    # 2. Latest Snapshots
    latest_score = scores.last()
    latest_bs = balance_sheet.last()
    
    # 3. Peer Comparison (Same Sector)
    peers = []
    if company.sector:
        peer_companies = Company.objects.filter(
            sector=company.sector
        ).exclude(
            symbol=symbol
        ).exclude(
            symbol=''
        ).exclude(
            symbol__isnull=True
        )[:5]
        
        for p in peer_companies:
            latest_peer_analysis = Analysis.objects.filter(company=p).order_by('year__fiscal_year').last()
            peers.append({
                'symbol': p.symbol,
                'company_name': p.company_name,
                'roe': latest_peer_analysis.roe_pct if latest_peer_analysis else "N/A"
            })
    
    context = {
        'company': company,
        'live_data': live_data,
        'scores': scores,
        'latest_score': latest_score,
        'financials': financials,
        'balance_sheet': balance_sheet,
        'cash_flow': cash_flow,
        'analysis': analysis,
        'latest_bs': latest_bs,
        'pros_cons': pros_cons,
        'peers': peers,
    }
    return render(request, 'analytics/company_detail.html', context)

@login_required
@cache_page(60 * 15)  # Cache for 15 minutes
def sector_analysis(request):
    """Sector analysis view with robust defensive handling for empty/missing tables."""
    try:
        sectors = Sector.objects.all()
        # Use try-except specifically for the aggregate query which hits fact tables
        try:
            stats = ProfitLoss.objects.values('company__sector__sector_name').annotate(
                avg_revenue=Avg('revenue'),
                total_profit=Sum('net_profit'),
                avg_margin=Avg('net_profit_margin_pct')
            ).order_by('-total_profit')
        except Exception as e:
            logger.warning(f"Failed to fetch ProfitLoss stats: {e}")
            stats = []
    except Exception as e:
        logger.error(f"Critical error in sector_analysis: {e}")
        sectors = []
        stats = []
    
    context = {
        'sectors': sectors,
        'stats': stats,
    }
    return render(request, 'analytics/sector_analysis.html', context)

@login_required
@cache_page(60 * 15)
def health_dashboard(request):
    """AI Health dashboard view with extreme robustness for missing ML data."""
    latest_year_val = "N/A"
    health_dist = []
    
    try:
        # Find the latest year that actually has ML scores
        latest_year_data = MLScore.objects.aggregate(max_year=Max('year__fiscal_year'))
        latest_year_val = latest_year_data.get('max_year')
        
        if latest_year_val:
            # Aggregate counts by health label for all records matching that fiscal year value
            health_dist = MLScore.objects.filter(
                year__fiscal_year=latest_year_val
            ).values('health__label_name').annotate(
                count=Count('id')
            ).order_by('health__health_id')
        else:
            latest_year_val = "N/A"
            health_dist = []
    except Exception as e:
        logger.error(f"Error in health_dashboard database query: {e}")
        latest_year_val = "Unavailable"
        health_dist = []
    
    context = {
        'health_dist': health_dist,
        'latest_year': latest_year_val
    }
    return render(request, 'analytics/health_dashboard.html', context)

class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.select_related('sector').all()
    serializer_class = CompanySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sector', 'industry']
    search_fields = ['symbol', 'company_name']
    ordering_fields = ['company_name']

    @method_decorator(cache_page(60 * 10))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CompanyDetailSerializer
        return CompanySerializer

    @action(detail=False, methods=['get'])
    def top_performers(self, request):
        """Returns top 10 companies by latest ML score."""
        latest_year = MLScore.objects.latest('year__fiscal_year').year
        top_scores = MLScore.objects.filter(year=latest_year).select_related('company', 'health', 'year').order_by('-probability_score')[:10]
        serializer = MLScoreSerializer(top_scores, many=True)
        return Response(serializer.data)

class MLScoreViewSet(viewsets.ModelViewSet):
    queryset = MLScore.objects.select_related('company', 'health', 'year').all()
    serializer_class = MLScoreSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'health', 'year__fiscal_year']

    @method_decorator(cache_page(60 * 10))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class FinancialsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProfitLoss.objects.all()
    serializer_class = ProfitLossSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'year__fiscal_year']

    @action(detail=False, methods=['get'])
    def sector_summary(self, request):
        """Returns aggregated financial summary by sector."""
        from django.db.models import Avg, Sum
        summary = ProfitLoss.objects.values('company__sector__sector_name').annotate(
            avg_revenue=Avg('revenue'),
            total_net_profit=Sum('net_profit'),
            avg_margin=Avg('net_profit_margin_pct')
        ).order_by('-total_net_profit')
        return Response(summary)
