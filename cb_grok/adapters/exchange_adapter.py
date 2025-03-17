import ccxt
import pandas as pd

class ExchangeAdapter:
    def __init__(self, exchange_name='binance', api_key=None, api_secret=None):
        """Инициализация адаптера для выбранной биржи."""
        if exchange_name == 'binance':
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
        elif exchange_name == 'bybit':
            self.exchange = ccxt.bybit({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
        else:
            raise ValueError(f"Неподдерживаемая биржа: {exchange_name}")
        self.exchange_name = exchange_name

    def fetch_ohlcv(self, symbol, timeframe='1m', limit=1000):
        """Загрузка OHLCV-данных с биржи."""
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df

    def create_order(self, symbol, side, amount, price=None, stop_loss=None, take_profit=None):
        """Создание ордера с поддержкой stop-loss и take-profit."""
        params = {}
        if stop_loss:
            params['stop_loss'] = stop_loss  # Bybit использует 'stop_loss'
            if self.exchange_name == 'binance':
                params['stopPrice'] = stop_loss  # Binance использует 'stopPrice' для стоп-ордеров
        if take_profit:
            params['take_profit'] = take_profit  # Bybit использует 'take_profit'
            if self.exchange_name == 'binance':
                params['takeProfitPrice'] = take_profit  # Binance требует отдельной настройки
        order_type = 'limit' if price else 'market'
        return self.exchange.create_order(symbol, order_type, side, amount, price, params)

    def fetch_balance(self):
        """Получение баланса аккаунта."""
        return self.exchange.fetch_balance()