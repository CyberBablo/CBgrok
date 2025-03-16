import ccxt
import pandas as pd
from datetime import datetime, timedelta

class ExchangeAdapter:
    def __init__(self, exchange_name='binance'):
        """Инициализирует адаптер для указанной биржи."""
        self.exchange = getattr(ccxt, exchange_name)()

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """
        Загружает OHLCV-данные с биржи.

        :param symbol: Символ торговой пары, например, 'BTC/USDT'.
        :param timeframe: Таймфрейм свечей, например, '1h'.
        :param limit: Количество свечей для загрузки.
        :return: DataFrame с данными OHLCV, индексированный по времени.
        """
        since = self.exchange.parse8601((datetime.now() - timedelta(hours=limit)).isoformat())
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df.set_index('timestamp')