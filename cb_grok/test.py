import asyncio
import websockets
import json


async def test_ws():
    ws_url = "wss://stream.bybit.com/v5/public/spot"  # URL для спотовой торговли
    try:
        async with websockets.connect(ws_url) as websocket:
            subscription_message = {
                "op": "subscribe",
                "args": ["kline.60.BTCUSDT"]  # Используем "60" вместо "1h"
            }
            await websocket.send(json.dumps(subscription_message))
            print(f"Отправлена подписка: {subscription_message}")

            # Получение и вывод ответа от сервера
            response = await websocket.recv()
            print(f"Получен ответ: {response}")
    except Exception as e:
        print(f"Ошибка: {e}")


asyncio.run(test_ws())