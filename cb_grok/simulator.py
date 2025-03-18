import asyncio
import websockets
import json
import pandas as pd
from datetime import datetime, timedelta
from cb_grok.adapters.exchange_adapter import ExchangeAdapter
import logging
import os

# Настройка логирования
log_folder = "log"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"{log_folder}/simulator_{timestamp}.log"
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_filename)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

class Simulator:
    def __init__(self, symbol, timeframe, limit=500, port=8765):
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.port = port
        self.adapter = ExchangeAdapter(exchange_name="bybit")

    async def handler(self, connection):
        """Обработчик подключений для WebSocket-сервера."""
        websocket = connection

        # Загружаем данные за последние 1500 часов
        data = self.adapter.fetch_ohlcv(self.symbol, self.timeframe, limit=self.limit, total_limit=self.limit)

        logger.info(f"Отправка {len(data)} свечей для {self.symbol} ({self.timeframe})")

        for _, row in data.iterrows():
            message_data = row.to_dict()
            message_data['timestamp'] = row.name.isoformat()
            message = json.dumps(message_data)
            await websocket.send(message)
            await asyncio.sleep(0.001)

        await websocket.close(code=1000, reason="Simulation complete")

    async def start_server(self):
        """Запуск WebSocket-сервера."""
        server = await websockets.serve(self.handler, "localhost", self.port)
        logger.info(f"Симулятор запущен на ws://localhost:{self.port}")
        await asyncio.Future()

    def _timeframe_to_minutes(self, timeframe):
        """Преобразование таймфрейма в минуты."""
        if timeframe == '1m':
            return 1
        elif timeframe == '1h':
            return 60
        elif timeframe == '1d':
            return 1440
        else:
            raise ValueError(f"Неподдерживаемый таймфрейм: {timeframe}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Имитация данных биржи через WebSocket")
    parser.add_argument("symbol", type=str, help="Символ валютной пары (например, BTC/USDT)")
    parser.add_argument("timeframe", type=str, help="Таймфрейм (например, 1h)")
    parser.add_argument("--port", type=int, default=8765, help="Порт для WebSocket-сервера")

    args = parser.parse_args()
    simulator = Simulator(args.symbol, args.timeframe, port=args.port)
    asyncio.run(simulator.start_server())