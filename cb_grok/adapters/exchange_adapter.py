import ccxt
import pandas as pd
import time
import traceback

class ExchangeAdapter:
    def __init__(self, exchange_name='binance', api_key=None, api_secret=None):
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

    def fetch_ohlcv(self, symbol, timeframe='1m', limit=1000, total_limit=5000):
        all_data = []
        max_per_request = 1000 if self.exchange_name == 'bybit' else limit
        since = None
        # print("limits", timeframe, limit, total_limit)
        while len(all_data) < total_limit:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=max_per_request)
                if not ohlcv:
                    break
                temp_test = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                temp_test['timestamp'] = pd.to_datetime(temp_test['timestamp'], unit='ms')
                # print("TEMP TEST___________________")
                # print(temp_test)
                # print("_____________________________")
                all_data = ohlcv + all_data
                since = ohlcv[0][0] - (max_per_request * self._timeframe_to_milliseconds(timeframe))
                time.sleep(self.exchange.rateLimit / 1000)

            except:
                print(f"Ошибка при загрузке данных: " + traceback.format_exc())
                break
        all_data = all_data[-total_limit:]
        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df

    def _timeframe_to_milliseconds(self, timeframe):
        if timeframe == '1m':
            return 60 * 1000
        if timeframe == '15m':
            return 60 * 1000 * 15
        elif timeframe == '1h':
            return 3600 * 1000
        elif timeframe == '1d':
            return 86400 * 1000
        else:
            raise ValueError(f"Неподдерживаемый таймфрейм: {timeframe}")

    def create_order(self, symbol, side, amount, price=None, stop_loss=None, take_profit=None):
        params = {}
        if stop_loss:
            params['stop_loss'] = stop_loss
            if self.exchange_name == 'binance':
                params['stopPrice'] = stop_loss
        if take_profit:
            params['take_profit'] = take_profit
            if self.exchange_name == 'binance':
                params['takeProfitPrice'] = take_profit
        order_type = 'limit' if price else 'market'
        return self.exchange.create_order(symbol, order_type, side, amount, price, params)

    def fetch_balance(self):
        return self.exchange.fetch_balance()