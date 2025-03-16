import asyncio
import websockets
import json
import pandas as pd
from cb_grok.adapters.exchange_adapter import ExchangeAdapter

class WSSAdapter:
    def __init__(self, exchange_name='binance'):
        self.exchange_name = exchange_name
        self.ws_url = f"wss://stream.{exchange_name}.com:9443/ws"

    async def connect(self, symbol, timeframe):
        """Подключение к WebSocket биржи для получения данных в реальном времени."""
        async with websockets.connect(self.ws_url) as websocket:
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@kline_{timeframe}"],
                "id": 1
            }
            await websocket.send(json.dumps(subscribe_msg))
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                if 'k' in data:
                    kline = data['k']
                    df = pd.DataFrame([{
                        'timestamp': pd.to_datetime(kline['t'], unit='ms'),
                        'open': float(kline['o']),
                        'high': float(kline['h']),
                        'low': float(kline['l']),
                        'close': float(kline['c']),
                        'volume': float(kline['v'])
                    }])
                    df.set_index('timestamp', inplace=True)
                    yield df

    async def simulate(self, symbol, timeframe, limit=1000):
        """Имитация данных за последние 1000 часов с интервалом в 1 час."""
        adapter = ExchangeAdapter(self.exchange_name)
        data = adapter.fetch_ohlcv(symbol, timeframe, limit=limit)
        for _, row in data.iterrows():
            df = pd.DataFrame([row])
            yield df
            await asyncio.sleep(1)  # Задержка 1 секунда для имитации реального времени