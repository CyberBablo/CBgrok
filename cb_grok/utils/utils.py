import json
import os
from datetime import datetime
import hashlib

def save_model_results(model_params, final_capital, orders, symbol, initial_capital, folder="order_bin"):
    """
    Сохраняет результаты модели в JSON-файл с меткой POS_ или NEG_, хэшем параметров и временной меткой.

    :param model_params: Словарь с параметрами модели (без symbol и timeframe).
    :param final_capital: Итоговый капитал после бэктеста.
    :param orders: Список ордеров.
    :param symbol: Символ валютной пары (например, 'BTC/USDT').
    :param initial_capital: Начальный капитал для сравнения.
    :param folder: Папка для сохранения файлов (по умолчанию 'order_bin').
    """
    # Создаём папку, если её нет
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Определяем метку: POS_ для прибыли, NEG_ для убытка
    prefix = "POS_" if final_capital > initial_capital else "NEG_"

    # Сериализуем параметры модели в строку JSON с сортировкой ключей
    params_str = json.dumps(model_params, sort_keys=True)

    # Генерируем SHA-256 хэш и берём первые 16 символов
    hash_object = hashlib.sha256(params_str.encode())
    hash_hex = hash_object.hexdigest()[:16]

    # Генерируем временную метку
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Формируем имя файла: POS/NEG_hash_timestamp.json
    filename = f"{folder}/{prefix}{hash_hex}_{timestamp}.json"

    # Формируем данные для записи
    data = {
        "model_params": model_params,
        "final_capital": final_capital,
        "orders": orders,
        "symbol": symbol
    }

    # Записываем данные в JSON-файл
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Результаты сохранены в {filename}")