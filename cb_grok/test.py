
from datetime import datetime, timedelta
from cb_grok.adapters.exchange_adapter import ExchangeAdapter
import logging
import os




bybit_exchanger = ExchangeAdapter(exchange_name="bybit")
binance_exchanger = ExchangeAdapter(exchange_name="binance")


bybit_data = bybit_exchanger.fetch_ohlcv("BTCUSDT", "1h", limit=10, total_limit=10)
binance_data = binance_exchanger.fetch_ohlcv("BTCUSDT", "1h", limit=10, total_limit=10)


print(bybit_data)

print(binance_data)

