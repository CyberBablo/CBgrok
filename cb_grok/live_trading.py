import asyncio
import websockets
import json
import pandas as pd
from cb_grok.strategies.moving_average_strategy import moving_average_strategy
from cb_grok.utils.telegram_bot import TelegramBot
import os
from websockets.exceptions import ConnectionClosedOK

def load_model_params(filename):
    """Загрузка параметров модели из файла."""
    best_models_folder = "library/best_models_params"
    filepath = os.path.join(best_models_folder, filename)
    with open(filepath, 'r') as f:
        model_params_with_meta = json.load(f)
    return model_params_with_meta

async def live_trading(filename, telegram_token, telegram_chat_id, mode="production", ws_url=None, initial_capital=10000):
    """Запуск торговли в реальном времени или симуляции."""
    model_params_with_meta = load_model_params(filename)
    symbol = model_params_with_meta["symbol"]
    timeframe = model_params_with_meta["timeframe"]
    strategy_params = {k: v for k, v in model_params_with_meta.items() if k not in ["symbol", "timeframe", "limit", "stop_loss_multiplier", "take_profit_multiplier"]}
    stop_loss_multiplier = model_params_with_meta.get("stop_loss_multiplier", 1.5)
    take_profit_multiplier = model_params_with_meta.get("take_profit_multiplier", 3.0)

    telegram_bot = TelegramBot(telegram_token, telegram_chat_id, timeout=20)

    if mode == "production":
        ws_url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@kline_{timeframe}"
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

    print(f"Подключение к {ws_url} в режиме {mode}")
    await telegram_bot.send_message(f"Подключение к {ws_url} в режиме {mode}")

    try:
        async with websockets.connect(ws_url) as websocket:
            while True:
                try:
                    response = await websocket.recv()
                    data = json.loads(response)

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

                    limit = model_params_with_meta.get("limit", 100)
                    if len(data_buffer) > limit:
                        data_buffer = data_buffer.iloc[-limit:]

                    if len(data_buffer) < required_candles:
                        continue

                    strategy_data = moving_average_strategy(data_buffer.copy(), **strategy_params, debug=False)
                    latest_signal = strategy_data['signal'].iloc[-1]
                    atr = strategy_data['atr'].iloc[-1]
                    current_price = float(df['close'].iloc[0])

                    decision = "Держать"

                    if position_open:
                        if current_price <= stop_loss:
                            decision = "Продажа (стоп-лосс)"
                            cash += assets * current_price
                            assets = 0.0
                            position_open = False
                        elif current_price >= take_profit:
                            decision = "Продажа (тейк-профит)"
                            cash += assets * current_price
                            assets = 0.0
                            position_open = False
                        elif latest_signal == -1:
                            decision = "Продажа (сигнал)"
                            cash += assets * current_price
                            assets = 0.0
                            position_open = False
                    else:
                        if latest_signal == 1 and cash > 0:
                            decision = "Покупка"
                            assets = cash / current_price
                            cash = 0.0
                            position_open = True
                            entry_price = current_price
                            stop_loss = entry_price - atr * stop_loss_multiplier
                            take_profit = entry_price + atr * take_profit_multiplier

                    portfolio_value = cash + assets * current_price
                    message = (
                        f"[{candle_time}] Символ: {symbol}, Решение: {decision}, "
                        f"Цена: {current_price:.2f}, Портфель: {portfolio_value:.2f} USDT"
                    )

                    if decision != "Держать":
                        await telegram_bot.send_message(message)

                    print(message)

                except ConnectionClosedOK:
                    print("Симуляция завершена, соединение закрыто.")
                    break

    except Exception as e:
        print(f"Ошибка при подключении к WebSocket: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Запуск торговли в реальном времени или симуляции")
    parser.add_argument("filename", type=str, help="Имя файла с параметрами модели")
    parser.add_argument("telegram_token", type=str, help="Токен Telegram бота")
    parser.add_argument("telegram_chat_id", type=str, help="ID чата Telegram")
    parser.add_argument("--mode", type=str, default="production", help="Режим: production или simulation")
    parser.add_argument("--ws_url", type=str, help="URL WebSocket для симуляции")
    parser.add_argument("--initial_capital", type=float, default=10000, help="Начальный капитал")

    args = parser.parse_args()
    asyncio.run(live_trading(args.filename, args.telegram_token, args.telegram_chat_id, args.mode, args.ws_url, args.initial_capital))