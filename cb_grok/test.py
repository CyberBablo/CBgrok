from datetime import datetime, timedelta
from cb_grok.adapters.exchange_adapter import ExchangeAdapter
import logging
import os




bybit_exchanger = ExchangeAdapter(exchange_name="bybit")
binance_exchanger = ExchangeAdapter(exchange_name="binance")


bybit_data = bybit_exchanger.fetch_ohlcv("BTCUSDT", "1h", limit=2000, total_limit=2000)


print(bybit_data)


