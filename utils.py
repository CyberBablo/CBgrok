import json
import os
from datetime import datetime

def save_model_results(model_params, final_capital, orders, symbol, initial_capital, folder="order_bin"):
    """
    Сохраняет результаты модели в JSON-файл с префиксом POS_ или NEG_.

    :param model_params: Параметры модели.
    :param final_capital: Итоговый капитал.
    :param orders: Список ордеров.
    :param symbol: Символ торговой пары.
    :param initial_capital: Начальный капитал.
    :param folder: Папка для сохранения.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    prefix = "POS_" if final_capital > initial_capital else "NEG_"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder}/{prefix}{symbol.replace('/', '_')}_{timestamp}.json"
    data = {
        "model_params": model_params,
        "final_capital": final_capital,
        "orders": orders
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)