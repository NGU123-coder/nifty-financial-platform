import yfinance as yf
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class StockService:
    CACHE_TIMEOUT = 300  # 5 minutes

    @staticmethod
    def get_live_data(symbol):
        """
        Fetch live stock data from Yahoo Finance with caching.
        Expects Indian stock symbols to end with .NS (NSE) or .BO (BSE).
        """
        # Improved symbol handling
        if symbol.startswith('^'):
            # Index symbols (like ^NSEI) should not have .NS appended
            yf_symbol = symbol
        elif not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            yf_symbol = f"{symbol}.NS"
        else:
            yf_symbol = symbol

        cache_key = f"stock_live_{yf_symbol}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        try:
            ticker = yf.Ticker(yf_symbol)
            
            # Use fast_info for real-time prices
            fast_info = getattr(ticker, 'fast_info', None)
            
            data = {
                'symbol': symbol,
                'price': getattr(fast_info, 'last_price', None),
                'change': getattr(fast_info, 'day_change', None),
                'change_pct': getattr(fast_info, 'day_change_percent', None),
                'market_cap': getattr(fast_info, 'market_cap', None),
                'currency': 'INR', 
                'day_high': getattr(fast_info, 'day_high', None),
                'day_low': getattr(fast_info, 'day_low', None),
            }
            
            # Fallback to history if price is None (often happens on first load or for indices)
            if data['price'] is None:
                history = ticker.history(period="1d")
                if not history.empty:
                    data['price'] = history['Close'].iloc[-1]
                    data['change'] = 0.0
                    data['change_pct'] = 0.0

            if data['price'] is not None:
                cache.set(cache_key, data, StockService.CACHE_TIMEOUT)
                return data
            
            return None
        except Exception as e:
            logger.error(f"Error fetching data for {yf_symbol}: {e}")
            return None

    @staticmethod
    def get_market_trends():
        """Fetch trends for key indices."""
        indices = {
            '^NSEI': 'Nifty 50',
            '^BSESN': 'Sensex',
            '^NSEBANK': 'Nifty Bank'
        }
        trends = []
        for symbol, name in indices.items():
            data = StockService.get_live_data(symbol)
            if data:
                data['name'] = name
                trends.append(data)
        return trends
