import yfinance as yf
from django.core.cache import cache
import logging
import os

logger = logging.getLogger(__name__)

class StockService:
    CACHE_TIMEOUT = 300
    IS_PROD = os.getenv('DEBUG', 'False').lower() == 'false'

    @staticmethod
    def get_live_data(symbol):
        if not symbol: return None
        
        yf_symbol = symbol if symbol.startswith('^') else f"{symbol}.NS"
        cache_key = f"stock_v2_{yf_symbol}"
        cached = cache.get(cache_key)
        if cached: return cached

        # In production, we favor stability. 
        # If rate limited, return a stable placeholder immediately.
        try:
            ticker = yf.Ticker(yf_symbol)
            fast = getattr(ticker, 'fast_info', None)
            
            price = getattr(fast, 'last_price', None)
            if price is None:
                # 2nd attempt: history (usually more reliable if info is throttled)
                hist = ticker.history(period="1d")
                price = hist['Close'].iloc[-1] if not hist.empty else None

            if price:
                data = {
                    'symbol': symbol,
                    'price': float(price),
                    'change': float(getattr(fast, 'day_change', 0) or 0),
                    'change_pct': float(getattr(fast, 'day_change_percent', 0) or 0),
                    'market_cap': getattr(fast, 'market_cap', None),
                    'currency': 'INR'
                }
                cache.set(cache_key, data, StockService.CACHE_TIMEOUT)
                return data
        except Exception as e:
            logger.warning(f"Stock lookup failed for {yf_symbol}: {e}")
        
        # Static Fallback to prevent dashboard crashes
        return {
            'symbol': symbol,
            'price': 0.0,
            'change': 0.0,
            'change_pct': 0.0,
            'market_cap': 0,
            'currency': 'INR',
            'is_fallback': True
        }

    @staticmethod
    def get_market_trends():
        indices = {'^NSEI': 'Nifty 50', '^BSESN': 'Sensex'}
        trends = []
        for sym, name in indices.items():
            data = StockService.get_live_data(sym)
            if data:
                data['name'] = name
                trends.append(data)
        return trends
