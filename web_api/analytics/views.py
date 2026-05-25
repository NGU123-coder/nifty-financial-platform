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
    """Registration view for new analysts."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                return redirect('dashboard')
            except Exception as e:
                logger.error(f"Error during registration: {e}")
                return render(request, 'registration/register.html', {'form': form, 'error': str(e)})
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

from django.http import HttpResponse

def ping(request):
    """Public health check endpoint."""
    return HttpResponse("pong", status=200)

@login_required
@cache_page(60 * 5)
def dashboard(request):
    """Main dashboard view with explicit debug logging."""
    try:
        companies_qs = Company.objects.all()
        total_companies = companies_qs.count()
        print(f"DEBUG Dashboard: Total Companies = {total_companies}")
        
        sectors = Sector.objects.annotate(company_count=Count('company'))
        
        # Latest scores logic
        latest_year_data = MLScore.objects.aggregate(max_year=Max('year__fiscal_year'))
        latest_year_val = latest_year_data.get('max_year')
        print(f"DEBUG Dashboard: Latest Year = {latest_year_val}")
        
        if latest_year_val:
            latest_scores = MLScore.objects.filter(
                year__fiscal_year=latest_year_val
            ).select_related('company', 'health').order_by('-probability_score')[:10]
        else:
            latest_scores = []

        market_trends = []
        try:
            market_trends = StockService.get_market_trends()
        except Exception as e:
            logger.error(f"StockService Error: {e}")

        context = {
            'total_companies': total_companies,
            'sectors': sectors,
            'latest_scores': latest_scores,
            'display_year': latest_year_val or "N/A",
            'market_trends': market_trends
        }
        return render(request, 'analytics/dashboard.html', context)
    except Exception as e:
        logger.error(f"Dashboard Error: {e}")
        return render(request, 'analytics/dashboard.html', {'error': True})

@login_required
def company_detail(request, symbol):
    """Deep-dive company analysis view."""
    company = get_object_or_404(Company, symbol=symbol)
    live_data = StockService.get_live_data(company.symbol)
    
    scores = MLScore.objects.filter(company=company).select_related('health', 'year').order_by('year__fiscal_year')
    financials = ProfitLoss.objects.filter(company=company).select_related('year').order_by('year__fiscal_year')
    
    # New context data for deep dive
    latest_score = scores.last()
    latest_bs = BalanceSheet.objects.filter(company=company).order_by('year__fiscal_year').last()
    analysis_qs = Analysis.objects.filter(company=company).order_by('year__fiscal_year')
    pros_cons = ProsCons.objects.filter(company=company)
    
    # Peer selection (same sector, excluding self)
    peers = Company.objects.filter(sector=company.sector).exclude(symbol=company.symbol)[:5]
    
    # Debug logging for chart troubleshooting
    print(f"DEBUG Chart: Company = {symbol}")
    print(f"DEBUG Chart: Financials Count = {financials.count()}")
    print(f"DEBUG Chart: Years = {[f.year.period_name for f in financials]}")
    chart_payload = {
        "labels": [f.year.period_name for f in financials],
        "revenue": [float(f.revenue or 0) for f in financials],
        "profit": [float(f.net_profit or 0) for f in financials]
    }
    print(f"DEBUG Chart: Serialized Payload = {chart_payload}")

    context = {
        'company': company,
        'live_data': live_data,
        'scores': scores,
        'financials': financials,
        'latest_score': latest_score,
        'latest_bs': latest_bs,
        'analysis': analysis_qs,
        'pros_cons': pros_cons,
        'peers': peers,
    }
    return render(request, 'analytics/company_detail.html', context)

@login_required
def sector_analysis(request):
    """Sector analysis view with explicit aggregation fixes."""
    try:
        sectors = Sector.objects.all()
        stats = ProfitLoss.objects.values('company__sector__sector_name').annotate(
            avg_revenue=Avg('revenue'),
            total_profit=Sum('net_profit'),
            avg_margin=Avg('net_profit_margin_pct'),
            count=Count('company', distinct=True)
        ).order_by('-total_profit')
        
        print(f"DEBUG Sector: Found {len(stats)} sector stat rows")
        
        context = {
            'sectors': sectors,
            'stats': stats,
        }
        return render(request, 'analytics/sector_analysis.html', context)
    except Exception as e:
        logger.error(f"Sector Analysis Error: {e}")
        return render(request, 'analytics/sector_analysis.html', {'sectors': [], 'stats': []})

@login_required
def health_dashboard(request):
    """AI Health dashboard view."""
    try:
        latest_year_data = MLScore.objects.aggregate(max_year=Max('year__fiscal_year'))
        latest_year_val = latest_year_data.get('max_year')
        
        health_dist = []
        if latest_year_val:
            health_dist = MLScore.objects.filter(
                year__fiscal_year=latest_year_val
            ).values('health__label_name').annotate(
                count=Count('id')
            ).order_by('health__health_id')
            
        print(f"DEBUG Health: Latest Year = {latest_year_val}, Dist count = {len(health_dist)}")

        context = {
            'health_dist': health_dist,
            'latest_year': latest_year_val or "N/A"
        }
        return render(request, 'analytics/health_dashboard.html', context)
    except Exception as e:
        logger.error(f"Health Dashboard Error: {e}")
        return render(request, 'analytics/health_dashboard.html', {'health_dist': [], 'latest_year': "Error"})

# ViewSets for API
class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.select_related('sector').all()
    serializer_class = CompanySerializer

class MLScoreViewSet(viewsets.ModelViewSet):
    queryset = MLScore.objects.select_related('company', 'health', 'year').all()
    serializer_class = MLScoreSerializer

class FinancialsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProfitLoss.objects.all()
    serializer_class = ProfitLossSerializer

    @action(detail=False, methods=['get'])
    def sector_summary(self, request):
        """Returns aggregated financial summary by sector."""
        summary = ProfitLoss.objects.values('company__sector__sector_name').annotate(
            avg_revenue=Avg('revenue'),
            total_net_profit=Sum('net_profit'),
            avg_margin=Avg('net_profit_margin_pct')
        ).order_by('-total_net_profit')
        return Response(summary)
