from django.db import models

class Sector(models.Model):
    sector_id = models.AutoField(primary_key=True)
    sector_name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        db_table = 'dim_sector'
        managed = True
        verbose_name_plural = "Sectors"

    def __str__(self):
        return self.sector_name

class HealthLabel(models.Model):
    health_id = models.AutoField(primary_key=True)
    label_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'dim_health_label'
        managed = True

    def __str__(self):
        return self.label_name

class Company(models.Model):
    company_id = models.AutoField(primary_key=True)
    symbol = models.CharField(max_length=20, unique=True)
    company_name = models.CharField(max_length=255)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, db_column='sector_id', null=True, blank=True)
    industry = models.CharField(max_length=255, null=True, blank=True)
    listing_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'dim_company'
        managed = True
        verbose_name_plural = "Companies"

    def __str__(self):
        return f"{self.symbol} - {self.company_name}"

class FiscalYear(models.Model):
    year_id = models.AutoField(primary_key=True)
    fiscal_year = models.IntegerField()
    period_name = models.CharField(max_length=20)
    sort_order = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'dim_year'
        managed = True
        unique_together = ('fiscal_year', 'period_name')

    def __str__(self):
        return self.period_name

class ProfitLoss(models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id')
    year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, db_column='year_id')
    revenue = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    expenses = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    operating_profit = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    net_profit = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    eps = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    dividend_payout_pct = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    net_profit_margin_pct = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    expense_ratio_pct = models.DecimalField(max_digits=18, decimal_places=2, null=True)

    class Meta:
        db_table = 'fact_profit_loss'
        managed = True
        unique_together = ('company', 'year')

class BalanceSheet(models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id')
    year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, db_column='year_id')
    equity_capital = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    reserves = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    borrowings = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    other_liabilities = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    total_liabilities = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    fixed_assets = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    cwip = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    investments = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    other_assets = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    total_assets = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    debt_to_equity = models.DecimalField(max_digits=18, decimal_places=2, null=True)

    class Meta:
        db_table = 'fact_balance_sheet'
        managed = True
        unique_together = ('company', 'year')

class CashFlow(models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id')
    year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, db_column='year_id')
    operating_cash_flow = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    investing_cash_flow = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    financing_cash_flow = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    net_cash_flow = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    free_cash_flow = models.DecimalField(max_digits=18, decimal_places=2, null=True)

    class Meta:
        db_table = 'fact_cash_flow'
        managed = True
        unique_together = ('company', 'year')

class Analysis(models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id')
    year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, db_column='year_id')
    market_cap = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    current_price = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    stock_pe = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    book_value = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    dividend_yield = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    roce_pct = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    roe_pct = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    interest_coverage = models.DecimalField(max_digits=18, decimal_places=2, null=True)

    class Meta:
        db_table = 'fact_analysis'
        managed = True
        unique_together = ('company', 'year')

class ProsCons(models.Model):
    id = models.AutoField(primary_key=True)
    TYPE_CHOICES = [('PROS', 'PROS'), ('CONS', 'CONS')]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    point = models.TextField()

    class Meta:
        db_table = 'fact_pros_cons'
        managed = True

class MLScore(models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id')
    year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, db_column='year_id')
    health = models.ForeignKey(HealthLabel, on_delete=models.SET_NULL, db_column='health_id', null=True)
    probability_score = models.DecimalField(max_digits=5, decimal_places=4)
    prediction_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fact_ml_scores'
        managed = True
        unique_together = ('company', 'year')
