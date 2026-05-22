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
        # Append .NS for Nifty companies if not present
        if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
            yf_symbol = f"{symbol}.NS"
        else:
            yf_symbol = symbol

        cache_key = f"stock_live_{yf_symbol}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            if info is None:
                logger.warning(f"No info found for {yf_symbol}")
                return None
            
            # Use fast_info for real-time prices if available
            fast_info = getattr(ticker, 'fast_info', None)
            
            data = {
                'symbol': symbol,
                'price': fast_info.last_price if fast_info and hasattr(fast_info, 'last_price') else info.get('currentPrice'),
                'change': fast_info.day_change if fast_info and hasattr(fast_info, 'day_change') else None,
                'change_pct': fast_info.day_change_percent if fast_info and hasattr(fast_info, 'day_change_percent') else None,
                'market_cap': info.get('marketCap'),
                'currency': info.get('currency', 'INR'),
                'day_high': fast_info.day_high if fast_info and hasattr(fast_info, 'day_high') else info.get('dayHigh'),
                'day_low': fast_info.day_low if fast_info and hasattr(fast_info, 'day_low') else info.get('dayLow'),
            }
            
            # Fallback if currentPrice is not in info
            if data['price'] is None:
                history = ticker.history(period="1d")
                if not history.empty:
                    data['price'] = history['Close'].iloc[-1]

            cache.set(cache_key, data, StockService.CACHE_TIMEOUT)
            return data
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
