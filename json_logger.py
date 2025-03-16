import json
import os
from datetime import datetime


def save_model_results(model_params, final_capital, orders, symbol, initial_capital, folder="order_bin"):
    """
    Сохраняет результаты модели в JSON-файл с приставкой POS_ или NEG_ в зависимости от прибыльности.

    :param model_params: Словарь с параметрами модели.
    :param final_capital: Итоговый капитал после бэктеста.
    :param orders: Список ордеров.
    :param symbol: Символ валютной пары (например, 'BTC/USDT').
    :param initial_capital: Начальный капитал для сравнения.
    :param folder: Папка для сохранения файлов (по умолчанию 'order_bin').
    """
    # Создаем папку, если ее нет
    if not os.path.exists(folder):
        os.makedirs(folder)
    # Определяем приставку: POS_ для прибыли, NEG_ для убытка
    prefix = "POS_" if final_capital > initial_capital else "NEG_"

    # Генерируем имя файла с приставкой, символом и временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder}/{prefix}{symbol.replace('/', '_')}_{timestamp}.json"

    # Формируем данные для записи
    data = {
        "model_params": model_params,
        "final_capital": final_capital,
        "orders": orders
    }

    # Записываем данные в JSON-файл
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

    # print(f"Результаты сохранены в {filename}")