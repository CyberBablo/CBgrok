import asyncio
import websockets
import json
import pandas as pd
from cb_grok.adapters.exchange_adapter import ExchangeAdapter
from cb_grok.strategies.moving_average_strategy import moving_average_strategy
from cb_grok.utils.telegram_bot import TelegramBot
import os
from websockets.exceptions import ConnectionClosedOK, InvalidStatus
import logging
from datetime import datetime

# Настройка логирования
log_folder = "log"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"{log_folder}/live_trading_{timestamp}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_model_params(filename):
    """Загрузка параметров модели из файла."""
    best_models_folder = "library/best_models_params"
    filepath = os.path.join(best_models_folder, filename)
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки параметров модели: {e}")
        raise

def convert_timeframe_for_bybit(timeframe):
    """Преобразование текстового интервала в числовой для Bybit."""
    mapping = {
        '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30', '1h': '60',
        '2h': '120', '4h': '240', '6h': '360', '12h': '720', '1d': 'D', '1w': 'W', '1M': 'M'
    }
    return mapping.get(timeframe, timeframe)

async def live_trading(filename, telegram_token, telegram_chat_id, mode="production", ws_url=None,
                      initial_capital=10000, exchange_name='binance', api_key=None, api_secret=None,
                      category='linear', timeframe='1h'):
    """Запуск торговли в реальном времени или симуляции."""
    try:
        model_params = load_model_params(filename)
        symbol = model_params["symbol"]
        timeframe_from_file = model_params.get("timeframe", timeframe)
        strategy_params = {k: v for k, v in model_params.items() if k not in ["symbol", "timeframe", "limit",
                                                                             "stop_loss_multiplier",
                                                                             "take_profit_multiplier"]}
        stop_loss_multiplier = model_params.get("stop_loss_multiplier", 2)
        take_profit_multiplier = model_params.get("take_profit_multiplier", 4)

        telegram_bot = TelegramBot(telegram_token, telegram_chat_id, timeout=20)
        exchange = ExchangeAdapter(exchange_name, api_key, api_secret)

        # Преобразование timeframe для Bybit, если используется
        ws_timeframe = timeframe_from_file
        if exchange_name == 'bybit':
            ws_timeframe = convert_timeframe_for_bybit(timeframe_from_file)

        # Определение WebSocket URL
        if mode == "production":
            if exchange_name == 'binance':
                ws_url = f"wss://stream.binance.com:9443/ws/{symbol.lower().replace('/', '')}usdt@kline_{timeframe_from_file}"
            elif exchange_name == 'bybit':
                if category == 'spot':
                    ws_url = "wss://stream.bybit.com/v5/public/spot"
                elif category == 'linear':
                    ws_url = "wss://stream.bybit.com/v5/public/linear"
                elif category == 'inverse':
                    ws_url = "wss://stream.bybit.com/v5/public/inverse"
                elif category == 'option':
                    ws_url = "wss://stream.bybit.com/v5/public/option"
                else:
                    raise ValueError(f"Неподдерживаемая категория для Bybit: {category}")
            else:
                raise ValueError(f"Неподдерживаемая биржа: {exchange_name}")
        elif mode == "simulation":
            ws_url = ws_url or "ws://localhost:8765"
        else:
            raise ValueError("Неверный режим. Используйте 'production' или 'simulation'.")

        data_buffer = pd.DataFrame()
        cash = initial_capital
        assets = 0.0
        position_open = False
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0

        required_candles = max(strategy_params.get("long_period", 50), strategy_params.get("ema_long_period", 200))

        logger.info(f"Подключение к {ws_url} в режиме {mode}")
        await telegram_bot.send_message(f"Подключение к {ws_url} в режиме {mode}")

        async with websockets.connect(ws_url) as websocket:
            if exchange_name == 'bybit' and mode == "production":
                subscription_message = {
                    "op": "subscribe",
                    "args": [f"kline.{ws_timeframe}.{symbol.replace('/', '')}"]
                }
                await websocket.send(json.dumps(subscription_message))
                logger.info(f"Отправлена подписка: {subscription_message}")

            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)

                    # Обработка данных в зависимости от режима
                    if mode == "simulation":
                        # Ожидаем данные в формате {'open': ..., 'high': ..., 'low': ..., 'close': ..., 'volume': ..., 'timestamp': ...}
                        candle_time = pd.to_datetime(data['timestamp'])
                        df = pd.DataFrame([{
                            'open': float(data['open']),
                            'high': float(data['high']),
                            'low': float(data['low']),
                            'close': float(data['close']),
                            'volume': float(data['volume']),
                            'timestamp': candle_time
                        }])
                        df.set_index('timestamp', inplace=True)
                        data_buffer = pd.concat([data_buffer, df])

                    # Обработка данных от Bybit
                    elif exchange_name == 'bybit' and 'topic' in data and data['topic'].startswith('kline'):
                        candle = data['data'][0]
                        candle_time = pd.to_datetime(candle['start'], unit='ms')
                        df = pd.DataFrame([{
                            'open': float(candle['open']),
                            'high': float(candle['high']),
                            'low': float(candle['low']),
                            'close': float(candle['close']),
                            'volume': float(candle['volume']),
                            'timestamp': candle_time
                        }])
                        df.set_index('timestamp', inplace=True)
                        data_buffer = pd.concat([data_buffer, df])

                    # Обработка данных от Binance
                    elif exchange_name == 'binance' and 'k' in data:
                        candle = data['k']
                        if candle['x']:  # Проверяем, закрыта ли свеча
                            candle_time = pd.to_datetime(candle['t'], unit='ms')
                            df = pd.DataFrame([{
                                'open': float(candle['o']),
                                'high': float(candle['h']),
                                'low': float(candle['l']),
                                'close': float(candle['c']),
                                'volume': float(candle['v']),
                                'timestamp': candle_time
                            }])
                            df.set_index('timestamp', inplace=True)
                            data_buffer = pd.concat([data_buffer, df])

                    # Ограничение буфера данных
                    limit = model_params.get("limit", 100)
                    if len(data_buffer) > limit:
                        data_buffer = data_buffer.iloc[-limit:]

                    if len(data_buffer) < required_candles:
                        continue

                    # Применение стратегии
                    strategy_data = moving_average_strategy(data_buffer.copy(), **strategy_params, debug=False)
                    latest_signal = strategy_data['signal'].iloc[-1]
                    atr = strategy_data['atr'].iloc[-1]
                    current_price = float(df['close'].iloc[0])
                    logger.info(f"Текущая цена: {current_price}")
                    decision = "Держать"
                    transaction_amount = 0.0

                    # Логика торговли в режиме production
                    if mode == "production" and position_open:
                        balance = exchange.fetch_balance()
                        assets = balance['total'].get(symbol.split('/')[0], 0)
                        if current_price <= stop_loss or current_price >= take_profit or latest_signal == -1:
                            exchange.create_order(symbol, 'sell', assets, stop_loss=stop_loss, take_profit=take_profit)
                            decision = "Продажа"
                            transaction_amount = assets
                            cash += assets * current_price
                            assets = 0.0
                            position_open = False
                    elif mode == "production" and latest_signal == 1 and not position_open:
                        amount = cash / current_price
                        exchange.create_order(symbol, 'buy', amount, stop_loss=stop_loss, take_profit=take_profit)
                        decision = "Покупка"
                        transaction_amount = amount
                        assets = amount
                        cash = 0.0
                        position_open = True
                        entry_price = current_price
                        stop_loss = entry_price - atr * stop_loss_multiplier
                        take_profit = entry_price + atr * take_profit_multiplier

                    # Логика торговли в режиме simulation
                    elif mode == "simulation":
                        if position_open:
                            if current_price <= stop_loss:
                                decision = "Продажа (стоп-лосс)"
                                transaction_amount = assets
                                cash += assets * current_price
                                assets = 0.0
                                position_open = False
                            elif current_price >= take_profit:
                                decision = "Продажа (тейк-профит)"
                                transaction_amount = assets
                                cash += assets * current_price
                                assets = 0.0
                                position_open = False
                            elif latest_signal == -1:
                                decision = "Продажа (сигнал)"
                                transaction_amount = assets
                                cash += assets * current_price
                                assets = 0.0
                                position_open = False
                        else:
                            if latest_signal == 1 and cash > 0:
                                decision = "Покупка"
                                transaction_amount = cash / current_price
                                assets = transaction_amount
                                cash = 0.0
                                position_open = True
                                entry_price = current_price
                                stop_loss = entry_price - atr * stop_loss_multiplier
                                take_profit = entry_price + atr * take_profit_multiplier

                    # Формирование отчёта
                    portfolio_value = cash + assets * current_price
                    action_detail = (f"{decision}: {transaction_amount:.2f} {symbol.split('/')[0]}"
                                    if decision != "Держать" else "")
                    portfolio_detail = f"({cash:.2f} USDT + {assets:.2f} {symbol.split('/')[0]})"
                    message = (f"[{candle_time}] Символ: {symbol}, Решение: {decision}, "
                              f"Цена: {current_price:.2f}, {action_detail}, Портфель: {portfolio_value:.2f} USDT {portfolio_detail}")

                    if decision != "Держать":
                        await telegram_bot.send_message(message)
                    logger.info(message)

                except ConnectionClosedOK:
                    logger.info("Соединение закрыто корректно.")
                    break
                except Exception as e:
                    logger.error(f"Ошибка в цикле обработки: {e}")
                    await telegram_bot.send_message(f"Ошибка: {e}")

    except InvalidStatus as e:
        logger.error(f"Ошибка WebSocket: {e}")
        await telegram_bot.send_message(f"Ошибка WebSocket: {e}")
        raise
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        await telegram_bot.send_message(f"Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Запуск торговли в реальном времени или симуляции")
    parser.add_argument("filename", help="Имя файла с параметрами модели")
    parser.add_argument("telegram_token", help="Токен Telegram бота")
    parser.add_argument("telegram_chat_id", help="ID чата Telegram")
    parser.add_argument("--mode", default="production", help="Режим: production или simulation")
    parser.add_argument("--ws_url", help="URL WebSocket для симуляции")
    parser.add_argument("--initial_capital", type=float, default=10000, help="Начальный капитал")
    parser.add_argument("--exchange_name", default="binance", help="Биржа: binance или bybit")
    parser.add_argument("--api_key", help="API-ключ")
    parser.add_argument("--api_secret", help="API-секрет")
    parser.add_argument("--category", default="linear", help="Категория торговли для Bybit: spot, linear, inverse, option")
    parser.add_argument("--timeframe", default="1h", help="Таймфрейм (например, 1h, 5m)")

    args = parser.parse_args()
    asyncio.run(live_trading(args.filename, args.telegram_token, args.telegram_chat_id, args.mode,
                            args.ws_url, args.initial_capital, args.exchange_name, args.api_key,
                            args.api_secret, args.category, args.timeframe))