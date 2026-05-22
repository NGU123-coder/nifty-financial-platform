# B100 Intelligence DAX Measures Library

This document provides a comprehensive library of DAX measures for the "B100 Intelligence" financial analytics project.

## 1. Setup: Measures Table
Create a disconnected table to house all measures.
```dax
_Measures = DATATABLE("Index", INTEGER, {{1}})
```
*After creating, hide the 'Index' column.*

---

## 2. Naming Conventions & Folder Organization
- **Base Measures:** `[Total ...]` or `[Avg ...]`
- **YoY Growth:** `[% Growth ...]`
- **Benchmarks:** `[Sector Avg ...]`
- **Formatting:** `[_Color ...]` or `[_Dynamic Title]`

**Folders:**
- 01_Core_KPIs
- 02_Growth
- 03_Profitability
- 04_Leverage_Debt
- 05_Cash_Flow
- 06_Dividends
- 07_ML_Scoring
- 08_Sector_Analysis
- 09_Time_Intelligence
- 10_UI_Formatting

---

## 3. Core DAX Measures

### 01_Core_KPIs
```dax
Total Revenue = SUM('fact_profit_loss'[revenue])

Total Net Profit = SUM('fact_profit_loss'[net_profit])

Total Assets = SUM('fact_balance_sheet'[total_assets])

Market Cap = SUM('fact_analysis'[market_cap])

Current Stock Price = AVERAGE('fact_analysis'[current_price])
```

### 02_Growth
```dax
Revenue Growth YoY = 
VAR CurrentVal = [Total Revenue]
VAR PreviousVal = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR('dim_year'[fiscal_year_date])) -- Assuming a date relationship exists, otherwise use custom logic below
RETURN
DIVIDE(CurrentVal - PreviousVal, PreviousVal)

-- Robust Growth Logic (Manual Year Offset)
Net Profit Growth % = 
VAR CurrentYear = SELECTEDVALUE('dim_year'[fiscal_year])
VAR CurrentVal = [Total Net Profit]
VAR PreviousVal = CALCULATE([Total Net Profit], 'dim_year'[fiscal_year] = CurrentYear - 1)
RETURN
DIVIDE(CurrentVal - PreviousVal, ABS(PreviousVal))
```

### 03_Profitability
```dax
Net Profit Margin % = DIVIDE([Total Net Profit], [Total Revenue])

Operating Profit Margin % = DIVIDE(SUM('fact_profit_loss'[operating_profit]), [Total Revenue])

ROE % = AVERAGE('fact_analysis'[roe_pct]) / 100

ROCE % = AVERAGE('fact_analysis'[roce_pct]) / 100
```

### 04_Leverage_Debt
```dax
Debt to Equity Ratio = AVERAGE('fact_balance_sheet'[debt_to_equity])

Interest Coverage Ratio = AVERAGE('fact_analysis'[interest_coverage])

Total Borrowings = SUM('fact_balance_sheet'[borrowings])

Debt to Assets = DIVIDE([Total Borrowings], [Total Assets])
```

### 05_Cash_Flow
```dax
Free Cash Flow (FCF) = SUM('fact_cash_flow'[free_cash_flow])

OCF to Net Profit Ratio = DIVIDE(SUM('fact_cash_flow'[operating_cash_flow]), [Total Net Profit])

FCF Yield % = DIVIDE([Free Cash Flow (FCF)], [Market Cap])
```

### 06_Dividends
```dax
Dividend Yield % = AVERAGE('fact_analysis'[dividend_yield]) / 100

Dividend Payout Ratio % = AVERAGE('fact_profit_loss'[dividend_payout_pct]) / 100
```

### 07_ML_Scoring
```dax
ML Probability Score = 
VAR LatestDate = CALCULATE(MAX('fact_ml_scores'[prediction_date]), ALLSELECTED('fact_ml_scores'))
RETURN
CALCULATE(AVERAGE('fact_ml_scores'[probability_score]), 'fact_ml_scores'[prediction_date] = LatestDate)

Health Status = SELECTEDVALUE('dim_health_label'[label_name], "Unrated")

Score Confidence Label = 
SWITCH(TRUE(),
    [ML Probability Score] >= 0.8, "High Confidence",
    [ML Probability Score] >= 0.6, "Medium Confidence",
    "Low Confidence"
)
```

### 08_Sector_Analysis
```dax
Sector Avg ROE = 
CALCULATE(
    [ROE %],
    ALLEXCEPT('dim_company', 'dim_sector'[sector_name])
)

ROE vs Sector Avg = [ROE %] - [Sector Avg ROE]

Sector Rank (Market Cap) = 
RANKX(
    ALL('dim_company'),
    [Market Cap],
    ,
    DESC,
    Dense
)
```

### 09_Time_Intelligence
```dax
Revenue (Current Year) = 
VAR MaxYear = MAX('dim_year'[fiscal_year])
RETURN CALCULATE([Total Revenue], 'dim_year'[fiscal_year] = MaxYear)

Revenue (Previous Year) = 
VAR MaxYear = MAX('dim_year'[fiscal_year])
RETURN CALCULATE([Total Revenue], 'dim_year'[fiscal_year] = MaxYear - 1)
```

### 10_UI_Formatting
```dax
Color Profitability = 
SWITCH(TRUE(),
    [Net Profit Margin %] > 0.2, "#228B22", -- ForestGreen
    [Net Profit Margin %] > 0.1, "#9ACD32", -- YellowGreen
    [Net Profit Margin %] > 0, "#FFD700",    -- Gold
    "#FF4500" -- OrangeRed
)

Dynamic Dashboard Title = 
VAR Company = SELECTEDVALUE('dim_company'[company_name], "All Companies")
VAR Sector = SELECTEDVALUE('dim_sector'[sector_name], "All Sectors")
RETURN
"B100 Intelligence: " & Company & " | Sector: " & Sector

Tooltip Performance Summary = 
"Rev Growth: " & FORMAT([Revenue Growth YoY], "0.0%") & UNICHAR(10) &
"ROE: " & FORMAT([ROE %], "0.0%") & UNICHAR(10) &
"D/E: " & FORMAT([Debt to Equity Ratio], "0.00")
```

---

## 4. Implementation Instructions
1. **Relationships:** Ensure `dim_year[year_id]` relates to all `fact_...[year_id]`.
2. **Formatting:** Set Percentage measures to `Percentage` format with 1 or 2 decimal places.
3. **ML Score:** The `ML Probability Score` measure uses `prediction_date` to ensure only the latest prediction is shown by default.
4. **Aggregation:** Always use measures instead of raw columns in visuals to ensure filter context is respected.
